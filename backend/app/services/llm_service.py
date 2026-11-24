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
GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"


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

    def __init__(self) -> None:
        self._resolved: dict[str, str] = {}  # provider -> model found by discovery after a retirement

    def model_for(self, provider: str) -> str:
        configured = {"gemini": settings.gemini_model, "groq": settings.groq_model, "openai": settings.openai_model}[provider]
        return self._resolved.get(provider, configured)

    def model_name(self) -> str | None:
        p = self.provider()
        return self.model_for(p) if p else None

    last_error: str | None = None  # short, key-free description of the most recent failure

    def candidates(self) -> list[str]:
        """Configured providers in the order they are tried: the chosen one first, then the others."""
        keys = {"gemini": settings.gemini_api_key, "groq": settings.groq_api_key, "openai": settings.openai_api_key}
        first = self.provider()
        rest = [p for p, k in keys.items() if k and p != first]
        return ([first] if first else []) + rest

    def chat(self, messages: list[Message], system: str = "", json_mode: bool = False, temperature: float = 0.4) -> str:
        providers = self.candidates()
        if not providers:
            raise LLMError("No LLM API key configured")
        errors = []
        for provider in providers:  # fall back to the next configured provider on failure
            try:
                text = self._call_with_model_recovery(provider, messages, system, json_mode, temperature)
                self.used_provider = provider
                self.last_error = "; ".join(errors) or None  # earlier providers that failed, if any
                return text
            except httpx.HTTPStatusError as exc:
                detail = _error_detail(exc.response)
                errors.append(f"{provider}: HTTP {exc.response.status_code}{' ' + detail if detail else ''}")
            except (httpx.HTTPError, LLMError) as exc:
                errors.append(f"{provider}: {type(exc).__name__}")
            log.warning("LLM provider failed: %s", errors[-1])
        self.last_error = "; ".join(errors)
        raise LLMError(self.last_error)

    used_provider: str | None = None

    def chat_json(self, prompt: str, system: str = "") -> dict:
        """Ask for a JSON object and parse it defensively."""
        text = self.chat([Message("user", prompt)], system=system, json_mode=True, temperature=0.2)
        return parse_json_object(text)

    # -- model recovery ----------------------------------------------------
    def _send(self, provider, model, messages, system, json_mode, temperature) -> str:
        if provider == "gemini":
            return self._gemini(messages, system, json_mode, temperature, model=model)
        return self._openai_compatible(provider, messages, system, json_mode, temperature, model=model)

    def _call_with_model_recovery(self, provider, messages, system, json_mode, temperature) -> str:
        """Call the provider; if its model was retired, switch to a currently available one and retry once."""
        model = self.model_for(provider)
        try:
            return self._send(provider, model, messages, system, json_mode, temperature)
        except httpx.HTTPStatusError as exc:
            if not _is_model_error(exc.response):
                raise
            replacement = self._discover_model(provider, exclude=model)
            if not replacement:
                raise
            log.warning("LLM model %s/%s unavailable, switching to %s", provider, model, replacement)
            self._resolved[provider] = replacement
            return self._send(provider, replacement, messages, system, json_mode, temperature)

    def _discover_model(self, provider: str, exclude: str = "") -> str | None:
        """Ask the provider which chat models exist now and pick a sensible one."""
        try:
            if provider == "gemini":
                r = httpx.get(GEMINI_MODELS_URL, headers={"x-goog-api-key": settings.gemini_api_key},
                              params={"pageSize": 200}, timeout=settings.llm_timeout)
                r.raise_for_status()
                names = [m["name"].split("/", 1)[-1] for m in r.json().get("models", [])
                         if "generateContent" in m.get("supportedGenerationMethods", [])]
            else:
                url, key = (GROQ_MODELS_URL, settings.groq_api_key) if provider == "groq" else (OPENAI_MODELS_URL, settings.openai_api_key)
                r = httpx.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=settings.llm_timeout)
                r.raise_for_status()
                names = [m["id"] for m in r.json().get("data", []) if m.get("active", True)]
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            log.warning("Model discovery failed for %s: %s", provider, type(exc).__name__)
            return None
        return pick_model(provider, [n for n in names if n != exclude])

    # -- providers ---------------------------------------------------------
    def _gemini(self, messages, system, json_mode, temperature, model=None) -> str:
        body: dict = {
            "contents": [{"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.content}]} for m in messages],
            "generationConfig": {"temperature": temperature},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        r = httpx.post(GEMINI_URL.format(model=model or self.model_for("gemini")), json=body,
                       headers={"x-goog-api-key": settings.gemini_api_key}, timeout=settings.llm_timeout)
        r.raise_for_status()
        try:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMError("Unexpected Gemini response") from exc

    def _openai_compatible(self, provider, messages, system, json_mode, temperature, model=None) -> str:
        url, key = (GROQ_URL, settings.groq_api_key) if provider == "groq" else (OPENAI_URL, settings.openai_api_key)
        model = model or self.model_for(provider)
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


def _is_model_error(response: httpx.Response) -> bool:
    """True when the provider rejected the model name (retired, renamed or not allowed)."""
    if response.status_code == 404:
        return True
    if response.status_code in (400, 403):
        text = _error_detail(response).lower()
        return "model" in text and any(w in text for w in ("not found", "no longer", "does not exist", "decommission", "deprecat", "not supported"))
    return False


_SKIP = ("embed", "embedding", "whisper", "tts", "audio", "image", "vision-only", "guard", "moderation", "aqa",
         "imagen", "veo", "live", "transcribe", "realtime", "search", "computer-use", "robotics", "nano", "gemma")


def _version(name: str) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", name)[:3]) or (0,)


def pick_model(provider: str, names: list[str]) -> str | None:
    """Choose a fast, general chat model from a provider's live model list."""
    pool = [n for n in names if not any(s in n.lower() for s in _SKIP)]
    stable = [n for n in pool if not any(t in n.lower() for t in ("preview", "exp", "experimental"))] or pool
    if provider == "gemini":
        ranked = ([n for n in stable if "flash" in n and "lite" not in n]
                  or [n for n in stable if "flash" in n] or stable)
        aliases = [n for n in ranked if n.endswith("-latest")]
        return aliases[0] if aliases else (max(ranked, key=_version) if ranked else None)
    if provider == "groq":
        for want in (("llama", "versatile"), ("llama", "70b"), ("gpt-oss", "120b"), ("llama",), ("qwen",), ("gpt-oss",)):
            hits = [n for n in stable if all(w in n.lower() for w in want)]
            if hits:
                return max(hits, key=_version)
        return stable[0] if stable else None
    hits = [n for n in stable if n.startswith("gpt-") and "mini" in n] or [n for n in stable if n.startswith("gpt-")]
    return max(hits, key=_version) if hits else None


def _error_detail(response: httpx.Response) -> str:
    """Provider error message without secrets (providers never echo the key back)."""
    try:
        err = response.json().get("error", {})
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
    except ValueError:
        msg = ""
    msg = re.sub(r"(AIza|gsk_|sk-)[A-Za-z0-9_\-]+", "[key]", msg)
    return msg[:160]


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
