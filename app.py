"""The PerenicAI website (first version), built with Streamlit.

Start it with:
    streamlit run app.py
Then open the link it prints (usually http://localhost:8501).

How the page works: Streamlit runs this whole file from top to bottom every
time someone clicks a button. Anything we want to remember between clicks
(the latest results, the list of recent scans) lives in `st.session_state`.
"""

import streamlit as st

from perenic import github, llm, report
from perenic.scanner import scan

st.set_page_config(page_title="PerenicAI · PAT Finance", page_icon="🛡️", layout="wide")

# Things to remember between clicks.
if "history" not in st.session_state:
    st.session_state.history = []  # recent scans, newest first
if "latest" not in st.session_state:
    st.session_state.latest = None  # the scan to show on screen


def run_scan(files: dict[str, str], source: str, use_claude: bool) -> None:
    """Run the PAT agents on `files` and remember the results."""
    with st.spinner(f"PAT agents are checking {len(files)} file(s)…"):
        results = scan(files, use_claude=use_claude)
    st.session_state.latest = {"source": source, "results": results}
    st.session_state.history.insert(0, report.history_entry(source, results))


def show_results(source: str, results: list) -> None:
    """The PASS / FAIL banner, the totals, then one section per file."""
    totals = report.summarize(results)
    st.subheader(f"Results: {source}")
    if totals["passed"]:
        st.success("**PASS**: no blocking problems found. This code can go ahead.")
    else:
        st.error(
            f"**FAIL**: {totals['failed_files']} of {totals['files']} file(s) have blocking problems. "
            "Fix the ❌ errors below before this code reaches production."
        )

    columns = st.columns(4)
    columns[0].metric("Files checked", totals["files"])
    columns[1].metric("Errors (block release)", totals["errors"])
    columns[2].metric("Warnings", totals["warnings"])
    columns[3].metric("Suggestions", totals["info"])

    # Failed files first, so the problems are at the top.
    for result in sorted(results, key=lambda r: (r.passed, r.filename)):
        icon = "✅" if result.passed else "❌"
        with st.expander(f"{icon} {result.filename}", expanded=not result.passed):
            rows = report.finding_rows(result)
            if rows:
                st.dataframe(rows, hide_index=True)
            else:
                st.write("No findings. Nice work.")


# ---------------------------------------------------------------------------
# Sidebar: settings and recent scans
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🛡️ PerenicAI")
    st.caption("PAT agents: quality gates for financial software")

    claude_ready = llm.claude_available()
    use_claude = st.toggle(
        "Deeper review with Claude",
        value=False,
        disabled=not claude_ready,
        help="Adds an AI review on top of the rule-based checks. Your code is sent to Anthropic "
        "and each file uses API credits."
        if claude_ready
        else "Set the ANTHROPIC_API_KEY environment variable before starting the app to turn this on.",
    )



# ---------------------------------------------------------------------------
# Main page: choose the code to check
# ---------------------------------------------------------------------------

st.title("PAT Finance quality gate")
st.write(
    "Check code before it reaches production. PerenicAI's PAT agents look for money stored as "
    "`float`, card numbers and card data in logs, hard-coded passwords, and common bugs, "
    "then give a **PASS** or **FAIL** verdict."
)

github_tab, upload_tab, paste_tab = st.tabs(["🐙 GitHub repository", "📁 Upload files", "📝 Paste code"])

with github_tab:
    url = st.text_input("Public GitHub repository link", placeholder="https://github.com/owner/repo")
    st.caption(
        f"Checks up to {github.MAX_FILES} Python files. "
        "Private and company repositories are coming soon with the PerenicAI GitHub App."
    )
    if st.button("Scan repository", type="primary", disabled=not url.strip()):
        try:
            with st.spinner("Downloading the Python files from GitHub…"):
                repo = github.fetch_python_files(url)
        except github.GitHubError as error:
            st.error(str(error))
        else:
            if repo.skipped:
                st.info(f"{repo.skipped} Python file(s) were not checked (file limit, very large files, or library folders).")
            run_scan(repo.files, repo.label, use_claude)

with upload_tab:
    uploads = st.file_uploader("Choose Python files", type=["py"], accept_multiple_files=True)
    if st.button("Scan files", type="primary", disabled=not uploads):
        files = {upload.name: upload.getvalue().decode("utf-8", errors="replace") for upload in uploads}
        source = uploads[0].name if len(uploads) == 1 else f"{len(uploads)} uploaded files"
        run_scan(files, source, use_claude)

with paste_tab:
    filename = st.text_input("File name", value="snippet.py")
    code = st.text_area("Python code", height=300, placeholder="def charge(card_number, amount: float): ...")
    if st.button("Scan code", type="primary", disabled=not code.strip()):
        name = filename.strip() or "snippet.py"
        run_scan({name: code}, name, use_claude)

st.divider()
if st.session_state.latest:
    show_results(st.session_state.latest["source"], st.session_state.latest["results"])
else:
    st.caption("Choose some code above to see its PASS / FAIL result here.")

# The recent-scans list is drawn last, so it already includes a scan that
# was just run on this click (Streamlit draws the page from top to bottom).
with st.sidebar:
    st.divider()
    st.subheader("Recent scans")
    if st.session_state.history:
        st.dataframe(st.session_state.history, hide_index=True)
    else:
        st.caption("Your scans will appear here.")

    st.divider()
    st.caption(
        "PAT agents help catch common PCI DSS and money-handling risks early. "
        "They do not certify that software is PCI DSS compliant. Python code only, for now."
    )
