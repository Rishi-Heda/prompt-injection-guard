from typing import Any

from groq import Groq


class GroqProvider:
    def __init__(self, client: Groq | None = None):
        import os

        self.client = client or Groq(api_key=os.environ["GROQ_API_KEY"])

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
