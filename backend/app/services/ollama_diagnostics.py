"""Synchronous CLI diagnostics, separate from the application's async chat service."""

from time import perf_counter

import httpx
from pydantic import Field

from app.core.config import Settings
from app.schemas.real_programs import StrictModel


class DiagnosticResult(StrictModel):
    server_url: str
    configured_model: str
    reachable: bool = False
    installed_models: list[str] | None = None
    model_available: bool | None = None
    response: str | None = None
    response_seconds: float | None = None
    total_seconds: float = 0
    error: str | None = None
    instructions: list[str] = Field(default_factory=list)


def diagnose_ollama(settings: Settings, client: httpx.Client) -> DiagnosticResult:
    result = DiagnosticResult(
        server_url=settings.ollama_base_url, configured_model=settings.ollama_model
    )
    started = perf_counter()
    try:
        tags = client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
        result.reachable = True
        tags.raise_for_status()
        models = tags.json()["models"]
        if not isinstance(models, list):
            raise ValueError("models must be a list")
        names = [item["name"] for item in models]
        if any(not isinstance(name, str) or not name for name in names):
            raise ValueError("invalid installed model name")
        result.installed_models = names
        configured = settings.ollama_model
        result.model_available = configured in names or (
            ":" not in configured and configured + ":latest" in names
        )
        if not result.model_available:
            result.error = f"Configured model '{configured}' is not installed."
            result.instructions = [
                f"To install it manually, run: ollama pull {configured}",
                "This may be a large download; no model was downloaded by this diagnostic.",
            ]
            return result
        inference_started = perf_counter()
        try:
            response = client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": configured,
                    "stream": False,
                    "messages": [
                        {"role": "user", "content": "Reply with: LifePilot diagnostic OK"}
                    ],
                    "options": {"temperature": 0, "num_predict": 40},
                },
            )
        finally:
            result.response_seconds = perf_counter() - inference_started
        response.raise_for_status()
        content = response.json()["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty/non-text model reply")
        result.response = content.strip()
    except httpx.TimeoutException:
        result.error = "Ollama request timed out; check server load and OLLAMA_TIMEOUT_SECONDS."
    except httpx.RequestError as exc:
        result.error = f"Cannot reach Ollama: {type(exc).__name__}: {exc}"
        result.instructions = [
            "Start the server manually: ollama serve",
            "Check OLLAMA_BASE_URL in the project's .env and ensure the port is reachable.",
            "After starting the server, rerun this script to check models and inference.",
        ]
    except httpx.HTTPStatusError as exc:
        result.error = f"Ollama returned HTTP {exc.response.status_code}."
        if exc.response.status_code == 404:
            result.instructions = [
                f"Check the endpoint/model; install manually: ollama pull {settings.ollama_model}"
            ]
    except (ValueError, KeyError, TypeError):
        result.error = "Ollama returned invalid JSON or an unexpected response structure."
    finally:
        result.total_seconds = perf_counter() - started
    return result
