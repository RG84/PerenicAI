from perenic.agents import PATCodeReviewerAgent


def rules_found(code):
    agent = PATCodeReviewerAgent(use_claude=False)
    return {f.rule for f in agent.rule_checks(code)}


def test_clean_code_has_no_findings():
    code = 'def greet(name):\n    """Say hello."""\n    return f"Hello {name}"\n'
    assert rules_found(code) == set()


def test_detects_mutable_default():
    assert "mutable-default" in rules_found("def f(x=[]):\n    return x\n")


def test_detects_bare_except():
    code = "try:\n    pass\nexcept:\n    pass\n"
    assert "bare-except" in rules_found(code)


def test_detects_too_many_arguments():
    assert "too-many-arguments" in rules_found("def f(a, b, c, d, e, g):\n    pass\n")


def test_detects_long_function():
    body = "".join("    x = 1\n" for _ in range(60))
    assert "long-function" in rules_found('def f():\n    """Doc."""\n' + body)


def test_detects_missing_docstring_only_for_public_functions():
    assert "missing-docstring" in rules_found("def public():\n    pass\n")
    assert "missing-docstring" not in rules_found("def _private():\n    pass\n")


def test_detects_todo():
    assert "todo" in rules_found("x = 1  # TODO: fix\n")


def test_syntax_error_is_reported():
    assert rules_found("def broken(:\n") == {"syntax-error"}
