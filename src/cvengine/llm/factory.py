from __future__ import annotations

from cvengine.config import LLMSettings
from cvengine.llm.base import LLMProvider
from cvengine.llm.ollama_provider import OllamaProvider
from cvengine.llm.openai_provider import OpenAIProvider


def build_llm(settings: LLMSettings) -> LLMProvider:
    """Instantiate the configured LLM provider.

    :param settings: the LLM configuration section
    :return: a ready-to-use provider
    :raises ValueError: if the provider name is unknown
    """
    provider = settings.provider.lower()
    if provider == "ollama":
        return OllamaProvider(
            model=settings.model,
            base_url=settings.base_url,
            temperature=settings.temperature,
        )
    if provider == "openai":
        if not settings.api_key:
            raise ValueError("OpenAI provider requires CVENGINE_LLM_API_KEY")
        return OpenAIProvider(
            api_key=settings.api_key,
            model=settings.model,
            temperature=settings.temperature,
        )
    raise ValueError(f"Unknown LLM provider: {settings.provider!r}")
