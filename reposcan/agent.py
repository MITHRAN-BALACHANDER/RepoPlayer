"""
RepoScope — GitHub Repository Intelligence Agent.

Orchestrates GitHub API calls and LLM analysis to produce a full
intelligence report about any public GitHub repository.
"""

from __future__ import annotations

from .github_tools import (
    fetch_repo,
    fetch_recent_issues,
    fetch_recent_prs,
    fetch_contributors,
    fetch_readme,
)
from .ai_tools import analyze_repository, generate_contributor_brief


def run(owner: str, repo: str) -> dict:
    """
    Analyse a GitHub repository and return a structured intelligence report.

    All external calls (GitHub API + LLM) are @agenttape.tool boundaries:
    recorded on first run, replayed for free on every subsequent run.

    Returns a dict with keys:
        repo             - raw GitHub metadata
        issues           - list of recent open issues
        prs              - list of recent open pull requests
        contributors     - top contributors by commit count
        readme_preview   - first 500 chars of README
        analysis         - LLM structured analysis (summary, health_score, ...)
        onboarding       - LLM contributor onboarding paragraph
    """
    repo_meta    = fetch_repo(owner, repo)
    issues       = fetch_recent_issues(owner, repo, n=10)
    prs          = fetch_recent_prs(owner, repo, n=10)
    contributors = fetch_contributors(owner, repo, n=10)
    readme       = fetch_readme(owner, repo)

    issue_titles  = "\n".join(f"  - #{i['number']}: {i['title']}" for i in issues[:5])
    pr_titles     = "\n".join(f"  - #{p['number']}: {p['title']}" for p in prs[:5])
    contrib_names = ", ".join(c["login"] for c in contributors[:5])

    context = f"""Repository: {repo_meta['name']}
Description: {repo_meta['description']}
Language: {repo_meta['language']}
Stars: {repo_meta['stars']:,}   Forks: {repo_meta['forks']:,}   Open issues: {repo_meta['open_issues']:,}
Topics: {', '.join(repo_meta['topics']) or 'none'}
License: {repo_meta['license']}
Top contributors: {contrib_names}

Recent open issues (sample):
{issue_titles or '  (none)'}

Recent open PRs (sample):
{pr_titles or '  (none)'}

README (first 800 chars):
{readme[:800]}
"""

    analysis   = analyze_repository(context)
    onboarding = generate_contributor_brief(context)

    return {
        "repo":           repo_meta,
        "issues":         issues,
        "prs":            prs,
        "contributors":   contributors,
        "readme_preview": readme[:500],
        "analysis":       analysis,
        "onboarding":     onboarding,
    }


def format_report(result: dict) -> str:
    """Render an intelligence report dict as a human-readable string."""
    r   = result["repo"]
    a   = result["analysis"]
    sep = "=" * 62

    lines = [
        sep,
        "  RepoScope Intelligence Report",
        f"  {r['name']}",
        sep,
        "",
        f"  Language : {r['language']}",
        f"  Stars    : {r['stars']:,}",
        f"  Forks    : {r['forks']:,}",
        f"  Issues   : {r['open_issues']:,} open",
        f"  License  : {r['license']}",
        f"  Topics   : {', '.join(r['topics']) or 'none'}",
        "",
        "-- Summary " + "-" * 50,
        a.get("summary", ""),
        "",
        f"-- Health Score: {a.get('health_score', '?')} / 10 " + "-" * 33,
        "",
        "-- Highlights " + "-" * 47,
    ]
    for h in a.get("highlights", []):
        lines.append(f"  + {h}")

    concerns = a.get("concerns", [])
    if concerns:
        lines += ["", "-- Concerns " + "-" * 49]
        for c in concerns:
            lines.append(f"  ! {c}")

    gfi = a.get("good_first_issues", [])
    if gfi:
        lines += ["", "-- Good First Issues " + "-" * 40]
        for issue in gfi:
            lines.append(f"  * {issue}")

    lines += [
        "",
        "-- Verdict " + "-" * 50,
        f"  {a.get('verdict', '')}",
        "",
        "-- Onboarding " + "-" * 47,
        result.get("onboarding", ""),
        "",
        sep,
    ]
    return "\n".join(lines)
