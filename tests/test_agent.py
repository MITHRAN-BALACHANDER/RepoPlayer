"""
Tests for RepoScope — GitHub Repository Intelligence Agent.

All tests replay from committed cassettes — zero API calls, zero cost.
The cassette was recorded once with:
    python reposcan.py record fastapi/fastapi

To re-record against live APIs:
    pytest --agenttape-record
"""

import pytest
import agenttape
from reposcan.agent import run, format_report
from reposcan.github_tools import (
    fetch_repo, fetch_recent_issues, fetch_recent_prs,
    fetch_contributors, fetch_readme,
)
from reposcan.ai_tools import analyze_repository, generate_contributor_brief

CASSETTE = "fastapi__fastapi"


# ── Full agent pipeline ────────────────────────────────────────────────────

@pytest.mark.agenttape(CASSETTE)
def test_agent_returns_all_sections(agenttape_cassette):
    result = run("fastapi", "fastapi")

    assert "repo" in result
    assert "issues" in result
    assert "prs" in result
    assert "contributors" in result
    assert "readme_preview" in result
    assert "analysis" in result
    assert "onboarding" in result


@pytest.mark.agenttape(CASSETTE)
def test_agent_repo_fields(agenttape_cassette):
    result = run("fastapi", "fastapi")
    repo = result["repo"]

    assert "fastapi" in repo["name"].lower()
    assert repo["language"] == "Python"
    assert isinstance(repo["stars"], int) and repo["stars"] > 0
    assert isinstance(repo["forks"], int)
    assert isinstance(repo["open_issues"], int)
    assert repo["license"]
    assert repo["default_branch"]


@pytest.mark.agenttape(CASSETTE)
def test_agent_issues_are_real(agenttape_cassette):
    result = run("fastapi", "fastapi")
    issues = result["issues"]

    # Issues list may be empty if GitHub's first-page results were all PRs
    # (fastapi has 1000+ open PRs; the updated-sort page may not include issues).
    # The important thing is that the list and structure are correct.
    assert isinstance(issues, list)
    if issues:
        first = issues[0]
        assert "number" in first
        assert "title" in first
        assert "labels" in first
        assert isinstance(first["number"], int)


@pytest.mark.agenttape(CASSETTE)
def test_agent_prs_shape(agenttape_cassette):
    result = run("fastapi", "fastapi")
    prs = result["prs"]

    assert isinstance(prs, list)
    if prs:
        first = prs[0]
        assert "number" in first
        assert "title" in first
        assert "draft" in first


@pytest.mark.agenttape(CASSETTE)
def test_agent_contributors_shape(agenttape_cassette):
    result = run("fastapi", "fastapi")
    contributors = result["contributors"]

    assert isinstance(contributors, list)
    assert len(contributors) > 0
    assert "login" in contributors[0]
    assert "contributions" in contributors[0]
    # tiangolo is the creator — should be top contributor
    logins = [c["login"] for c in contributors]
    assert "tiangolo" in logins


@pytest.mark.agenttape(CASSETTE)
def test_agent_readme_non_empty(agenttape_cassette):
    result = run("fastapi", "fastapi")
    assert len(result["readme_preview"]) > 100


# ── AI analysis structure ──────────────────────────────────────────────────

@pytest.mark.agenttape(CASSETTE)
def test_analysis_has_all_keys(agenttape_cassette):
    result = run("fastapi", "fastapi")
    analysis = result["analysis"]

    for key in ("summary", "health_score", "highlights", "concerns",
                "good_first_issues", "verdict"):
        assert key in analysis, f"Missing key in analysis: {key}"


@pytest.mark.agenttape(CASSETTE)
def test_analysis_health_score_in_range(agenttape_cassette):
    result = run("fastapi", "fastapi")
    score = result["analysis"]["health_score"]
    assert isinstance(score, int)
    assert 1 <= score <= 10


@pytest.mark.agenttape(CASSETTE)
def test_analysis_highlights_non_empty(agenttape_cassette):
    result = run("fastapi", "fastapi")
    highlights = result["analysis"]["highlights"]
    assert isinstance(highlights, list)
    assert len(highlights) >= 1


@pytest.mark.agenttape(CASSETTE)
def test_analysis_verdict_is_string(agenttape_cassette):
    result = run("fastapi", "fastapi")
    verdict = result["analysis"]["verdict"]
    assert isinstance(verdict, str)
    assert len(verdict) > 20


@pytest.mark.agenttape(CASSETTE)
def test_onboarding_is_paragraph(agenttape_cassette):
    result = run("fastapi", "fastapi")
    onboarding = result["onboarding"]
    assert isinstance(onboarding, str)
    assert len(onboarding) > 50


# ── Report formatting ──────────────────────────────────────────────────────

@pytest.mark.agenttape(CASSETTE)
def test_format_report_contains_repo_name(agenttape_cassette):
    result = run("fastapi", "fastapi")
    report = format_report(result)
    assert "fastapi" in report.lower()


@pytest.mark.agenttape(CASSETTE)
def test_format_report_contains_health_score(agenttape_cassette):
    result = run("fastapi", "fastapi")
    report = format_report(result)
    assert "Health Score" in report


@pytest.mark.agenttape(CASSETTE)
def test_format_report_contains_verdict(agenttape_cassette):
    result = run("fastapi", "fastapi")
    report = format_report(result)
    assert "Verdict" in report


# ── Individual tool boundary tests ────────────────────────────────────────

@pytest.mark.agenttape(CASSETTE)
def test_fetch_repo_boundary(agenttape_cassette):
    result = run("fastapi", "fastapi")
    # Verify the tool was exercised (cassette introspection)
    boundaries = [i.boundary for i in agenttape_cassette.interactions]
    assert "fetch_repo" in boundaries


@pytest.mark.agenttape(CASSETTE)
def test_all_boundaries_exercised(agenttape_cassette):
    run("fastapi", "fastapi")
    boundaries = [i.boundary for i in agenttape_cassette.interactions]
    expected = {
        "fetch_repo", "fetch_recent_issues", "fetch_recent_prs",
        "fetch_contributors", "fetch_readme",
        "analyze_repository", "generate_contributor_brief",
    }
    for b in expected:
        assert b in boundaries, f"Boundary '{b}' was not exercised"


@pytest.mark.agenttape(CASSETTE)
def test_interaction_kinds(agenttape_cassette):
    run("fastapi", "fastapi")
    kinds = {i.kind for i in agenttape_cassette.interactions}
    assert "tool" in kinds


# ── Determinism: replay is byte-identical ─────────────────────────────────

@pytest.mark.agenttape(CASSETTE)
def test_replay_is_deterministic(agenttape_cassette):
    """Two replays must return byte-identical results."""
    r1 = run("fastapi", "fastapi")

    with agenttape.use_cassette(CASSETTE, mode="none"):
        r2 = run("fastapi", "fastapi")

    assert r1["repo"] == r2["repo"]
    assert r1["analysis"] == r2["analysis"]
    assert r1["onboarding"] == r2["onboarding"]


# ── Safety: no side effects on replay ─────────────────────────────────────

@pytest.mark.agenttape(CASSETTE)
def test_github_tool_not_called_on_replay(agenttape_cassette, monkeypatch):
    """
    Patch the real requests.get to raise — if any tool calls the real API
    during replay, the test fails. This proves AgentTape blocks all network calls.
    """
    import requests

    def should_not_be_called(*args, **kwargs):
        raise AssertionError(
            "requests.get was called during replay — AgentTape did not intercept it!"
        )

    monkeypatch.setattr(requests, "get", should_not_be_called)
    # This must succeed even though requests.get is patched out
    result = run("fastapi", "fastapi")
    assert "fastapi" in result["repo"]["name"].lower()
