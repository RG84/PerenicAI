"""Tests for the logic behind the website (app.py).

The page itself needs Streamlit, but everything it calculates lives in
perenic/scanner.py, perenic/report.py and perenic/github.py, tested here.
"""

import json

import pytest

from perenic import github, report
from perenic.scanner import build_agents, scan

BAD = "def charge(card_number, amount: float):\n    print(card_number)\n"
GOOD = 'def add(a, b):\n    """Add two numbers."""\n    return a + b\n'


# ---------------- scanner ----------------


def test_scan_runs_code_reviewer_and_finance_agents():
    assert [agent.name for agent in build_agents(use_claude=False)] == ["pat-code-reviewer", "pat-finance"]


def test_scan_gives_one_result_per_file():
    results = scan({"bad.py": BAD, "good.py": GOOD}, use_claude=False)
    assert {r.filename: r.passed for r in results} == {"bad.py": False, "good.py": True}


# ---------------- report ----------------


def test_summarize_counts_files_and_findings():
    totals = report.summarize(scan({"bad.py": BAD, "good.py": GOOD}, use_claude=False))
    assert totals["passed"] is False
    assert totals["files"] == 2
    assert totals["failed_files"] == 1
    assert totals["errors"] >= 2  # money-as-float and card-data-in-logs


def test_finding_rows_put_errors_first_and_use_friendly_names():
    code = "def charge(card_number, amount: float):\n    print(card_number)\n"
    rows = report.finding_rows(scan({"bad.py": code}, use_claude=False)[0])
    assert rows[0]["Severity"] == "❌ Error"
    assert "Finance (PCI DSS)" in {row["Found by"] for row in rows}
    assert rows[-1]["Rule"] == "missing-docstring"  # an info finding, so last


def test_history_entry():
    entry = report.history_entry("bad.py", scan({"bad.py": BAD}, use_claude=False))
    assert entry["Code"] == "bad.py"
    assert entry["Result"] == "❌ FAIL"
    assert entry["Files"] == 1


# ---------------- github ----------------


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://github.com/RG84/PerenicAI", ("RG84", "PerenicAI", None)),
        ("github.com/RG84/PerenicAI/", ("RG84", "PerenicAI", None)),
        ("https://github.com/RG84/PerenicAI.git", ("RG84", "PerenicAI", None)),
        ("https://github.com/RG84/PerenicAI/tree/dev", ("RG84", "PerenicAI", "dev")),
    ],
)
def test_parse_repo_url(url, expected):
    assert github.parse_repo_url(url) == expected


def test_parse_repo_url_rejects_other_links():
    with pytest.raises(github.GitHubError):
        github.parse_repo_url("https://gitlab.com/a/b")


def test_library_and_non_python_files_are_skipped():
    assert github.is_wanted("src/payments.py", 1000)
    assert not github.is_wanted("README.md", 1000)
    assert not github.is_wanted(".venv/lib/thing.py", 1000)
    assert not github.is_wanted("huge.py", github.MAX_FILE_BYTES + 1)


def test_fetch_python_files_downloads_only_python(monkeypatch):
    tree = {
        "tree": [
            {"path": "pay.py", "type": "blob", "size": 50},
            {"path": "README.md", "type": "blob", "size": 50},
            {"path": "venv/x.py", "type": "blob", "size": 50},
            {"path": "src", "type": "tree"},
        ]
    }
    pages = {
        "https://api.github.com/repos/acme/bank": {"default_branch": "main"},
        "https://api.github.com/repos/acme/bank/git/trees/main?recursive=1": tree,
    }
    requested = []

    def fake_download(url):
        requested.append(url)
        if url in pages:
            return json.dumps(pages[url]).encode()
        assert url == "https://raw.githubusercontent.com/acme/bank/main/pay.py"
        return b"price = 9.99\n"

    monkeypatch.setattr(github, "_download", fake_download)
    repo = github.fetch_python_files("https://github.com/acme/bank")

    assert repo.files == {"pay.py": "price = 9.99\n"}
    assert repo.skipped == 1  # venv/x.py
    assert repo.label == "acme/bank (main)"
    assert len(requested) == 3


def test_repository_without_python_is_reported(monkeypatch):
    def fake_download(url):
        return json.dumps({"tree": [{"path": "index.js", "type": "blob", "size": 5}]}).encode()

    monkeypatch.setattr(github, "_download", fake_download)
    with pytest.raises(github.GitHubError, match="No Python files"):
        github.fetch_python_files("https://github.com/acme/web/tree/main")
