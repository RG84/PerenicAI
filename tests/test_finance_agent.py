from pathlib import Path

from perenic.__main__ import main
from perenic.agents import PATFinanceAgent

EXAMPLES = Path(__file__).parent.parent / "examples"


def finance_rules(code):
    return {f.rule for f in PATFinanceAgent().run(code, "test.py", []).findings}


def test_finance_flags_money_as_float():
    assert "money-as-float" in finance_rules("price = 9.99\n")
    assert "money-as-float" in finance_rules("refund = float(text)\n")
    assert "money-as-float" in finance_rules("def pay(amount: float):\n    pass\n")


def test_finance_allows_decimal_money_and_non_money_floats():
    assert finance_rules("from decimal import Decimal\nprice = Decimal('9.99')\n") == set()
    assert finance_rules("ratio = 0.5\n") == set()


def test_finance_flags_luhn_valid_card_numbers_only():
    assert "card-number" in finance_rules("CARD = '4111 1111 1111 1111'\n")
    assert "card-number" not in finance_rules("ORDER_ID = '4111 1111 1111 1112'\n")


def test_finance_flags_card_data_in_logs():
    assert "card-data-in-logs" in finance_rules("logger.info('charging %s', card_number)\n")
    assert "card-data-in-logs" in finance_rules("print(record['cvv'])\n")


def test_finance_ignores_logs_without_card_data():
    assert finance_rules("logger.info('server started on port %s', port)\n") == set()


def test_short_terms_do_not_match_inside_other_words():
    # "pan" is a card term, but "company" should not trigger it.
    assert finance_rules("print(company)\n") == set()


def test_finance_flags_hardcoded_secrets():
    assert "hardcoded-secret" in finance_rules("DB_PASSWORD = 'hunter2'\n")
    assert "hardcoded-secret" in finance_rules("connect(api_key='abc123')\n")


def test_secret_loaded_from_environment_is_fine():
    assert finance_rules("import os\nDB_PASSWORD = os.environ['DB_PASSWORD']\n") == set()


# ---------------- Command line ----------------


def test_cli_always_runs_the_finance_checks(tmp_path):
    code = tmp_path / "pay.py"
    code.write_text('def pay():\n    """Pay."""\n    price = 9.99\n    return price\n')
    # Float money is a PAT Finance error, and PAT Finance always runs.
    assert main(["review", str(code), "--no-claude"]) == 1


def test_finance_example_fails_the_gate():
    assert main(["review", str(EXAMPLES / "finance_sample.py"), "--no-claude"]) == 1


def test_finance_guidance_reaches_claude(tmp_path, monkeypatch):
    """Replace the real Claude call with a fake one and check what it receives."""
    from perenic import llm

    received = {}

    def fake_review(code, filename, industry_guidance=""):
        received["guidance"] = industry_guidance
        return {"summary": "Looks fine.", "findings": []}

    monkeypatch.setattr(llm, "claude_available", lambda: True)
    monkeypatch.setattr(llm, "review_with_claude", fake_review)

    code = tmp_path / "ok.py"
    code.write_text('def ok():\n    """Ok."""\n    return 1\n')
    main(["review", str(code)])

    assert received["guidance"] == PATFinanceAgent.claude_guidance
    assert "PCI DSS" in received["guidance"]
