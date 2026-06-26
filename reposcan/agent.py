"""
RepoScope — GitHub Repository Intelligence Agent.

Orchestrates GitHub API calls and LLM analysis to produce a full
intelligence report about any public GitHub repository.
"""

from __future__ import annotations

import shutil
import textwrap

from .github_tools import (
    fetch_repo,
    fetch_recent_issues,
    fetch_recent_prs,
    fetch_contributors,
    fetch_readme,
)
from .ai_tools import analyze_repository, generate_contributor_brief

_README_PREVIEW_CHARS = 800


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
        readme_preview   - first 800 chars of README
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

README (first {_README_PREVIEW_CHARS} chars):
{readme[:_README_PREVIEW_CHARS]}
"""

    analysis   = analyze_repository(context)
    onboarding = generate_contributor_brief(context)

    return {
        "repo":           repo_meta,
        "issues":         issues,
        "prs":            prs,
        "contributors":   contributors,
        "readme_preview": readme[:_README_PREVIEW_CHARS],
        "analysis":       analysis,
        "onboarding":     onboarding,
    }


# ── Width-aware formatting helpers ─────────────────────────────────────────
# Every line in the report is produced through these helpers so the layout
# stays consistent and never relies on the terminal's own wrapping.

_DEFAULT_WIDTH = 100   # used when the terminal width cannot be determined
_WIDTH_PADDING = 4     # trailing breathing room so lines never hug the edge
_LABEL_WIDTH = 8       # widest header label ("Language"); aligns all colons


def wrap_width() -> int:
    """Current wrap width: terminal width minus padding, capped at 100.

    Falls back to 100 columns when the terminal size cannot be determined
    (e.g. output piped to a file or running under CI).
    """
    columns = shutil.get_terminal_size(fallback=(_DEFAULT_WIDTH, 24)).columns
    return min(columns - _WIDTH_PADDING, _DEFAULT_WIDTH)


def wrap_text(text: str) -> str:
    """Wrap a plain paragraph to the current width with no indentation."""
    return textwrap.fill(
        str(text).strip(),
        width=wrap_width(),
        break_long_words=False,
        break_on_hyphens=False,
    )


def wrap_bullet(text: str, marker: str = "+") -> str:
    """Wrap one bullet point, aligning continuation lines under the text."""
    prefix = f"{marker} "
    return textwrap.fill(
        str(text).strip(),
        width=wrap_width(),
        initial_indent=prefix,
        subsequent_indent=" " * len(prefix),
        break_long_words=False,
        break_on_hyphens=False,
    )


def print_key_value(label: str, value: object) -> str:
    """Render an aligned ``Label : value`` line, wrapping long values.

    Continuation lines (e.g. a long Topics list) indent to line up under the
    value rather than the label.
    """
    prefix = f"{label.ljust(_LABEL_WIDTH)} : "
    return textwrap.fill(
        str(value),
        width=wrap_width(),
        initial_indent=prefix,
        subsequent_indent=" " * len(prefix),
        break_long_words=False,
        break_on_hyphens=False,
    )


def _section_title(title: str) -> str:
    """A ``-- Title ----...`` separator that fills the current width."""
    head = f"-- {title} "
    return head + "-" * max(0, wrap_width() - len(head))


def _section(
    lines: list[str],
    title: str,
    *,
    paragraph: str | None = None,
    bullets: list | None = None,
    marker: str = "+",
) -> None:
    """Append a titled section: separator, blank line, then a wrapped body.

    Paragraphs are wrapped with :func:`wrap_text`; bullets with
    :func:`wrap_bullet`, separated by blank lines for readability.
    """
    lines += ["", _section_title(title), ""]
    if paragraph:
        lines.append(wrap_text(paragraph))
    for bullet in bullets or []:
        lines.append(wrap_bullet(bullet, marker))
        lines.append("")          # blank line between bullets
    if bullets and lines[-1] == "":
        lines.pop()               # drop the trailing blank the loop left


def format_report(result: dict) -> str:
    """Render an intelligence report dict as a width-aware, readable string.

    Paragraphs, bullets and the header fields are all wrapped to the current
    terminal width (capped at 100 columns, defaulting to 100 when unknown) via
    the shared wrap_text / wrap_bullet / print_key_value helpers, so the report
    renders cleanly from 80 to 160 columns and copies into Markdown without
    overflowing.
    """
    r = result["repo"]
    a = result["analysis"]
    rule = "=" * wrap_width()

    lines: list[str] = [
        rule,
        "  RepoScope Intelligence Report",
        f"  {r['name']}",
        rule,
        "",
        print_key_value("Language", r["language"]),
        print_key_value("Stars", f"{r['stars']:,}"),
        print_key_value("Forks", f"{r['forks']:,}"),
        print_key_value("Issues", f"{r['open_issues']:,} open"),
        print_key_value("License", r["license"]),
        print_key_value("Topics", ", ".join(r["topics"]) or "none"),
    ]

    _section(lines, "Summary", paragraph=a.get("summary", ""))

    lines += ["", _section_title(f"Health Score: {a.get('health_score', '?')} / 10")]

    _section(lines, "Highlights", bullets=a.get("highlights", []), marker="+")

    concerns = a.get("concerns", [])
    if concerns:
        _section(lines, "Concerns", bullets=concerns, marker="!")

    gfi = a.get("good_first_issues", [])
    if gfi:
        _section(lines, "Good First Issues", bullets=gfi, marker="*")

    _section(lines, "Verdict", paragraph=a.get("verdict", ""))
    _section(lines, "Onboarding", paragraph=result.get("onboarding", ""))

    lines += ["", rule]
    return "\n".join(lines)
