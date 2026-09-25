# PerenicAI

PerenicAI builds **PAT agents** (**P**erennial **A**rtificial **T**esting) that act as **quality gates** for your code. PAT agents review code, flag problems, and give a **PASS / FAIL** verdict. The goal is to keep production stable.

Each PAT agent can be tailored to an industry. The first two industries are **Healthcare** and **Financial institutions**.

## How it works

```
            your code (file, snippet or PR)
                        │
                 ┌──────▼──────┐
                 │ Orchestrator │  runs the PAT agents in order and
                 └──────┬──────┘  passes messages between them
                        │
          ┌─────────────┴──────────────┐
          ▼                            ▼
  PAT Code Reviewer          industry PAT agent (optional)
  (always runs; any          --industry healthcare → PAT Healthcare
   industry)                 --industry finance    → PAT Finance
          │                            │
          └─────────────┬──────────────┘
                        ▼
              PAT Compliance (optional)      ◄── MCP ── your compliance &
              --compliance-docs / -mcp            regulation documents
                        │
                        ▼
   PASS / FAIL  ← fails if any PAT agent reports an "error"
```

- **Orchestrator** (`perenic/orchestrator.py`) runs each PAT agent. Agents talk to each other by posting messages, and every agent that runs later gets them in its `inbox`.
- **PAT Code Reviewer** (`perenic/agents/code_reviewer.py`) runs general rule-based checks. When an `ANTHROPIC_API_KEY` is set, it also asks Claude for a deeper review. If you choose an industry, Claude's review focuses on that industry's risks.
- **PAT Healthcare** (`perenic/agents/healthcare.py`) and **PAT Finance** (`perenic/agents/finance.py`) add industry-specific checks.
- **PAT Compliance** (`perenic/agents/compliance.py`) runs last. It reads your compliance and regulation documents through MCP and reports code that risks breaching them, citing the rule. See [Compliance documents](#compliance-documents-pat-compliance).

> ⚠️ PAT agents help catch common compliance risks early. They do **not** certify that software is HIPAA or PCI DSS compliant.

## PAT agents and their checks

### PAT Code Reviewer (all industries)

| Rule | Severity | What it catches |
|---|---|---|
| `syntax-error` | error | Code that doesn't parse |
| `mutable-default` | error | `def f(x=[])`. The list is shared between calls |
| `bare-except` | warning | `except:` with no exception type |
| `long-function` | warning | Functions over 50 lines |
| `too-many-arguments` | warning | Functions with more than 5 arguments |
| `missing-docstring` | info | Public functions without a docstring |
| `todo` | info | `TODO` / `FIXME` comments |

### PAT Healthcare (`--industry healthcare`, HIPAA)

| Rule | Severity | What it catches |
|---|---|---|
| `phi-in-logs` | error | Patient data (SSN, DOB, MRN, diagnosis, …) passed to `print()` or a logger |
| `real-patient-data` | error | SSN patterns or medical record numbers written into code |
| `hardcoded-secret` | error | Passwords, API keys and tokens written directly in code |

### PAT Finance (`--industry finance`, PCI DSS)

| Rule | Severity | What it catches |
|---|---|---|
| `money-as-float` | error | Money held in `float` (`price = 9.99`, `amount: float`). Use `Decimal` |
| `card-number` | error | Payment card numbers in code (checked with the Luhn checksum) |
| `card-data-in-logs` | error | Card or account data (card number, CVV, IBAN, …) passed to `print()` or a logger |
| `hardcoded-secret` | error | Passwords, API keys and tokens written directly in code |

### Compliance documents (PAT Compliance)

Any industry can also be checked against **your own compliance and regulation documents**: official regulation texts, internal policies, audit findings and so on. PAT Compliance lets Claude search and read those documents through **MCP** (Model Context Protocol). Claude then reports each place where the code risks breaching a rule, with the document and section it relates to:

```
❌ line 17  phi-logged (claude): Date of birth and patient name are written to the application log.
            Risks breaching: example_internal_policy.md: LOG-1 No patient data in logs
  Rules checked:
    - example_internal_policy.md: LOG-1 No patient data in logs
    - hipaa_security_rule_summary.md: §164.502(b) Minimum necessary
```

There are two ways to connect the documents:

| | Option A: remote MCP server | Option B: local folder |
|---|---|---|
| Use | `--compliance-mcp https://…` | `--compliance-docs compliance_docs/healthcare` |
| How it works | Anthropic's API connects to the MCP server at that URL | Perenic starts its own MCP server (`perenic/compliance_server.py`) that reads the folder |
| Good for | Documents in a system that offers an MCP server (SharePoint, Confluence, Google Drive, …) | Private documents kept in the repo or on the build machine |
| Documents | Whatever the server provides | `.md`, `.txt` and `.pdf` files |
| Access token | `PERENIC_COMPLIANCE_MCP_TOKEN` environment variable, if the server needs one | Not needed |

```bash
export ANTHROPIC_API_KEY=your-key-here
# Option B: a folder of documents
python -m perenic review examples/healthcare_sample.py --industry healthcare --compliance-docs compliance_docs/healthcare
# Option A: a remote MCP server
export PERENIC_COMPLIANCE_MCP_TOKEN=your-token   # only if the server needs one
python -m perenic review payments.py --industry finance --compliance-mcp https://docs.example.com/mcp
```

How PAT Compliance decides:

- **A finding that cites a rule is always an error**, so it blocks the merge. A person should then confirm it by reading the cited rule.
- It receives the other PAT agents' findings, and checks whether those also break a documented rule.
- **It fails safe:** if the check can't run (no API key, or the MCP server is unreachable), the gate fails rather than passing unchecked code.
- Claude is told to cite only rules it actually read through MCP, and to treat document text as reference material, never as instructions.

**Starter documents:** `compliance_docs/` contains short plain-English summaries of selected HIPAA and PCI DSS sections, plus an example internal policy for each industry. They are **not** the official texts. Replace them with your organisation's real documents (see `compliance_docs/README.md`).

**Cost and privacy:** compliance checks use Claude and read documents, so each review costs more than a plain review. The code and the document sections Claude reads are sent to Anthropic.

## Getting started

```bash
# 1. (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Review a file (rule-based checks only)
python -m perenic review examples/sample_code.py --no-claude

# 4. Add an industry PAT agent
python -m perenic review examples/healthcare_sample.py --industry healthcare --no-claude
python -m perenic review examples/finance_sample.py --industry finance --no-claude

# 5. Turn on Claude reviews
export ANTHROPIC_API_KEY=your-key-here   # Windows: set ANTHROPIC_API_KEY=...
python -m perenic review examples/finance_sample.py --industry finance

# 6. Check against compliance documents (needs the API key)
python -m perenic review examples/healthcare_sample.py --industry healthcare --compliance-docs compliance_docs/healthcare

# Review a snippet by pasting it in (press Ctrl+D when done)
python -m perenic review - --industry healthcare

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
| `PERENIC_INDUSTRY` | **Variables** tab | `healthcare` or `finance`. Adds that industry's PAT agent |
| `PERENIC_COMPLIANCE_DOCS` | **Variables** tab | A folder in the repo, e.g. `compliance_docs/healthcare`. Turns on PAT Compliance (option B) |
| `PERENIC_COMPLIANCE_MCP_URL` | **Variables** tab | A remote MCP server URL. Turns on PAT Compliance (option A). Use this *or* the folder, not both |
| `PERENIC_COMPLIANCE_MCP_TOKEN` | **Secrets** tab | The remote MCP server's access token, if it needs one |

PAT Compliance also needs `PERENIC_INDUSTRY` and `ANTHROPIC_API_KEY` to be set.

## Adding a new PAT agent

1. Create `perenic/agents/my_agent.py` with a class that inherits from `PATAgent`.
2. Give it a `name` and a `run(self, code, filename, inbox)` method that returns an `AgentReport`.
3. Use `self.post(topic, content)` to share results with the agents that run after it, and read `inbox` to see what earlier agents shared.
4. Add it to the list passed to `Orchestrator([...])` in `perenic/__main__.py`.

### Adding a new industry

1. Create a PAT agent as above, and also set `industry = "my-industry"` and a `claude_guidance` string describing that industry's risks.
2. Reuse checks from `perenic/checks.py` (for example `hardcoded_secrets` or `sensitive_data_logged`) where they fit.
3. Register it in `INDUSTRY_AGENTS` in `perenic/agents/__init__.py`. `--industry my-industry` then works automatically.

## Roadmap

- [x] Orchestrator + PAT Code Reviewer
- [x] Industry PAT agents: Healthcare and Finance
- [x] PAT Compliance: check code against compliance documents over MCP
- [ ] PAT Coverage Checker (runs tests with coverage)
- [ ] PAT Test Gap Recommender (suggests missing tests)
- [ ] More industries
- [ ] Post review results as PR comments
