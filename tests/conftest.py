"""
Pytest configuration for RepoScope.

All tests replay from committed cassettes — no API calls, no API keys needed.
To re-record: pytest --agenttape-record  (requires the LLM provider API key)
"""
import pytest
import agenttape
from reposcan.agent import run

CASSETTE = "fastapi__fastapi"


@pytest.fixture(scope="session")
def fastapi_result():
    """Run the full agent pipeline once per session and cache the result.

    Tests that only inspect output data use this fixture instead of
    calling run() individually, avoiding redundant cassette replays.
    """
    with agenttape.use_cassette(CASSETTE, mode="none"):
        return run("fastapi", "fastapi")
