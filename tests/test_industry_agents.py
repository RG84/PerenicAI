from pathlib import Path

from perenic.__main__ import main
from perenic.agents import PATFinanceAgent, PATHealthcareAgent

EXAMPLES = Path(__file__).parent.parent / "examples"


def healthcare_rules(code):
    return {f.rule for f in PATHealthcareAgent().run(code, "test.py", []).findings}


def finance_rules(code):
    return {f.rule for f in PATFinanceAgent().run(code, "test.py", []).findings}


# ---------------- PAT Healthcare ----------------


def test_healthcare_flags_phi_in_logs():
    assert "phi-in-logs" in healthcare_rules("logger.info('seen %s', patient.dob)\n")
    assert "phi-in-logs" in healthcare_rules("print(record['ssn'])\n")
    assert "phi-in-logs" in healthcare_rules("print(f'{patient_name} checked in')\n")


def test_healthcare_ignores_logs_without_phi():
    assert healthcare_rules("logger.info('server started on port %s', port)\n") == set()


def test_healthcare_flags_ssn_and_mrn_values():
    assert "real-patient-data" in healthcare_rules("x = 'SSN 123-45-6789'\n")
    assert "real-patient-data" in healthcare_rules("mrn = '00482913'\n")


def test_healthcare_flags_hardcoded_secrets():
    assert "hardcoded-secret" in healthcare_rules("DB_PASSWORD = 'hunter2'\n")
    assert "hardcoded-secret" in healthcare_rules("connect(api_key='abc123')\n")


def test_secret_loaded_from_environment_is_fine():
    assert healthcare_rules("import os\nDB_PASSWORD = os.environ['DB_PASSWORD']\n") == set()


# ---------------- PAT Finance ----------------


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


def test_short_terms_do_not_match_inside_other_words():
    # "pan" is a card term, but "company" should not trigger it.
    assert finance_rules("print(company)\n") == set()


# ---------------- Command line ----------------


def test_cli_industry_option(tmp_path):
    code = tmp_path / "pay.py"
    code.write_text('def pay():\n    """Pay."""\n    price = 9.99\n    return price\n')

    # Only the finance PAT agent knows float money is an error.
    assert main(["review", str(code), "--no-claude"]) == 0
    assert main(["review", str(code), "--no-claude", "--industry", "finance"]) == 1


def test_examples_fail_their_industry_gate():
    assert main(["review", str(EXAMPLES / "healthcare_sample.py"), "--no-claude", "--industry", "healthcare"]) == 1
    assert main(["review", str(EXAMPLES / "finance_sample.py"), "--no-claude", "--industry", "finance"]) == 1


def test_industry_guidance_reaches_claude(tmp_path, monkeypatch):
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
    main(["review", str(code), "--industry", "healthcare"])

    assert received["guidance"] == PATHealthcareAgent.claude_guidance
    assert "HIPAA" in received["guidance"]
