"""The PAT Code Reviewer agent: a general review that suits any industry.

It always runs a set of simple rule-based checks written in plain Python.
If an Anthropic API key is set, it also asks Claude for a deeper review.
"""

import ast

from perenic import llm
from perenic.agents.base import PATAgent
from perenic.models import ERROR, INFO, WARNING, AgentReport, Finding, Message

MAX_FUNCTION_LINES = 50
MAX_ARGUMENTS = 5


class PATCodeReviewerAgent(PATAgent):
    name = "pat-code-reviewer"

    def __init__(self, use_claude: bool = True, industry_guidance: str = ""):
        super().__init__()
        self.use_claude = use_claude
        # Set by the CLI when an industry is chosen, so Claude knows what to focus on.
        self.industry_guidance = industry_guidance

    def run(self, code: str, filename: str, inbox: list[Message]) -> AgentReport:
        report = AgentReport(agent_name=self.name)
        report.findings.extend(self.rule_checks(code))

        if self.use_claude and llm.claude_available():
            try:
                result = llm.review_with_claude(code, filename, self.industry_guidance)
                report.summary = result["summary"]
                for item in result["findings"]:
                    report.findings.append(
                        Finding(
                            rule=item["rule"],
                            message=item["message"],
                            severity=item["severity"],
                            line=item["line"] or None,
                            source="claude",
                        )
                    )
            except Exception as error:  # keep going with the rule-based results
                report.findings.append(
                    Finding("claude-unavailable", f"Claude review skipped: {error}", INFO)
                )

        if not report.summary:
            report.summary = f"Rule-based review found {len(report.findings)} issue(s)."

        # Let other agents (added later) see what we found.
        self.post("review.findings", report.findings)
        return report

    # ------------------------------------------------------------------
    # Rule-based checks. Each one looks at the code's syntax tree (AST),
    # which is Python's own structured view of the source code.
    # ------------------------------------------------------------------

    def rule_checks(self, code: str) -> list[Finding]:
        try:
            tree = ast.parse(code)
        except SyntaxError as error:
            return [Finding("syntax-error", f"Code does not parse: {error.msg}", ERROR, error.lineno)]

        findings = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                findings.extend(self.check_function(node))
            elif isinstance(node, ast.ExceptHandler) and node.type is None:
                findings.append(
                    Finding(
                        "bare-except",
                        "Bare `except:` catches every error, even Ctrl+C. Catch a specific exception.",
                        WARNING,
                        node.lineno,
                    )
                )

        for number, text in enumerate(code.splitlines(), start=1):
            if "TODO" in text or "FIXME" in text:
                findings.append(Finding("todo", "Unfinished work (TODO/FIXME) left in code.", INFO, number))

        return sorted(findings, key=lambda f: f.line or 0)

    def check_function(self, node) -> list[Finding]:
        findings = []
        name = node.name

        length = node.end_lineno - node.lineno + 1
        if length > MAX_FUNCTION_LINES:
            findings.append(
                Finding(
                    "long-function",
                    f"`{name}` is {length} lines long; consider splitting it (limit {MAX_FUNCTION_LINES}).",
                    WARNING,
                    node.lineno,
                )
            )

        arg_count = len(node.args.args) + len(node.args.kwonlyargs)
        if arg_count > MAX_ARGUMENTS:
            findings.append(
                Finding(
                    "too-many-arguments",
                    f"`{name}` takes {arg_count} arguments; consider grouping them (limit {MAX_ARGUMENTS}).",
                    WARNING,
                    node.lineno,
                )
            )

        for default in node.args.defaults + node.args.kw_defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                findings.append(
                    Finding(
                        "mutable-default",
                        f"`{name}` uses a list/dict/set as a default argument; it is shared between calls. Use None instead.",
                        ERROR,
                        node.lineno,
                    )
                )

        if not name.startswith("_") and ast.get_docstring(node) is None:
            findings.append(
                Finding("missing-docstring", f"Public function `{name}` has no docstring.", INFO, node.lineno)
            )

        return findings
