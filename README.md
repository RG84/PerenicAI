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
   PASS / FAIL  ← fails if any PAT agent reports an "error"
```

- **Orchestrator** (`perenic/orchestrator.py`) runs each PAT agent. Agents talk to each other by posting messages, and every agent that runs later gets them in its `inbox`.
- **PAT Code Reviewer** (`perenic/agents/code_reviewer.py`) runs general rule-based checks. When an `ANTHROPIC_API_KEY` is set, it also asks Claude for a deeper review. If you choose an industry, Claude's review focuses on that industry's risks.
- **PAT Healthcare** (`perenic/agents/healthcare.py`) and **PAT Finance** (`perenic/agents/finance.py`) add industry-specific checks.

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

Both settings are optional and live under **Settings → Secrets and variables → Actions**:

| Setting | Where | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Secrets** tab | Turns on Claude reviews. Without it, only rule-based checks run |
| `PERENIC_INDUSTRY` | **Variables** tab | `healthcare` or `finance`. Adds that industry's PAT agent |

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
- [ ] PAT Coverage Checker (runs tests with coverage)
- [ ] PAT Test Gap Recommender (suggests missing tests)
- [ ] More industries
- [ ] Post review results as PR comments
