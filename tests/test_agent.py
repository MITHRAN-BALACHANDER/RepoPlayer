"""
Tests for RepoScope — GitHub Repository Intelligence Agent.

All tests replay from committed cassettes — zero API calls, zero cost.
The cassette was recorded once with:
    python cli.py record fastapi/fastapi

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
# These tests only inspect result data; they share a single session-scoped
# replay via the fastapi_result fixture (defined in conftest.py).

def test_agent_returns_all_sections(fastapi_result):
    assert "repo" in fastapi_result
    assert "issues" in fastapi_result
    assert "prs" in fastapi_result
    assert "contributors" in fastapi_result
    assert "readme_preview" in fastapi_result
    assert "analysis" in fastapi_result
    assert "onboarding" in fastapi_result


def test_agent_repo_fields(fastapi_result):
    repo = fastapi_result["repo"]

    assert "fastapi" in repo["name"].lower()
    assert repo["language"] == "Python"
    assert isinstance(repo["stars"], int) and repo["stars"] > 0
    assert isinstance(repo["forks"], int)
    assert isinstance(repo["open_issues"], int)
    assert repo["license"]
    assert repo["default_branch"]


def test_agent_issues_are_real(fastapi_result):
    issues = fastapi_result["issues"]

    assert isinstance(issues, list)
    if issues:
        first = issues[0]
        assert "number" in first
        assert "title" in first
        assert "labels" in first
        assert isinstance(first["number"], int)


def test_agent_prs_shape(fastapi_result):
    prs = fastapi_result["prs"]

    assert isinstance(prs, list)
    if prs:
        first = prs[0]
        assert "number" in first
        assert "title" in first
        assert "draft" in first


def test_agent_contributors_shape(fastapi_result):
    contributors = fastapi_result["contributors"]

    assert isinstance(contributors, list)
    assert len(contributors) > 0
    assert "login" in contributors[0]
    assert "contributions" in contributors[0]
    # tiangolo is the creator — should be top contributor
    logins = [c["login"] for c in contributors]
    assert "tiangolo" in logins


def test_agent_readme_non_empty(fastapi_result):
    assert len(fastapi_result["readme_preview"]) > 100


# ── AI analysis structure ──────────────────────────────────────────────────

def test_analysis_has_all_keys(fastapi_result):
    analysis = fastapi_result["analysis"]

    for key in ("summary", "health_score", "highlights", "concerns",
                "good_first_issues", "verdict"):
        assert key in analysis, f"Missing key in analysis: {key}"


def test_analysis_health_score_in_range(fastapi_result):
    score = fastapi_result["analysis"]["health_score"]
    assert isinstance(score, int)
    assert 1 <= score <= 10


def test_analysis_highlights_non_empty(fastapi_result):
    highlights = fastapi_result["analysis"]["highlights"]
    assert isinstance(highlights, list)
    assert len(highlights) >= 1


def test_analysis_verdict_is_string(fastapi_result):
    verdict = fastapi_result["analysis"]["verdict"]
    assert isinstance(verdict, str)
    assert len(verdict) > 20


def test_onboarding_is_paragraph(fastapi_result):
    onboarding = fastapi_result["onboarding"]
    assert isinstance(onboarding, str)
    assert len(onboarding) > 50


# ── Report formatting ──────────────────────────────────────────────────────

def test_format_report_contains_repo_name(fastapi_result):
    report = format_report(fastapi_result)
    assert "fastapi" in report.lower()


def test_format_report_contains_health_score(fastapi_result):
    report = format_report(fastapi_result)
    assert "Health Score" in report


def test_format_report_contains_verdict(fastapi_result):
    report = format_report(fastapi_result)
    assert "Verdict" in report


# ── Individual tool boundary tests ────────────────────────────────────────
# These tests introspect agenttape_cassette.interactions so they must
# call run() themselves inside a cassette context.

@pytest.mark.agenttape(CASSETTE)
def test_fetch_repo_boundary(agenttape_cassette):
    run("fastapi", "fastapi")
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
    """Two replays within the same cassette context must return identical results."""
    r1 = run("fastapi", "fastapi")
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
