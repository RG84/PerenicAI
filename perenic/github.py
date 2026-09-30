"""Fetch the Python files from a public GitHub repository.

The website uses this for "Scan a GitHub repository". It only needs
Python's standard library (urllib), so there is nothing extra to install.

Public repositories work without logging in. GitHub allows about 60
anonymous requests an hour, and each scan uses one or two. To raise that
limit, set a GITHUB_TOKEN environment variable (a GitHub personal access
token). Private and company repositories will need the PerenicAI GitHub
App, which is the next step on the roadmap.
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

MAX_FILES = 50  # keeps scans quick (and Claude costs predictable)
MAX_FILE_BYTES = 200_000  # skip very large files, which are usually generated
# Folders that hold other people's code or generated code, not the customer's.
SKIP_FOLDERS = {".venv", "venv", "env", "site-packages", "node_modules", "__pycache__", ".git", "build", "dist"}

REPO_URL = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/"
    r"(?P<owner>[A-Za-z0-9-]+)/(?P<repo>[A-Za-z0-9._-]+?)(?:\.git)?"
    r"(?:/tree/(?P<branch>[^?#]+?))?/?(?:[?#].*)?$"
)


class GitHubError(Exception):
    """A problem worth showing to the user, e.g. 'Repository not found'."""


@dataclass
class RepoFiles:
    owner: str
    repo: str
    branch: str
    files: dict[str, str] = field(default_factory=dict)  # path -> code
    skipped: int = 0  # Python files left out because of MAX_FILES or size

    @property
    def label(self) -> str:
        return f"{self.owner}/{self.repo} ({self.branch})"


def parse_repo_url(url: str) -> tuple[str, str, str | None]:
    """Split a GitHub link into (owner, repo, branch).

    "https://github.com/RG84/PerenicAI" -> ("RG84", "PerenicAI", None)
    "github.com/RG84/PerenicAI/tree/dev" -> ("RG84", "PerenicAI", "dev")
    """
    match = REPO_URL.match(url.strip())
    if not match:
        raise GitHubError("That doesn't look like a GitHub repository link. Example: https://github.com/owner/repo")
    return match["owner"], match["repo"], match["branch"]


def is_wanted(path: str, size: int) -> bool:
    """True for Python files that are the customer's own code."""
    if not path.endswith(".py") or size > MAX_FILE_BYTES:
        return False
    folders = path.split("/")[:-1]
    return not any(folder in SKIP_FOLDERS for folder in folders)


def _download(url: str) -> bytes:
    """Download one URL. Tests replace this function with a fake one."""
    headers = {"User-Agent": "PerenicAI", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise GitHubError("Repository or branch not found. Is the link right, and is the repository public?")
        if error.code in (403, 429):
            raise GitHubError("GitHub's limit for anonymous requests was reached. Try again later, or set GITHUB_TOKEN.")
        raise GitHubError(f"GitHub returned an error ({error.code}).")
    except urllib.error.URLError as error:
        raise GitHubError(f"Could not reach GitHub: {error.reason}")


def _get_json(url: str) -> dict:
    return json.loads(_download(url))


def fetch_python_files(url: str) -> RepoFiles:
    """Download the Python files from a public GitHub repository link."""
    owner, repo, branch = parse_repo_url(url)
    api = f"https://api.github.com/repos/{owner}/{repo}"

    if branch is None:
        branch = _get_json(api)["default_branch"]

    tree = _get_json(f"{api}/git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1")
    paths = sorted(
        item["path"]
        for item in tree.get("tree", [])
        if item.get("type") == "blob" and is_wanted(item["path"], item.get("size", 0))
    )
    all_python = [item for item in tree.get("tree", []) if item.get("path", "").endswith(".py")]

    result = RepoFiles(owner, repo, branch)
    for path in paths[:MAX_FILES]:
        raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{urllib.parse.quote(branch)}/{urllib.parse.quote(path)}"
        result.files[path] = _download(raw).decode("utf-8", errors="replace")
    result.skipped = len(all_python) - len(result.files)

    if not result.files:
        raise GitHubError("No Python files were found in that repository. PerenicAI checks Python code for now.")
    return result
