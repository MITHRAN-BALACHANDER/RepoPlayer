# RepoScope

**Understand any GitHub repository in seconds -- AI-powered, fully testable.**

RepoScope fetches live data from the GitHub API, runs it through an LLM, and produces a structured intelligence report: summary, health score, highlights, concerns, good-first-issues, a verdict, and a contributor onboarding guide.

Built on [AgentTape](https://pypi.org/project/agenttape/) -- every external call is recorded once and replayed forever, so tests run offline in under a second with zero API cost.

---

## The problem it solves

Evaluating an unfamiliar GitHub repository before adopting it or contributing takes 20-30 minutes of manual reading: README, recent issues, open PRs, contributor activity, license, health signals. Do this 10 times a week and it consumes hours.

RepoScope does it in one command.

```bash
python cli.py record fastapi/fastapi
```

The report below is the exact output replayed from the committed `cassettes/fastapi__fastapi.yaml` (recorded 2026-06-19 against the real GitHub API and Gemini):

```
==============================================================
  RepoScope Intelligence Report
  fastapi/fastapi
==============================================================

  Language : Python
  Stars    : 99,391
  Forks    : 9,453
  Issues   : 88 open
  License  : MIT
  Topics   : api, async, asyncio, fastapi, framework, json, ...

-- Summary --------------------------------------------------
FastAPI is a highly popular and performant Python web framework
designed for building APIs quickly, leveraging modern Python
features like type hints and async/await. It boasts strong
community adoption, comprehensive documentation, and is built on
established standards like OpenAPI and JSON Schema.

-- Health Score: 10 / 10 ---------------------------------

-- Highlights -----------------------------------------------
  + Exceptional community engagement with nearly 100k stars and
    robust fork activity, indicating widespread adoption and trust.
  + Actively maintained with a steady stream of new features and
    bug fixes, as evidenced by recent pull requests.
  + Strong technical foundation built on Starlette and Pydantic,
    providing high performance and automatic API documentation.
  + Clear MIT license encourages adoption and contribution.

-- Good First Issues ----------------------------------------
  * Update documentation for a specific feature or use case
  * Add more type hints to existing internal utility functions
  * Refine error messages for common validation failures

-- Verdict --------------------------------------------------
  Developers should absolutely adopt and contribute to FastAPI,
  as it is a well-established, actively maintained, and
  high-quality framework with a thriving community.

-- Onboarding -----------------------------------------------
Welcome to FastAPI! To get started, familiarize yourself with our
comprehensive documentation at fastapi.tiangolo.com and then
explore existing issues for potential fixes or new features...
==============================================================
```

---

## Why AgentTape matters here

Without AgentTape, every test run would consume GitHub API rate quota, spend real LLM tokens, and require API keys in CI.

| | Without AgentTape | With AgentTape |
|---|---|---|
| CI cost | LLM tokens per run x N runs | **$0** after first record |
| Speed | ~15 s (sum of real API latencies) | **< 1 s** replay |
| Flakiness | GitHub API or LLM varies | **byte-identical** every run |
| API keys in CI | Required | **Not needed** |
| Offline dev | Impossible | **Works anywhere** |

The numbers are measured from this repo: the recorded latencies in `cassettes/fastapi__fastapi.yaml` total ~15.4 s of real API time (two LLM calls alone are ~6.6 s each), while the full 19-test suite replays in ~0.9 s.

The key insight: **record once against real services, replay forever for free.**

---

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
pip install google-genai          # for Gemini (default, free)
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
# Get a free key at https://aistudio.google.com/apikey
```

### 3. Record a cassette (once -- calls real APIs)

```bash
python cli.py record fastapi/fastapi
```

This calls GitHub + your LLM once and saves everything to `cassettes/fastapi__fastapi.yaml`. Commit that file to Git.

### 4. Replay offline (no key, no network, no cost)

```bash
python cli.py show fastapi/fastapi
```

### 5. Run tests (pure offline replay)

```bash
pytest                        # no API keys needed
pytest --agenttape-record     # re-record against live APIs
```

---

## CLI reference

`cli.py` is the canonical entry point. `reposcan.py` is a thin compatibility shim that runs `cli.py`, so the older `python reposcan.py ...` invocation still works.

```
python cli.py record <owner/repo>   Record cassette from real APIs
python cli.py show   <owner/repo>   Display saved report (offline)
```

Examples:

```bash
python cli.py record fastapi/fastapi
python cli.py record pallets/flask
python cli.py show   fastapi/fastapi
```

---

## LLM providers

Switch provider by setting `LLM_PROVIDER` in your `.env` file.

| Provider | `LLM_PROVIDER` value | Free? | Key env var |
|---|---|---|---|
| **Gemini** (default) | `gemini` | Yes | `GEMINI_API_KEY` |
| **Ollama** | `ollama` | Yes (local) | none |
| **Anthropic** | `anthropic` | No | `ANTHROPIC_API_KEY` |
| **OpenAI** | `openai` | No | `OPENAI_API_KEY` |

Get a free Gemini key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

For Ollama (fully local, no key needed):

```bash
# Install Ollama: https://ollama.com
ollama pull llama3.2
```

Set in `.env`:

```
LLM_PROVIDER=ollama
```

Optional model overrides (set in `.env`, with the defaults shown):

```
GEMINI_MODEL=gemini-2.5-flash
OLLAMA_MODEL=llama3.2
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
OPENAI_MODEL=gpt-4o-mini
```

---

## GitHub rate limits

By default, GitHub allows 60 unauthenticated requests per hour -- enough for occasional use. To raise this to 5,000/hour, add a GitHub token to `.env`:

```
GITHUB_TOKEN=ghp_...
```

Generate one at [github.com/settings/tokens](https://github.com/settings/tokens) -- no scopes needed for public repos. The token is redacted out of cassettes automatically (see `agenttape.toml`).

---

## Project structure

```
cli.py                  canonical CLI entry point (record / show)
reposcan.py             compatibility shim -- runs cli.py

reposcan/
    __init__.py         package marker (empty; .env is loaded by cli.py)
    agent.py            orchestration -- run() and format_report()
    github_tools.py     @agenttape.tool GitHub API functions (5)
    ai_tools.py         @agenttape.tool LLM analysis functions (2)
    llm.py              multi-provider LLM dispatcher

tests/
    conftest.py         session-scoped replay fixture (fastapi_result)
    test_agent.py       19 tests -- all offline replay

cassettes/              committed recordings (real GitHub + LLM data)
    fastapi__fastapi.yaml
    pallets__flask.yaml ... (one .yaml per analysed repo)

.env.example            environment variable template
agenttape.toml          cassette config + secret redaction
pytest.ini              pytest config + agenttape marker
requirements.txt
```

---

## How AgentTape works in this project

Every external boundary is a `@agenttape.tool`:

```python
@agenttape.tool
def fetch_repo(owner, repo):          # GitHub API call
    ...

@agenttape.tool
def analyze_repository(context):      # LLM call
    ...
```

On first run (`mode="record"`): the function executes for real and the response is saved to a YAML cassette.

On every subsequent run (`mode="none"`, the default in `agenttape.toml`): AgentTape intercepts the call before it runs and returns the saved response. Zero network. Zero tokens.

```python
with agenttape.use_cassette("fastapi__fastapi", mode="record"):
    result = run("fastapi", "fastapi")   # calls real GitHub + LLM

with agenttape.use_cassette("fastapi__fastapi", mode="none"):
    result = run("fastapi", "fastapi")   # reads from cassette, offline
```

7 boundaries are recorded per repo: 5 GitHub API calls (`fetch_repo`, `fetch_recent_issues`, `fetch_recent_prs`, `fetch_contributors`, `fetch_readme`) and 2 LLM calls (`analyze_repository`, `generate_contributor_brief`).

---

## AgentTape features demonstrated

| Feature | Where |
|---|---|
| `@agenttape.tool` | All 7 external boundary functions |
| `mode="record"` | `cli.py record` -- writes cassette from real APIs |
| `mode="none"` | `cli.py show` and all pytest tests |
| `@pytest.mark.agenttape` | Boundary-introspection tests in `tests/test_agent.py` |
| `agenttape_cassette` fixture | Inspecting `interactions` (boundary, kind) in tests |
| Frozen clock / random / uuid | `freeze = ["clock", "uuid", "random"]` in `agenttape.toml` |
| Secret redaction | API keys + tokens stripped from cassettes automatically |
| Git-friendly YAML cassettes | `cassettes/` committed to version control |

---

## Analysing a different repository

```bash
python cli.py record pallets/flask
python cli.py show   pallets/flask
```

Each repository gets its own cassette (`cassettes/owner__repo.yaml`). Record once, replay forever.

---

## Re-recording after the project changes

If you want a fresh snapshot of a repository's current state:

```bash
python cli.py record fastapi/fastapi
# or from pytest:
pytest --agenttape-record
```

---

## License

MIT -- see the `Licence` file.
