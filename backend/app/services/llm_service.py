import json
from typing import Any, Dict

import httpx
from app.core.settings import settings


class LLMService:
    """Minimal LLM client responsible for prompt delivery and result parsing."""

    def analyze(self, prompt: str) -> Dict[str, Any]:
        """Send prompt to Ollama and parse JSON response."""
        url = f"{settings.OLLAMA_URL}/v1/completions"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "max_tokens": 300,
            "temperature": 0.0,
        }

        response = httpx.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Ollama may return text in a nested structure; parse the first completion.
        if not data or "choices" not in data or not data["choices"]:
            raise ValueError("Invalid response from Ollama")

        text = data["choices"][0].get("text") or data["choices"][0].get("message", {}).get("content")
        if not text:
            raise ValueError("Empty completion text from Ollama")

        # Attempt to parse JSON content from the model response.
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as exc:
            raise ValueError(f"Unable to parse Ollama JSON response: {exc}; raw={text}") from exc
