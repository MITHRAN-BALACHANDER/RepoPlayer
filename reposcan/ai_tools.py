"""
AI analysis boundary functions — all wrapped with @agenttape.tool.

Provider is selected via LLM_PROVIDER env var (default: gemini).
See reposcan/llm.py for all provider options and configuration.

During recording   : calls the real LLM API.
During replay      : returns the saved response, zero API calls.
Outside a session  : behaves like a plain function (passthrough).
"""

import json
import agenttape
from .llm import chat

_ANALYSIS_SYSTEM = (
    "You are an expert open-source engineer. Given a repository context, "
    "produce a structured JSON analysis with exactly these keys:\n"
    "  summary           - 2-3 sentence plain-English description\n"
    "  health_score      - integer 1-10 (10 = excellent)\n"
    "  highlights        - list of 3 positive signals\n"
    "  concerns          - list of up to 3 potential concerns (empty list if none)\n"
    "  good_first_issues - list of issue titles suitable for new contributors (up to 3)\n"
    "  verdict           - one sentence: should a developer adopt/contribute to this project?\n"
    "Respond with ONLY valid JSON, no markdown fences."
)

_ONBOARDING_SYSTEM = (
    "You are an expert open-source engineer. Write a concise 3-4 sentence "
    "onboarding paragraph for a developer who wants to contribute to this project. "
    "Focus on: how to get started, what kind of contributions are most needed, "
    "and any key things to know about the community. "
    "Be specific to the project, not generic. Plain text, no markdown."
)


@agenttape.tool
def analyze_repository(context: str) -> dict:
    """
    Ask the configured LLM to analyze a GitHub repository context.
    Returns a structured dict: summary, health_score, highlights,
    concerns, good_first_issues, verdict.
    """
    raw = chat(_ANALYSIS_SYSTEM, context).strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) >= 2 else parts[-1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


@agenttape.tool
def generate_contributor_brief(context: str) -> str:
    """Ask the configured LLM to write a contributor onboarding paragraph."""
    return chat(_ONBOARDING_SYSTEM, context).strip()
