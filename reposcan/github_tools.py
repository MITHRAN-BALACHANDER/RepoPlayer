"""
GitHub API boundary functions — all wrapped with @agenttape.tool.

During recording   : calls the real GitHub REST API.
During replay      : returns the saved response, never touches the network.
Outside a session  : behaves like a plain function (passthrough).

Rate limits:
    No GITHUB_TOKEN  : 60 requests / hour
    GITHUB_TOKEN set : 5,000 requests / hour
"""

import os
import requests
import agenttape

BASE = "https://api.github.com"


def _headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


@agenttape.tool
def fetch_repo(owner: str, repo: str) -> dict:
    """Fetch core repository metadata."""
    r = requests.get(f"{BASE}/repos/{owner}/{repo}", headers=_headers(), timeout=10)
    r.raise_for_status()
    data = r.json()
    return {
        "name": data["full_name"],
        "description": data.get("description") or "",
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
        "language": data.get("language") or "unknown",
        "topics": data.get("topics", []),
        "license": (data.get("license") or {}).get("spdx_id", "none"),
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
        "default_branch": data["default_branch"],
        "homepage": data.get("homepage") or "",
    }


@agenttape.tool
def fetch_recent_issues(owner: str, repo: str, n: int = 10) -> list:
    """Fetch the N most recently updated open issues (excluding PRs).

    Requests 3× the desired count to account for PRs mixed into the
    /issues endpoint response (GitHub's issues API returns both issues
    and PRs; we filter out PRs after fetching).
    """
    r = requests.get(
        f"{BASE}/repos/{owner}/{repo}/issues",
        headers=_headers(),
        params={"state": "open", "per_page": min(n * 3, 100), "sort": "updated"},
        timeout=10,
    )
    r.raise_for_status()
    return [
        {
            "number": i["number"],
            "title": i["title"],
            "labels": [lb["name"] for lb in i.get("labels", [])],
            "comments": i["comments"],
            "created_at": i["created_at"],
        }
        for i in r.json()
        if "pull_request" not in i
    ][:n]


@agenttape.tool
def fetch_recent_prs(owner: str, repo: str, n: int = 10) -> list:
    """Fetch the N most recently updated open pull requests."""
    r = requests.get(
        f"{BASE}/repos/{owner}/{repo}/pulls",
        headers=_headers(),
        params={"state": "open", "per_page": n, "sort": "updated"},
        timeout=10,
    )
    r.raise_for_status()
    return [
        {
            "number": p["number"],
            "title": p["title"],
            "draft": p.get("draft", False),
            "created_at": p["created_at"],
            "updated_at": p["updated_at"],
        }
        for p in r.json()
    ][:n]


@agenttape.tool
def fetch_contributors(owner: str, repo: str, n: int = 10) -> list:
    """Fetch the top N contributors by commit count."""
    r = requests.get(
        f"{BASE}/repos/{owner}/{repo}/contributors",
        headers=_headers(),
        params={"per_page": n},
        timeout=10,
    )
    r.raise_for_status()
    return [
        {"login": c["login"], "contributions": c["contributions"]}
        for c in r.json()
    ][:n]


@agenttape.tool
def fetch_readme(owner: str, repo: str) -> str:
    """Fetch the repository README as plain text (first 3000 characters)."""
    h = {**_headers(), "Accept": "application/vnd.github.raw"}
    r = requests.get(f"{BASE}/repos/{owner}/{repo}/readme", headers=h, timeout=10)
    if r.status_code == 404:
        return "(no README found)"
    r.raise_for_status()
    return r.text[:3000]
