"""PAT Finance: checks for software used by banks and payment companies (PCI DSS)."""

import ast
import re

from perenic import checks
from perenic.agents.base import PATAgent
from perenic.models import ERROR, AgentReport, Finding, Message

# Parts of variable names that suggest an amount of money.
MONEY_TERMS = (
    "amount", "price", "balance", "total", "cost", "fee", "payment",
    "salary", "wage", "deposit", "withdrawal", "refund", "charge", "principal",
)
# Parts of variable names that suggest card or account data.
CARD_TERMS = ("card_number", "cardnumber", "pan", "cvv", "cvc", "card", "account_number", "routing_number", "iban")
CARD_NUMBER = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")


class PATFinanceAgent(PATAgent):
    name = "pat-finance"
    industry = "finance"

    # Extra instructions added to the PAT Code Reviewer's Claude prompt.
    claude_guidance = (
        "This code runs in a financial institution and may be subject to PCI DSS and SOX. "
        "Pay special attention to: money stored or calculated as float instead of Decimal; "
        "rounding errors; card data (PAN, CVV) stored or logged; payments that could be "
        "charged twice (missing idempotency); race conditions when updating balances; "
        "missing audit trails for money movement; and hard-coded credentials."
    )

    def run(self, code: str, filename: str, inbox: list[Message]) -> AgentReport:
        report = AgentReport(agent_name=self.name)
        try:
            tree = ast.parse(code)
        except SyntaxError:
            report.summary = "Skipped: the code does not parse (see pat-code-reviewer)."
            return report

        report.findings += self.money_as_float(tree)
        report.findings += self.card_numbers(tree)
        report.findings += checks.sensitive_data_logged(tree, CARD_TERMS, "card-data-in-logs", "Card or account data")
        report.findings += checks.hardcoded_secrets(tree)
        report.findings.sort(key=lambda f: f.line or 0)

        report.summary = f"Finance (PCI DSS) checks found {len(report.findings)} issue(s)."
        self.post("finance.findings", report.findings)
        return report

    def money_as_float(self, tree) -> list[Finding]:
        """Flag money held in floats: `price = 9.99`, `float(amount)`, `balance: float`."""
        findings = []

        def flag(name: str, line: int):
            findings.append(
                Finding(
                    "money-as-float",
                    f"`{name}` looks like money but uses float, which causes rounding errors "
                    "(0.1 + 0.2 != 0.3). Use decimal.Decimal.",
                    ERROR,
                    line,
                )
            )

        for node in ast.walk(tree):
            # price = 9.99   or   price = float(text)
            if isinstance(node, ast.Assign):
                value_is_float = (isinstance(node.value, ast.Constant) and isinstance(node.value.value, float)) or (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "float"
                )
                if value_is_float:
                    names = set().union(*(checks.names_in(target) for target in node.targets))
                    for name in sorted(checks.matches_any(names, MONEY_TERMS)):
                        flag(name, node.lineno)
            # def pay(amount: float)   or   balance: float = ...
            elif isinstance(node, (ast.arg, ast.AnnAssign)):
                annotation = node.annotation
                name = node.arg if isinstance(node, ast.arg) else getattr(node.target, "id", "")
                is_float = isinstance(annotation, ast.Name) and annotation.id == "float"
                if is_float and checks.matches_any({name.lower()}, MONEY_TERMS):
                    flag(name, node.lineno)
        return findings

    def card_numbers(self, tree) -> list[Finding]:
        """Flag numbers that pass the card checksum (Luhn) written into the code."""
        findings = []
        for text, line in checks.string_constants(tree):
            for match in CARD_NUMBER.finditer(text):
                digits = re.sub(r"\D", "", match.group())
                if 13 <= len(digits) <= 19 and checks.luhn_valid(digits):
                    findings.append(
                        Finding(
                            "card-number",
                            "A payment card number is written into the code (PCI DSS). Even test cards "
                            "belong in test fixtures or configuration, not source code.",
                            ERROR,
                            line,
                        )
                    )
                    break
        return findings
