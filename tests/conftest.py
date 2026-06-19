"""
Pytest configuration for RepoScope.

All tests replay from committed cassettes — no API calls, no API keys needed.
To re-record: pytest --agenttape-record  (requires the LLM provider API key)
"""
import pathlib
import pytest

CASSETTE_DIR = pathlib.Path(__file__).parent.parent / "cassettes"
