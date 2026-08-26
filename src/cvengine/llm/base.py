"""LLM provider abstraction for OpenAI and Ollama."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """A response from an LLM provider with token accounting."""

    content: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(ABC):
    """Interface for chat-based LLM providers with optional JSON output."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def model(self) -> str: ...

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        json_schema: dict | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Send a chat completion.

        :param messages: list of ``{"role": ..., "content": ...}`` messages
        :param json_schema: optional JSON schema to constrain the output
        :param temperature: optional temperature override
        :return: the model response with token counts
        """
