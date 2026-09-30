"""The one place that decides which PAT agents run.

Both the command line (`python -m perenic review ...`) and the website
(`streamlit run app.py`) call these functions, so they always give the
same PASS / FAIL answer for the same code.
"""

from perenic.agents import PATCodeReviewerAgent, PATComplianceAgent, PATFinanceAgent
from perenic.compliance import ComplianceSource
from perenic.orchestrator import GateResult, Orchestrator


def build_agents(use_claude: bool = True, compliance_source: ComplianceSource | None = None) -> list:
    """The PAT agents to run, in order.

    1. PAT Code Reviewer: general checks (plus a Claude review if allowed).
    2. PAT Finance: PCI DSS and money-handling checks. It also tells Claude
       what financial risks to look for.
    3. PAT Compliance (optional): checks the code against your compliance
       documents. It runs last so it can see what the others found.
    """
    guidance = PATFinanceAgent.claude_guidance
    agents = [
        PATCodeReviewerAgent(use_claude=use_claude, industry_guidance=guidance),
        PATFinanceAgent(),
    ]
    if compliance_source is not None:
        agents.append(PATComplianceAgent(guidance, compliance_source))
    return agents


def scan(files: dict[str, str], use_claude: bool = True) -> list[GateResult]:
    """Review several files and return one GateResult per file.

    `files` maps a file name to its code, e.g. {"payments.py": "def pay(): ..."}.
    """
    orchestrator = Orchestrator(build_agents(use_claude))
    return [orchestrator.review(code, name) for name, code in files.items()]
