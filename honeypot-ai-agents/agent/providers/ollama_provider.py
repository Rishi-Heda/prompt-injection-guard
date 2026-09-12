import json
from types import SimpleNamespace
from typing import Any

import ollama


class OllamaProvider:
    """Native Ollama provider normalized to the agent's Groq-style response shape."""

    def __init__(self, think: bool = True):
        self.think = think

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
    ) -> Any:
        tool_names = [
            tool.get("function", {}).get("name", "<unnamed>")
            for tool in tools
        ]
        print(f"[ollama] model={model!r} think={self.think!r} tools={tool_names}")
        try:
            response = ollama.chat(
                model=model,
                messages=self._prepare_messages(messages),
                tools=tools,
                think=self.think,
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            )
        except Exception as error:
            print(
                f"[ollama] chat failed: model={model!r}, think={self.think!r}, "
                f"tools={tool_names}, error={type(error).__name__}: {error}"
            )
            raise
        return self._normalize_response(response)

    @staticmethod
    def _prepare_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert the loop's normalized messages to Ollama-native JSON data."""
        prepared = []
        for message in messages:
            item = {
                "role": message.get("role"),
                "content": message.get("content") or "",
            }
            if message.get("role") == "assistant" and message.get("tool_calls"):
                item["tool_calls"] = [
                    {
                        "function": {
                            "name": OllamaProvider._value(
                                OllamaProvider._value(call, "function", {}),
                                "name",
                                "",
                            ),
                            "arguments": OllamaProvider._arguments(
                                OllamaProvider._value(call, "function", {})
                            ),
                        }
                    }
                    for call in message["tool_calls"]
                ]
            prepared.append(item)
        return prepared

    @staticmethod
    def _arguments(function: Any) -> dict[str, Any]:
        arguments = OllamaProvider._value(function, "arguments", {}) or {}
        if isinstance(arguments, str):
            return json.loads(arguments)
        return arguments

    @staticmethod
    def _normalize_response(response: Any) -> Any:
        message = response.get("message", {}) if isinstance(response, dict) else response.message
        content = OllamaProvider._value(message, "content", "") or ""
        thinking = (
            OllamaProvider._value(message, "thinking")
            or OllamaProvider._value(message, "reasoning")
            or ""
        )
        raw_tool_calls = OllamaProvider._value(message, "tool_calls", []) or []
        tool_calls = []
        for index, tool_call in enumerate(raw_tool_calls):
            function = OllamaProvider._value(tool_call, "function", {})
            arguments = OllamaProvider._value(function, "arguments", {}) or {}
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments)
            tool_calls.append(
                SimpleNamespace(
                    id=OllamaProvider._value(tool_call, "id", f"ollama-tool-{index}"),
                    type="function",
                    function=SimpleNamespace(
                        name=OllamaProvider._value(function, "name", ""),
                        arguments=arguments,
                    ),
                )
            )
        normalized_message = SimpleNamespace(
            role=OllamaProvider._value(message, "role", "assistant"),
            content=content,
            reasoning=thinking,
            tool_calls=tool_calls,
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=normalized_message)],
            model=OllamaProvider._value(response, "model", None),
        )

    @staticmethod
    def _value(item: Any, key: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)
