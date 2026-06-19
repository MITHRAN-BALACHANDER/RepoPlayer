# RepoScope

**Understand any GitHub repository in seconds — AI-powered, fully testable.**

RepoScope fetches live data from the GitHub API, runs it through an LLM, and produces a structured intelligence report: health score, highlights, concerns, good-first-issues, and a contributor onboarding guide.

Built on [AgentTape](https://pypi.org/project/agenttape/) — every external call is recorded once and replayed forever, so tests run offline in under a second with zero API cost.

---

## The problem it solves

Evaluating an unfamiliar GitHub repository before adopting it or contributing takes 20-30 minutes of manual reading: README, recent issues, open PRs, contributor activity, license, health signals. Do this 10 times a week and it consumes hours.

RepoScope does it in one command.

```
python reposcan.py record fastapi/fastapi
```

Output:

```
==============================================================
  RepoScope Intelligence Report
  fastapi/fastapi
==============================================================

  Language : Python
  Stars    : 99,391
  License  : MIT

-- Health Score: 10 / 10 ------------------------------------

-- Highlights -----------------------------------------------
  + Exceptional community engagement (~100k stars)
  + Actively maintained with steady stream of bug fixes
  + Strong technical foundation built on Starlette and Pydantic

-- Verdict --------------------------------------------------
  Developers should absolutely adopt FastAPI.

-- Onboarding -----------------------------------------------
  Welcome to FastAPI! Start with the docs at fastapi.tiangolo.com...
==============================================================
```

---

## Why AgentTape matters here

Without AgentTape, every test run would consume GitHub API rate quota, spend real LLM tokens, and require API keys in CI.

| | Without AgentTape | With AgentTape |
|---|---|---|
| CI cost | ~$0.01 per run x N runs | **$0** after first record |
| Speed | 5-10 seconds | **< 1 second** |
| Flakiness | GitHub API or LLM varies | **byte-identical** every run |
| API keys in CI | Required | **Not needed** |
| Offline dev | Impossible | **Works anywhere** |

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
python reposcan.py record fastapi/fastapi
```

This calls GitHub + your LLM once and saves everything to `cassettes/fastapi__fastapi.yaml`. Commit that file to Git.

### 4. Replay offline (no key, no network, no cost)

```bash
python reposcan.py show fastapi/fastapi
```

### 5. Run tests (pure offline replay)

```bash
pytest                        # no API keys needed
pytest --agenttape-record     # re-record against live APIs
```

---

## CLI reference

```
python reposcan.py record <owner/repo>   Record cassette from real APIs
python reposcan.py show   <owner/repo>   Display saved report (offline)
```

Examples:

```bash
python reposcan.py record fastapi/fastapi
python reposcan.py record pallets/flask
python reposcan.py show   fastapi/fastapi
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

Optional model overrides (set in `.env`):

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

Generate one at [github.com/settings/tokens](https://github.com/settings/tokens) -- no scopes needed for public repos.

---

## Project structure

```
reposcan/
    __init__.py         auto-loads .env
    agent.py            main orchestration -- run() and format_report()
    github_tools.py     @agenttape.tool GitHub API functions
    ai_tools.py         @agenttape.tool LLM analysis functions
    llm.py              multi-provider LLM dispatcher

tests/
    test_agent.py       19 tests -- all offline replay

cassettes/
    fastapi__fastapi.yaml   committed recording (real GitHub + LLM data)

reposcan.py             CLI entry point (record / show)
.env.example            environment variable template
agenttape.toml          cassette config + secret redaction
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

On every subsequent run (`mode="none"`): AgentTape intercepts the call before it runs and returns the saved response. Zero network. Zero tokens.

```python
with agenttape.use_cassette("fastapi__fastapi", mode="record"):
    result = run("fastapi", "fastapi")   # calls real GitHub + LLM

with agenttape.use_cassette("fastapi__fastapi", mode="none"):
    result = run("fastapi", "fastapi")   # reads from cassette, offline
```

7 boundaries are recorded per repo: 5 GitHub API calls and 2 LLM calls.

---

## AgentTape features demonstrated

| Feature | Where |
|---|---|
| `@agenttape.tool` | All 7 external boundary functions |
| `mode="record"` | `reposcan.py record` -- writes cassette from real APIs |
| `mode="none"` | `reposcan.py show` and all pytest tests |
| `@pytest.mark.agenttape` | Every test in `tests/test_agent.py` |
| `agenttape_cassette` fixture | Boundary introspection in tests |
| Secret redaction | API keys + tokens stripped from cassette automatically |
| Git-friendly YAML cassettes | `cassettes/` committed to version control |

---

## Analysing a different repository

```bash
python reposcan.py record pallets/flask
python reposcan.py show   pallets/flask
```

Each repository gets its own cassette (`cassettes/owner__repo.yaml`). Record once, replay forever.

---

## Re-recording after the project changes

If you want a fresh snapshot of a repository's current state:

```bash
python reposcan.py record fastapi/fastapi
# or from pytest:
pytest --agenttape-record
```

---

## License

MIT
