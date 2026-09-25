"""PAT Compliance: checks code against your compliance and regulation documents.

It runs after the other PAT agents and reads their findings from its inbox,
so it can check whether those problems also break a documented rule.
"""

from perenic import compliance, llm
from perenic.agents.base import PATAgent
from perenic.models import ERROR, AgentReport, Finding, Message


class PATComplianceAgent(PATAgent):
    name = "pat-compliance"

    def __init__(self, industry_guidance: str, source: compliance.ComplianceSource):
        super().__init__()
        self.industry_guidance = industry_guidance
        self.source = source

    def run(self, code: str, filename: str, inbox: list[Message]) -> AgentReport:
        report = AgentReport(agent_name=self.name)

        # You asked for a compliance check, so if it can't run, the gate
        # fails rather than passing code that was never checked.
        if not llm.claude_available():
            report.findings.append(
                Finding(
                    "compliance-review-unavailable",
                    "Compliance documents were given but ANTHROPIC_API_KEY is not set, so they could not be checked.",
                    ERROR,
                )
            )
            report.summary = "Compliance review did not run."
            return report

        try:
            result = compliance.review(code, filename, self.industry_guidance, self.earlier_findings(inbox), self.source)
        except Exception as error:
            report.findings.append(
                Finding("compliance-review-failed", f"Compliance review could not finish: {error}", ERROR)
            )
            report.summary = "Compliance review did not finish."
            return report

        report.findings = sorted(self.to_findings(result["findings"]), key=lambda f: f.line or 0)
        report.rules_checked = result["rules_checked"]
        report.summary = result["summary"]

        self.post("compliance.findings", report.findings)
        return report

    def to_findings(self, items: list[dict]) -> list[Finding]:
        """Turn Claude's answer into Findings. Any risk of breaching a documented rule blocks the merge."""
        findings = []
        for item in items:
            regulation = item["regulation"].strip() or None
            findings.append(
                Finding(
                    rule=item["rule"],
                    message=item["message"],
                    severity=ERROR if regulation else item["severity"],
                    line=item["line"] or None,
                    source="claude",
                    regulation=regulation,
                )
            )
        return findings

    def earlier_findings(self, inbox: list[Message]) -> list[str]:
        """One line per finding that earlier PAT agents shared, e.g. 'line 7: mutable-default (...)'."""
        lines = []
        for message in inbox:
            for finding in message.content if isinstance(message.content, list) else []:
                where = f"line {finding.line}" if finding.line else "file"
                lines.append(f"{where}: {finding.rule} ({message.sender}): {finding.message}")
        return lines
