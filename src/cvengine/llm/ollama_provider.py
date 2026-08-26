from __future__ import annotations

import logging

import ollama

from cvengine.llm.base import LLMProvider, LLMResponse
from cvengine.observability import log_event, timeit

logger = logging.getLogger("cvengine")


class OllamaProvider(LLMProvider):
    """LLM provider backed by a local Ollama server."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
    ) -> None:
        self._client = ollama.Client(host=base_url)
        self._model = model
        self._temperature = temperature
        self._base_url = base_url

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    @timeit("llm_ollama_chat")
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        json_schema: dict | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        format_value: str | dict = json_schema if json_schema is not None else ""
        response = self._client.chat(
            model=self._model,
            messages=messages,
            format=format_value,
            options={
                "temperature": self._temperature if temperature is None else temperature,
                "num_predict": 4096,
            },
        )
        log_event(
            logger,
            "ollama chat completed",
            model=self._model,
            input_tokens=response.get("prompt_eval_count", 0),
            output_tokens=response.get("eval_count", 0),
        )
        return LLMResponse(
            content=response["message"]["content"],
            input_tokens=response.get("prompt_eval_count", 0),
            output_tokens=response.get("eval_count", 0),
        )
