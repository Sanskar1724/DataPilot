"""OpenRouter chat client (small, focused wrapper around httpx)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenRouterError(RuntimeError):
    """Raised when the OpenRouter request fails or times out."""


class MissingApiKeyError(OpenRouterError):
    """Raised when no OPENROUTER_API_KEY is configured."""


class UnsupportedFeatureError(OpenRouterError):
    """Raised when the configured model/provider does not support a requested
    feature (e.g. structured output / response_format)."""


def _feature_blocked_reason(status_code: int, text: str) -> str | None:
    """Return a feature name if the error indicates unsupported functionality."""
    lowered = text.lower()
    for marker in (
        "does not support feature",
        "not support structured-outputs",
        "structured-outputs",
        "response_format not supported",
        "not supported by model",
    ):
        if marker in lowered:
            return marker
    return None


@dataclass
class Completion:
    """A completed LLM call with usage metadata."""

    content: str
    model: str
    latency_ms: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class OpenRouterClient:
    """Thin httpx wrapper around the OpenRouter chat completions endpoint.

    The client never touches data; it only exchanges prompt metadata for text.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._http = httpx.Client(timeout=self.settings.openrouter_timeout)

    # ------------------------------------------------------------------ #

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 4000,
        response_format: dict[str, str] | None = None,
        retries: int = 2,
    ) -> Completion:
        """Send a chat request.

        Args:
            messages: OpenAI-style [{role, content}, ...].
            temperature: 0 for deterministic structured output.
            max_tokens: cap on the completion.
            response_format: e.g. {"type": "json_object"}.
            retries: how many times to retry on 5xx/429/timeout.

        Raises:
            MissingApiKeyError: no API key set.
            OpenRouterError: request failed after retries.
        """
        if not self.settings.has_api_key:
            raise MissingApiKeyError(
                "OPENROUTER_API_KEY is not set. Add it to your .env file."
            )

        payload: dict[str, Any] = {
            "model": self.settings.openrouter_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        url = f"{self.settings.openrouter_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        if self.settings.openrouter_http_referer:
            headers["HTTP-Referer"] = self.settings.openrouter_http_referer
        if self.settings.openrouter_app_name:
            headers["X-Title"] = self.settings.openrouter_app_name

        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            start = time.perf_counter()
            try:
                resp = self._http.post(url, json=payload, headers=headers)
                latency = int((time.perf_counter() - start) * 1000)

                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = 2 ** (attempt + 1)
                    logger.warning(
                        "OpenRouter returned %s (attempt %s); retrying in %ss",
                        resp.status_code,
                        attempt + 1,
                        wait,
                    )
                    time.sleep(wait)
                    continue

                if resp.status_code == 400:
                    reason = _feature_blocked_reason(resp.status_code, resp.text)
                    if reason is not None:
                        raise UnsupportedFeatureError(
                            f"{self.settings.openrouter_model} does not support "
                            f"{reason}. Response: {resp.text[:200]}"
                        )

                resp.raise_for_status()
                return self._parse(resp.json(), latency)

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                wait = 2 ** (attempt + 1)
                logger.warning("OpenRouter HTTP %s; retrying in %ss", exc.response.status_code, wait)
                if attempt < retries:
                    time.sleep(wait)
                    continue
                raise OpenRouterError(f"OpenRouter HTTP error: {exc}") from exc
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                wait = 2 ** (attempt + 1)
                logger.warning("OpenRouter connection error: %s; retrying in %ss", exc, wait)
                if attempt < retries:
                    time.sleep(wait)
                    continue
                raise OpenRouterError(str(exc)) from exc

        raise OpenRouterError(f"Request failed after retries: {last_exc}")

    # ------------------------------------------------------------------ #

    def _parse(self, data: dict[str, Any], latency_ms: int) -> Completion:
        choice = (data.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content") or ""
        usage = data.get("usage") or {}
        return Completion(
            content=content,
            model=self.settings.openrouter_model,
            latency_ms=latency_ms,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            raw=data,
        )

    def close(self) -> None:
        self._http.close()