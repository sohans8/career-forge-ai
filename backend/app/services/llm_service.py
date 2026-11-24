"""Unified LLM client for Gemini, Groq and OpenAI.

One interface for the mentor, the resume analyzer and the education watcher.
When no API key is configured, `available` is False and callers fall back to
deterministic logic, so the app still works offline.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import httpx

from backend.app.config import settings

log = logging.getLogger("career_forge.llm")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class LLMError(RuntimeError):
    pass


@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str


class LLMService:
    def provider(self) -> str | None:
        """Return the provider that will be used, or None when no key is set."""
        order = {"gemini": settings.gemini_api_key, "groq": settings.groq_api_key, "openai": settings.openai_api_key}
        wanted = settings.llm_provider
        if wanted in order:
            return wanted if order[wanted] else None
        for name, key in order.items():  # auto: first configured key wins
            if key:
                return name
        return None

    @property
    def available(self) -> bool:
        return self.provider() is not None

    def model_name(self) -> str | None:
        p = self.provider()
        return {"gemini": settings.gemini_model, "groq": settings.groq_model, "openai": settings.openai_model}.get(p or "")

    def chat(self, messages: list[Message], system: str = "", json_mode: bool = False, temperature: float = 0.4) -> str:
        provider = self.provider()
        if provider is None:
            raise LLMError("No LLM API key configured")
        try:
            if provider == "gemini":
                return self._gemini(messages, system, json_mode, temperature)
            return self._openai_compatible(provider, messages, system, json_mode, temperature)
        except httpx.HTTPError as exc:
            log.warning("LLM request failed: %s", type(exc).__name__)
            raise LLMError(f"{provider} request failed") from exc

    def chat_json(self, prompt: str, system: str = "") -> dict:
        """Ask for a JSON object and parse it defensively."""
        text = self.chat([Message("user", prompt)], system=system, json_mode=True, temperature=0.2)
        return parse_json_object(text)

    # -- providers ---------------------------------------------------------
    def _gemini(self, messages, system, json_mode, temperature) -> str:
        body: dict = {
            "contents": [{"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.content}]} for m in messages],
            "generationConfig": {"temperature": temperature},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        r = httpx.post(GEMINI_URL.format(model=settings.gemini_model), json=body,
                       headers={"x-goog-api-key": settings.gemini_api_key}, timeout=settings.llm_timeout)
        r.raise_for_status()
        try:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMError("Unexpected Gemini response") from exc

    def _openai_compatible(self, provider, messages, system, json_mode, temperature) -> str:
        url, key, model = (
            (GROQ_URL, settings.groq_api_key, settings.groq_model) if provider == "groq"
            else (OPENAI_URL, settings.openai_api_key, settings.openai_model)
        )
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": m.role, "content": m.content} for m in messages]
        body: dict = {"model": model, "messages": msgs, "temperature": temperature}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        r = httpx.post(url, json=body, headers={"Authorization": f"Bearer {key}"}, timeout=settings.llm_timeout)
        r.raise_for_status()
        try:
            return r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError("Unexpected response") from exc


def parse_json_object(text: str) -> dict:
    """Parse a JSON object from model output, tolerating code fences and prose."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise LLMError("Model did not return JSON")
        try:
            value = json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError("Model returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise LLMError("Model JSON was not an object")
    return value


llm_service = LLMService()
