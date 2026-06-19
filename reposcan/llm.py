"""
Multi-provider LLM dispatcher for RepoScope.

Select a provider via LLM_PROVIDER environment variable (default: gemini).
All values are read at call time, so .env changes take effect without restart.

    LLM_PROVIDER=gemini      (default — free, needs GEMINI_API_KEY)
    LLM_PROVIDER=ollama      (local, free, needs Ollama running)
    LLM_PROVIDER=anthropic   (needs ANTHROPIC_API_KEY)
    LLM_PROVIDER=openai      (needs OPENAI_API_KEY)
"""

from __future__ import annotations
import os


def _provider() -> str:
    return os.environ.get("LLM_PROVIDER", "gemini").lower()


def chat(system: str, user: str) -> str:
    """Send a system+user prompt to the configured LLM provider."""
    p = _provider()
    if p == "gemini":
        return _gemini(system, user)
    if p == "ollama":
        return _ollama(system, user)
    if p == "anthropic":
        return _anthropic(system, user)
    if p == "openai":
        return _openai(system, user)
    raise ValueError(
        f"Unknown LLM_PROVIDER={p!r}. Valid options: gemini, ollama, anthropic, openai"
    )


def _gemini(system: str, user: str) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError("Run: pip install google-genai")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set.\n"
            "Get a free key at https://aistudio.google.com/apikey\n"
            "Then add it to your .env file: GEMINI_API_KEY=AIza..."
        )

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=1500,
        ),
    )
    return response.text


def _ollama(system: str, user: str) -> str:
    try:
        import ollama
    except ImportError:
        raise ImportError("Run: pip install ollama")

    model    = os.environ.get("OLLAMA_MODEL", "llama3.2")
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    client   = ollama.Client(host=base_url)
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return response.message.content


def _anthropic(system: str, user: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise ImportError("Run: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set.\n"
            "Get a key at https://console.anthropic.com\n"
            "Then add it to your .env file: ANTHROPIC_API_KEY=sk-ant-..."
        )

    model  = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    client = anthropic.Anthropic(api_key=api_key)
    msg    = client.messages.create(
        model=model,
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


def _openai(system: str, user: str) -> str:
    try:
        import openai
    except ImportError:
        raise ImportError("Run: pip install openai")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set.\n"
            "Get a key at https://platform.openai.com/api-keys\n"
            "Then add it to your .env file: OPENAI_API_KEY=sk-..."
        )

    model    = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    client   = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_tokens=1500,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return response.choices[0].message.content
