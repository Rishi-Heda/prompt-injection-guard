import os
from typing import Any

from openai import OpenAI


class OpenRouterProvider:
    """OpenRouter adapter using its OpenAI-compatible chat completions API."""

    def __init__(self, client: OpenAI | None = None):
        self.client = client or OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
    ) -> Any:
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=max_tokens,
            temperature=temperature,
        )
