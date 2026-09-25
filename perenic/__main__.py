"""Command-line entry point.

Examples:
    python -m perenic review my_file.py
    python -m perenic review a.py b.py --no-claude
    python -m perenic review payments.py --industry finance
    python -m perenic review payments.py --industry finance --compliance-docs compliance_docs/finance
    python -m perenic review payments.py --industry finance --compliance-mcp https://example.com/mcp
    cat snippet.py | python -m perenic review -
"""

import argparse
import os
import sys

from perenic import llm
from perenic.compliance import ComplianceSource
from perenic.agents import INDUSTRY_AGENTS, PATCodeReviewerAgent, PATComplianceAgent
from perenic.orchestrator import GateResult, Orchestrator

ICONS = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}


def read_code(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as file:
        return file.read()


def format_text(result: GateResult) -> str:
    lines = [f"\n=== {result.filename}: {'PASS' if result.passed else 'FAIL'} ==="]
    for report in result.reports:
        lines.append(f"[{report.agent_name}] {report.summary}")
        for f in report.findings:
            where = f"line {f.line}" if f.line else "file"
            lines.append(f"  {f.severity.upper():8} {where:>9}  {f.rule} ({f.source}): {f.message}")
            if f.regulation:
                lines.append(f"{'':21}Risks breaching: {f.regulation}")
        if report.rules_checked:
            lines.append("  Rules checked:")
            lines.extend(f"    - {rule}" for rule in report.rules_checked)
    return "\n".join(lines)


def format_markdown(result: GateResult) -> str:
    lines = [f"### {'✅' if result.passed else '❌'} `{result.filename}`: {'PASS' if result.passed else 'FAIL'}"]
    for report in result.reports:
        lines.append(f"\n**{report.agent_name}**: {report.summary}\n")
        if report.findings:
            lines.append("| | Line | Rule | Source | Message |")
            lines.append("|---|---|---|---|---|")
            for f in report.findings:
                message = f.message.replace("|", "\\|")
                if f.regulation:
                    regulation = f.regulation.replace("|", "\\|")
                    message += f"<br>**Risks breaching:** {regulation}"
                lines.append(f"| {ICONS.get(f.severity, '')} | {f.line or ''} | {f.rule} | {f.source} | {message} |")
        if report.rules_checked:
            lines.append(f"\n<details><summary>Rules checked ({len(report.rules_checked)})</summary>\n")
            lines.extend(f"- {rule}" for rule in report.rules_checked)
            lines.append("\n</details>")
    return "\n".join(lines)


def build_agents(args, use_claude: bool) -> list:
    """The PAT agents to run, in order.

    The general PAT Code Reviewer always runs first. If an industry is chosen,
    its PAT agent runs next and tunes the Claude review. PAT Compliance runs
    last, so it can see what the other PAT agents found.
    """
    industry_agent = INDUSTRY_AGENTS[args.industry]() if args.industry else None
    guidance = industry_agent.claude_guidance if industry_agent else ""

    agents = [PATCodeReviewerAgent(use_claude=use_claude, industry_guidance=guidance)]
    if industry_agent:
        agents.append(industry_agent)
    if args.compliance_docs or args.compliance_mcp:
        source = ComplianceSource(
            docs_folder=args.compliance_docs,
            mcp_url=args.compliance_mcp,
            mcp_token=os.environ.get("PERENIC_COMPLIANCE_MCP_TOKEN"),
        )
        agents.append(PATComplianceAgent(guidance, source))
    return agents


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="perenic", description="PerenicAI PAT quality gate")
    subcommands = parser.add_subparsers(dest="command", required=True)

    review = subcommands.add_parser("review", help="Review one or more Python files")
    review.add_argument("files", nargs="+", help="Files to review, or - to read from stdin")
    review.add_argument(
        "--industry",
        choices=sorted(INDUSTRY_AGENTS),
        help="Add the PAT agent for this industry and tune the Claude review to it",
    )
    sources = review.add_mutually_exclusive_group()
    sources.add_argument(
        "--compliance-docs",
        metavar="FOLDER",
        help="Check the code against the compliance documents in this folder (.md, .txt, .pdf)",
    )
    sources.add_argument(
        "--compliance-mcp",
        metavar="URL",
        help="Check the code against documents served by this remote MCP server. "
        "Put its access token, if needed, in the PERENIC_COMPLIANCE_MCP_TOKEN environment variable",
    )
    review.add_argument("--no-claude", action="store_true", help="Only run the rule-based checks")
    review.add_argument("--markdown", action="store_true", help="Print a Markdown report (used by GitHub Actions)")

    args = parser.parse_args(argv)
    wants_compliance = bool(args.compliance_docs or args.compliance_mcp)
    if wants_compliance and not args.industry:
        review.error("--compliance-docs and --compliance-mcp need --industry")
    if wants_compliance and args.no_claude:
        review.error("compliance checks need Claude, so they can't be combined with --no-claude")

    use_claude = not args.no_claude
    if use_claude and not llm.claude_available():
        print("Note: ANTHROPIC_API_KEY not set, so only rule-based checks will run.", file=sys.stderr)

    orchestrator = Orchestrator(build_agents(args, use_claude))

    all_passed = True
    for path in args.files:
        name = "<stdin>" if path == "-" else path
        result = orchestrator.review(read_code(path), name)
        print(format_markdown(result) if args.markdown else format_text(result))
        all_passed = all_passed and result.passed

    # Exit code 0 means "gate passed"; 1 means "gate failed". CI tools use this.
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
