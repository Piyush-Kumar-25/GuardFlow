from typing import Any, Dict, Optional

from app.services.prompt_builder import PromptBuilder
from app.services.llm_service import LLMService


class WebsiteAnalyzer:
    """Analyzes website events by building a prompt and calling an LLM service."""

    def __init__(self, prompt_builder: Optional[PromptBuilder] = None, llm_service: Optional[LLMService] = None):
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.llm_service = llm_service or LLMService()

    def analyze(self, website: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self.prompt_builder.build_website_prompt(website)
        result = self.llm_service.analyze(prompt)

        # Validate and normalize expected output keys.
        return {
            "website_risk": float(result.get("website_risk", 0)),
            "reason": str(result.get("reason", "No reason provided")),
            "confidence": float(result.get("confidence", 0)),
        }
