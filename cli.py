"""
RepoScope CLI — Understand any GitHub repository in seconds.

Usage:
    python cli.py record <owner/repo>   Record a cassette from real APIs
    python cli.py show   <owner/repo>   Display a saved report (offline)

Examples:
    python cli.py record fastapi/fastapi
    python cli.py show   fastapi/fastapi
    python cli.py record pallets/flask

Environment:
    Copy .env.example to .env and fill in your API keys.
    LLM_PROVIDER controls which LLM is used (default: gemini).
"""

from dotenv import load_dotenv

load_dotenv()

import os
import sys
import agenttape
from reposcan.agent import run, format_report


def _parse_target(raw: str) -> tuple[str, str]:
    if "/" not in raw:
        print(f"ERROR: Expected owner/repo, got: {raw!r}")
        print("Example: python cli.py record fastapi/fastapi")
        sys.exit(1)
    return raw.split("/", 1)


def cmd_record(target: str) -> None:
    """Call real GitHub API + LLM, save cassette, print report."""
    owner, repo = _parse_target(target)
    cassette    = f"{owner}__{repo}"
    provider    = os.environ.get("LLM_PROVIDER", "gemini")

    required_keys = {
        "gemini":    "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai":    "OPENAI_API_KEY",
    }
    if provider in required_keys:
        key = required_keys[provider]
        if not os.environ.get(key):
            print(f"ERROR: {key} is not set.")
            print(f"Add it to your .env file:  {key}=your-key-here")
            print(f"Or switch to local Ollama: LLM_PROVIDER=ollama")
            sys.exit(1)

    print(f"RepoScope")
    print(f"  Provider : {provider}")
    print(f"  Target   : {owner}/{repo}")
    print(f"  Cassette : cassettes/{cassette}.yaml")
    print()
    print("Calling real APIs (runs once — replay is free forever after)...")
    print()

    with agenttape.use_cassette(cassette, mode="record"):
        result = run(owner, repo)

    print(format_report(result))
    print()
    print(f"[OK] Cassette saved to cassettes/{cassette}.yaml")
    print("     Commit it to Git. Tests and show command now work offline.")


def cmd_show(target: str) -> None:
    """Replay a saved cassette and print the report (no network, no API key)."""
    owner, repo  = _parse_target(target)
    cassette     = f"{owner}__{repo}"

    print(f"Replaying cassettes/{cassette}.yaml")
    print("No network. No API key. No cost.\n")

    try:
        with agenttape.use_cassette(cassette, mode="none"):
            result = run(owner, repo)
        print(format_report(result))
    except agenttape.UnmatchedInteractionError:
        print(f"[!!] No cassette found for {owner}/{repo}.")
        print(f"     Record it first:  python cli.py record {owner}/{repo}")
        sys.exit(1)


COMMANDS = {"record": cmd_record, "show": cmd_show}

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in COMMANDS:
        print("RepoScope — GitHub Repository Intelligence Agent")
        print()
        print("Usage:")
        print("  python cli.py record <owner/repo>   # record from real APIs")
        print("  python cli.py show   <owner/repo>   # display saved report")
        print()
        print("Examples:")
        print("  python cli.py record fastapi/fastapi")
        print("  python cli.py show   fastapi/fastapi")
        sys.exit(0 if len(sys.argv) == 1 else 1)

    COMMANDS[sys.argv[1]](sys.argv[2])
