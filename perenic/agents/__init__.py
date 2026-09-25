from perenic.agents.base import PATAgent
from perenic.agents.code_reviewer import PATCodeReviewerAgent
from perenic.agents.finance import PATFinanceAgent
from perenic.agents.healthcare import PATHealthcareAgent

# Industry name (used by --industry) -> the PAT agent for that industry.
INDUSTRY_AGENTS = {
    "healthcare": PATHealthcareAgent,
    "finance": PATFinanceAgent,
}

__all__ = ["INDUSTRY_AGENTS", "PATAgent", "PATCodeReviewerAgent", "PATFinanceAgent", "PATHealthcareAgent"]
