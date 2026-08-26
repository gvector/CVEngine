from __future__ import annotations

import logging

from openai import OpenAI

from cvengine.llm.base import LLMProvider, LLMResponse
from cvengine.observability import log_event, timeit

logger = logging.getLogger("cvengine")


class OpenAIProvider(LLMProvider):
    """LLM provider backed by the OpenAI chat completions API."""

    def __init__(self, api_key: str, model: str, temperature: float = 0.0) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._temperature = temperature

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    @timeit("llm_openai_chat")
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        json_schema: dict | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        response_format = None
        if json_schema is not None:
            response_format = {"type": "json_object"}
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=self._temperature if temperature is None else temperature,
            response_format=response_format,
        )
        log_event(
            logger,
            "openai chat completed",
            model=self._model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )
        return LLMResponse(
            content=response.choices[0].message.content or "",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )
