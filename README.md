# PerenicAI

PerenicAI builds AI agents that act as **quality gates** for your code. Perenic agents review code, flag problems, and give a **PASS / FAIL** verdict. The goal is to keep production stable.

## How it works

```
            your code (file, snippet or PR)
                        │
                 ┌──────▼──────┐
                 │ Orchestrator │  runs the agents in order and passes
                 └──────┬──────┘  messages between them
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
  Code Reviewer   (future) Coverage   (future) Test Gap
     agent         Checker agent      Recommender agent
        │
        ▼
   PASS / FAIL  ← fails if any agent reports an "error"
```

- **Orchestrator** (`perenic/orchestrator.py`) runs each agent. Agents talk to each other by posting messages, and every agent that runs later gets them in its `inbox`.
- **Code Reviewer** (`perenic/agents/code_reviewer.py`) always runs rule-based checks. When an `ANTHROPIC_API_KEY` is set, it also asks Claude for a deeper review.

### Rule-based checks

| Rule | Severity | What it catches |
|---|---|---|
| `syntax-error` | error | Code that doesn't parse |
| `mutable-default` | error | `def f(x=[])`. The list is shared between calls |
| `bare-except` | warning | `except:` with no exception type |
| `long-function` | warning | Functions over 50 lines |
| `too-many-arguments` | warning | Functions with more than 5 arguments |
| `missing-docstring` | info | Public functions without a docstring |
| `todo` | info | `TODO` / `FIXME` comments |

## Getting started

```bash
# 1. (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Review a file (rule-based checks only)
python -m perenic review examples/sample_code.py --no-claude

# 4. Turn on Claude reviews
export ANTHROPIC_API_KEY=your-key-here   # Windows: set ANTHROPIC_API_KEY=...
python -m perenic review examples/sample_code.py

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

To turn on Claude reviews in CI, add a repository secret named `ANTHROPIC_API_KEY` (**Settings → Secrets and variables → Actions**). Without it, only the rule-based checks run.

## Adding a new agent

1. Create `perenic/agents/my_agent.py` with a class that inherits from `BaseAgent`.
2. Give it a `name` and a `run(self, code, filename, inbox)` method that returns an `AgentReport`.
3. Use `self.post(topic, content)` to share results with the agents that run after it, and read `inbox` to see what earlier agents shared.
4. Add it to the list passed to `Orchestrator([...])` in `perenic/__main__.py`.

## Roadmap

- [x] Orchestrator + Code Reviewer agent
- [ ] Coverage Checker agent (runs tests with coverage)
- [ ] Test Gap Recommender agent (suggests missing tests)
- [ ] Post review results as PR comments
