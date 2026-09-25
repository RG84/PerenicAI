"""PAT Healthcare: checks for software that handles patient data (HIPAA)."""

import ast
import re

from perenic import checks
from perenic.agents.base import PATAgent
from perenic.models import ERROR, AgentReport, Finding, Message

# Parts of variable names that suggest protected health information (PHI).
PHI_TERMS = (
    "ssn", "social_security", "dob", "date_of_birth", "birth_date", "birthdate",
    "mrn", "medical_record", "diagnosis", "patient", "insurance_id", "member_id",
    "prescription", "medication", "health_record",
)
MRN_VALUE = re.compile(r"^\s*[A-Z]{0,3}\d{6,10}\s*$")


class PATHealthcareAgent(PATAgent):
    name = "pat-healthcare"
    industry = "healthcare"

    # Extra instructions added to the PAT Code Reviewer's Claude prompt.
    claude_guidance = (
        "This code runs in a healthcare organisation and may handle protected health "
        "information (PHI) covered by HIPAA. Pay special attention to: PHI exposed in "
        "logs, error messages or API responses; missing access control or audit logging "
        "around patient records; PHI stored or sent without encryption; hard-coded "
        "credentials; and real patient data in code or tests."
    )

    def run(self, code: str, filename: str, inbox: list[Message]) -> AgentReport:
        report = AgentReport(agent_name=self.name)
        try:
            tree = ast.parse(code)
        except SyntaxError:
            report.summary = "Skipped: the code does not parse (see pat-code-reviewer)."
            return report

        report.findings += checks.sensitive_data_logged(tree, PHI_TERMS, "phi-in-logs", "Patient data")
        report.findings += checks.hardcoded_secrets(tree)
        report.findings += self.real_patient_data(tree)
        report.findings.sort(key=lambda f: f.line or 0)

        report.summary = f"Healthcare (HIPAA) checks found {len(report.findings)} issue(s)."
        self.post("healthcare.findings", report.findings)
        return report

    def real_patient_data(self, tree) -> list[Finding]:
        """Flag SSNs anywhere, and MRN-like values assigned to MRN variables."""
        findings = []
        for text, line in checks.string_constants(tree):
            if checks.SSN.search(text):
                findings.append(
                    Finding(
                        "real-patient-data",
                        "A Social Security Number pattern appears in the code. Use clearly fake or generated test data.",
                        ERROR,
                        line,
                    )
                )

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                names = set().union(*(checks.names_in(target) for target in node.targets))
                value = node.value.value
                if checks.matches_any(names, ("mrn", "medical_record")) and MRN_VALUE.match(str(value)):
                    findings.append(
                        Finding(
                            "real-patient-data",
                            "A medical record number is written into the code. Use generated test data instead.",
                            ERROR,
                            node.lineno,
                        )
                    )
        return findings
