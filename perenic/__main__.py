"""Command-line entry point.

Examples:
    python -m perenic review my_file.py
    python -m perenic review a.py b.py --no-claude
    cat snippet.py | python -m perenic review -
"""

import argparse
import sys

from perenic import llm
from perenic.agents import CodeReviewerAgent
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
                lines.append(f"| {ICONS.get(f.severity, '')} | {f.line or ''} | {f.rule} | {f.source} | {message} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="perenic", description="PerenicAI quality gate")
    subcommands = parser.add_subparsers(dest="command", required=True)

    review = subcommands.add_parser("review", help="Review one or more Python files")
    review.add_argument("files", nargs="+", help="Files to review, or - to read from stdin")
    review.add_argument("--no-claude", action="store_true", help="Only run the rule-based checks")
    review.add_argument("--markdown", action="store_true", help="Print a Markdown report (used by GitHub Actions)")

    args = parser.parse_args(argv)

    use_claude = not args.no_claude
    if use_claude and not llm.claude_available():
        print("Note: ANTHROPIC_API_KEY not set, so only rule-based checks will run.", file=sys.stderr)

    orchestrator = Orchestrator([CodeReviewerAgent(use_claude=use_claude)])

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
