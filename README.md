# PerenicAI

PerenicAI builds **PAT agents** (**P**erennial **A**rtificial **T**esting) that act as **quality gates** for the code of **financial institutions**: banks, payment companies and fintechs. PAT agents review code, flag problems, and give a **PASS / FAIL** verdict, so risky code is stopped before it reaches production.

There are three ways to use it:

| | Status |
|---|---|
| **Website**: paste code, upload files or scan a public GitHub repository | ✅ First version (`app.py`) |
| **GitHub**: a check on every pull request | ✅ GitHub Actions workflow. A GitHub App for private and company repositories is next |
| **On-server agent**: installed on the customer's servers, checking continuously | Planned |

> ⚠️ PAT agents help catch common PCI DSS and money-handling risks early. They do **not** certify that software is PCI DSS compliant. Only Python code is checked for now.

## How it works

```
         your code (snippet, files, repository or pull request)
                        │
                 ┌──────▼──────┐
                 │ Orchestrator │  runs the PAT agents in order and
                 └──────┬──────┘  passes messages between them
                        │
                        ▼
              PAT Code Reviewer        general bugs and code quality
                        │              (+ Claude review, focused on finance)
                        ▼
                  PAT Finance          PCI DSS and money-handling checks
                        │
                        ▼
              PAT Compliance (optional) ◄── MCP ── your compliance &
                        │                         regulation documents
                        ▼
   PASS / FAIL  ← fails if any PAT agent reports an "error"
```

- **Orchestrator** (`perenic/orchestrator.py`) runs each PAT agent. Agents talk to each other by posting messages, and every agent that runs later gets them in its `inbox`.
- **Scanner** (`perenic/scanner.py`) decides which PAT agents run. The website and the command line both use it, so they always agree.
- **PAT Code Reviewer** (`perenic/agents/code_reviewer.py`) runs general rule-based checks. When an `ANTHROPIC_API_KEY` is set, it also asks Claude for a deeper review focused on financial risks.
- **PAT Finance** (`perenic/agents/finance.py`) adds PCI DSS and money-handling checks.
- **PAT Compliance** (`perenic/agents/compliance.py`) runs last, and only when you give it documents. It reads your compliance and regulation documents through MCP and reports code that risks breaching them, citing the rule.

## PAT agents and their checks

### PAT Code Reviewer

| Rule | Severity | What it catches |
|---|---|---|
| `syntax-error` | error | Code that doesn't parse |
| `mutable-default` | error | `def f(x=[])`. The list is shared between calls |
| `bare-except` | warning | `except:` with no exception type |
| `long-function` | warning | Functions over 50 lines |
| `too-many-arguments` | warning | Functions with more than 5 arguments |
| `missing-docstring` | info | Public functions without a docstring |
| `todo` | info | `TODO` / `FIXME` comments |

### PAT Finance (PCI DSS)

| Rule | Severity | What it catches |
|---|---|---|
| `money-as-float` | error | Money held in `float` (`price = 9.99`, `amount: float`). Use `Decimal` |
| `card-number` | error | Payment card numbers in code (checked with the Luhn checksum) |
| `card-data-in-logs` | error | Card or account data (card number, CVV, IBAN, …) passed to `print()` or a logger |
| `hardcoded-secret` | error | Passwords, API keys and tokens written directly in code |

## The website

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the link it prints (usually http://localhost:8501). You can:

- **scan a public GitHub repository** by pasting its link (up to 50 Python files),
- **upload** one or more `.py` files, or
- **paste** a snippet of code.

The page shows a PASS / FAIL banner, totals, and a table of findings for each file, with failed files first. Recent scans are listed in the sidebar while the page is open.

Optional settings (set them before `streamlit run`):

| Environment variable | What it does |
|---|---|
| `ANTHROPIC_API_KEY` | Turns on the "Deeper review with Claude" switch. The code is then sent to Anthropic, and each file uses API credits |
| `GITHUB_TOKEN` | A GitHub personal access token. Raises GitHub's limit of about 60 anonymous requests an hour |

The website's logic lives in `perenic/scanner.py`, `perenic/report.py` and `perenic/github.py`, so it can be tested without a browser (`tests/test_website.py`).

## Command line

```bash
# 1. (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Review a file (rule-based checks only)
python -m perenic review examples/finance_sample.py --no-claude

# 4. Turn on Claude reviews
export ANTHROPIC_API_KEY=your-key-here   # Windows: set ANTHROPIC_API_KEY=...
python -m perenic review examples/finance_sample.py

# 5. Check against compliance documents (needs the API key)
python -m perenic review examples/finance_sample.py --compliance-docs compliance_docs/finance

# Review a snippet by pasting it in (press Ctrl+D when done)
python -m perenic review -

# Run the tests
pytest
```

The command exits with code `0` when the gate passes and `1` when it fails, so CI systems can block a merge.

## GitHub pull requests

`.github/workflows/perenic.yml` runs on every pull request:

1. runs the test suite, and
2. reviews the Python files the PR changed, then writes the report to the run's **Summary** page.

These settings are all optional and live under **Settings → Secrets and variables → Actions**:

| Setting | Where | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Secrets** tab | Turns on Claude reviews. Without it, only rule-based checks run |
| `PERENIC_COMPLIANCE_DOCS` | **Variables** tab | A folder in the repo, e.g. `compliance_docs/finance`. Turns on PAT Compliance (option B) |
| `PERENIC_COMPLIANCE_MCP_URL` | **Variables** tab | A remote MCP server URL. Turns on PAT Compliance (option A). Use this *or* the folder, not both |
| `PERENIC_COMPLIANCE_MCP_TOKEN` | **Secrets** tab | The remote MCP server's access token, if it needs one |

PAT Compliance also needs `ANTHROPIC_API_KEY` to be set.

## Compliance documents (PAT Compliance)

The code can also be checked against **your own compliance and regulation documents**: the official PCI DSS text, internal policies, audit findings and so on. PAT Compliance lets Claude search and read those documents through **MCP** (Model Context Protocol). Claude then reports each place where the code risks breaching a rule, with the document and section it relates to:

```
ERROR    line 17  card-data-logged (claude): The card number is written to the application log.
                  Risks breaching: example_internal_policy.md: SEC-1 Card data handling
  Rules checked:
    - example_internal_policy.md: SEC-1 Card data handling
    - pci_dss_summary.md: Requirement 3.5.1 Make the PAN unreadable wherever it is stored
```

There are two ways to connect the documents:

| | Option A: remote MCP server | Option B: local folder |
|---|---|---|
| Use | `--compliance-mcp https://…` | `--compliance-docs compliance_docs/finance` |
| How it works | Anthropic's API connects to the MCP server at that URL | Perenic starts its own MCP server (`perenic/compliance_server.py`) that reads the folder |
| Good for | Documents in a system that offers an MCP server (SharePoint, Confluence, Google Drive, …) | Private documents kept in the repo or on the build machine |
| Documents | Whatever the server provides | `.md`, `.txt` and `.pdf` files |
| Access token | `PERENIC_COMPLIANCE_MCP_TOKEN` environment variable, if the server needs one | Not needed |

How PAT Compliance decides:

- **A finding that cites a rule is always an error**, so it blocks the merge. A person should then confirm it by reading the cited rule.
- It receives the other PAT agents' findings, and checks whether those also break a documented rule.
- **It fails safe:** if the check can't run (no API key, or the MCP server is unreachable), the gate fails rather than passing unchecked code.
- Claude is told to cite only rules it actually read through MCP, and to treat document text as reference material, never as instructions.

**Starter documents:** `compliance_docs/finance` contains a short plain-English summary of selected PCI DSS requirements, plus an example internal policy. They are **not** the official texts. Replace them with your organisation's real documents (see `compliance_docs/README.md`).

**Cost and privacy:** compliance checks use Claude and read documents, so each review costs more than a plain review. The code and the document sections Claude reads are sent to Anthropic.

## Adding a new PAT agent

1. Create `perenic/agents/my_agent.py` with a class that inherits from `PATAgent`.
2. Give it a `name` and a `run(self, code, filename, inbox)` method that returns an `AgentReport`.
3. Use `self.post(topic, content)` to share results with the agents that run after it, and read `inbox` to see what earlier agents shared.
4. Add it to `build_agents()` in `perenic/scanner.py`. The website and the command line then both use it.

Reusable checks such as `hardcoded_secrets` and `sensitive_data_logged` live in `perenic/checks.py`.

## Roadmap

- [x] Orchestrator + PAT Code Reviewer
- [x] PAT Finance (PCI DSS)
- [x] PAT Compliance: check code against compliance documents over MCP
- [x] Website, first version: paste, upload or scan a public GitHub repository
- [ ] PerenicAI GitHub App: sign in with GitHub, scan private and company repositories, and check every pull request automatically
- [ ] Customer accounts and saved scan history
- [ ] On-server PAT agent that checks the customer's code continuously
- [ ] PAT Coverage Checker (runs tests with coverage)
- [ ] PAT Test Gap Recommender (suggests missing tests)
- [ ] Post review results as PR comments
