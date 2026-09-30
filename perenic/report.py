"""Turn scan results into simple tables and totals for the website.

These functions don't use Streamlit, so they can be tested with pytest.
"""

from datetime import datetime

from perenic.models import ERROR, INFO, WARNING
from perenic.orchestrator import GateResult

ICONS = {ERROR: "❌ Error", WARNING: "⚠️ Warning", INFO: "ℹ️ Info"}
SEVERITY_ORDER = {ERROR: 0, WARNING: 1, INFO: 2}
AGENT_LABELS = {
    "pat-code-reviewer": "Code Reviewer",
    "pat-finance": "Finance (PCI DSS)",
    "pat-compliance": "Compliance",
}


def summarize(results: list[GateResult]) -> dict:
    """Totals for the top of the results page."""
    findings = [f for result in results for report in result.reports for f in report.findings]
    return {
        "passed": all(result.passed for result in results),
        "files": len(results),
        "failed_files": sum(1 for result in results if not result.passed),
        "errors": sum(1 for f in findings if f.severity == ERROR),
        "warnings": sum(1 for f in findings if f.severity == WARNING),
        "info": sum(1 for f in findings if f.severity == INFO),
    }


def finding_rows(result: GateResult) -> list[dict]:
    """One row per finding for one file, most serious first."""
    rows = []
    for report in result.reports:
        for f in report.findings:
            rows.append(
                {
                    "Severity": ICONS.get(f.severity, f.severity),
                    "Line": f.line or "",
                    "Rule": f.rule,
                    "Found by": AGENT_LABELS.get(report.agent_name, report.agent_name)
                    + (" + Claude" if f.source == "claude" else ""),
                    "What to fix": f.message,
                    "Risks breaching": f.regulation or "",
                    "_order": (SEVERITY_ORDER.get(f.severity, 3), f.line or 0),
                }
            )
    rows.sort(key=lambda row: row["_order"])
    for row in rows:
        del row["_order"]
    return rows


def history_entry(source: str, results: list[GateResult]) -> dict:
    """A one-line record of a scan for the 'Recent scans' list."""
    totals = summarize(results)
    return {
        "Time": datetime.now().strftime("%H:%M"),
        "Code": source,
        "Result": "✅ PASS" if totals["passed"] else "❌ FAIL",
        "Files": totals["files"],
        "Errors": totals["errors"],
    }
