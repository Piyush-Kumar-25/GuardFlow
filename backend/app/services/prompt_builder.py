from typing import Any, Dict


class PromptBuilder:
    """Builds structured prompts for website analysis by the LLM."""

    def build_website_prompt(self, website: Dict[str, Any]) -> str:
        """Construct a plain-text prompt describing a website for Ollama."""
        url = website.get("url", "")
        title = website.get("title", "")
        raw = website.get("raw", {}) or {}

        prompt_lines = [
            "You are a fraud detection assistant.",
            "Analyze the website and return only JSON with the keys:",
            "  website_risk, reason, confidence",
            "Respond with `website_risk` as an integer 0-100,",
            "`confidence` as an integer 0-100, and a short `reason`.",
            "",
            "Website metadata:",
            f"URL: {url}",
            f"Title: {title}",
        ]

        if raw:
            prompt_lines.append("Raw payload:")
            for key, value in raw.items():
                prompt_lines.append(f"- {key}: {value}")

        prompt_lines.extend([
            "",
            "Instructions:",
            "- Evaluate the site for possible fraud, phishing, or malicious behavior.",
            "- Do not add any other keys to the JSON output.",
            "- Keep `reason` concise and clear.",
        ])

        return "\n".join(prompt_lines)
