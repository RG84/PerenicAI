"""Reusable checks that industry PAT agents combine.

Each function takes a parsed syntax tree (from `ast.parse`) and returns a
list of Findings. Keeping them here means PAT Healthcare and PAT Finance
can share checks such as `hardcoded_secrets` without copying code.
"""

import ast
import re

from perenic.models import ERROR, Finding

SECRET_NAME = re.compile(r"password|passwd|pwd|secret|api_?key|token|private_?key|access_?key", re.IGNORECASE)
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
LOG_METHODS = {"debug", "info", "warning", "warn", "error", "critical", "exception", "log"}


def names_in(node) -> set[str]:
    """Every variable name, attribute name and string key used inside `node`.

    For `print(patient.ssn, record["dob"])` this returns {"print", "patient", "ssn", "record", "dob"}.
    """
    found = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            found.add(child.id.lower())
        elif isinstance(child, ast.Attribute):
            found.add(child.attr.lower())
        elif isinstance(child, ast.Subscript) and isinstance(child.slice, ast.Constant):
            found.add(str(child.slice.value).lower())
    return found


def name_has_term(name: str, term: str) -> bool:
    """True if `term` is a whole part of `name`.

    "patient_dob" has "dob" and "unit_prices" has "price", but "company" does
    not have "pan". Terms with underscores ("date_of_birth") may appear anywhere.
    """
    if "_" in term:
        return term in name
    parts = name.split("_")
    return term in parts or term + "s" in parts


def matches_any(names: set[str], terms: tuple[str, ...]) -> set[str]:
    """The names that contain one of the terms as a whole part."""
    return {name for name in names if any(name_has_term(name, term) for term in terms)}


def is_log_call(node) -> bool:
    """True for print(...) and logger.info(...)-style calls."""
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Name):
        return node.func.id == "print"
    return isinstance(node.func, ast.Attribute) and node.func.attr in LOG_METHODS


def sensitive_data_logged(tree, terms: tuple[str, ...], rule: str, what: str) -> list[Finding]:
    """Flag print/log calls whose arguments mention any of `terms`."""
    findings = []
    for node in ast.walk(tree):
        if is_log_call(node):
            args = node.args + [keyword.value for keyword in node.keywords]
            hits = set().union(*(matches_any(names_in(arg), terms) for arg in args)) if args else set()
            if hits:
                findings.append(
                    Finding(
                        rule,
                        f"{what} ({', '.join(sorted(hits))}) is written to a log or print. Mask or remove it.",
                        ERROR,
                        node.lineno,
                    )
                )
    return findings


def hardcoded_secrets(tree) -> list[Finding]:
    """Flag passwords, keys and tokens written directly in code, e.g. API_KEY = "abc123"."""
    findings = []

    def check(name: str, value, line: int):
        if SECRET_NAME.search(name) and isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value:
            findings.append(
                Finding(
                    "hardcoded-secret",
                    f"`{name}` is set to a literal value. Load secrets from environment variables or a secrets manager.",
                    ERROR,
                    line,
                )
            )

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                name = target.id if isinstance(target, ast.Name) else getattr(target, "attr", "")
                check(name, node.value, node.lineno)
        elif isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg:
                    check(keyword.arg, keyword.value, node.lineno)
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    check(key.value, value, node.lineno)
    return findings


def string_constants(tree):
    """Yield (text, line) for every string literal in the code."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value, node.lineno


def luhn_valid(digits: str) -> bool:
    """The Luhn checksum that every real card number passes."""
    total = 0
    for position, char in enumerate(reversed(digits)):
        number = int(char)
        if position % 2 == 1:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0
