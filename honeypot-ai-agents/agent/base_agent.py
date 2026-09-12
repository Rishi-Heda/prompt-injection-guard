import json
import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

from .providers import create_provider
from .system_prompt import SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, execute_tool


MAX_STEPS = 6


def _value(item: Any, key: str, default: Any = None) -> Any:
	if isinstance(item, dict):
		return item.get(key, default)
	return getattr(item, key, default)


def _extract_reasoning(message: Any, tool_calls: Any) -> str:
	"""Use normal assistant content as the explanation before tool calls."""
	if tool_calls:
		return _value(message, "reasoning", "") or _value(message, "content", "") or ""
	return ""


class Agent:
	def __init__(self, client: Any = None, model: str | None = None):
		load_dotenv()
		self.provider_name = os.getenv("MODEL_PROVIDER", "groq").lower()
		self.provider = create_provider(self.provider_name, client=client)
		if self.provider_name == "groq":
			default_model = os.getenv("GROQ_MODEL")
		elif self.provider_name == "ollama":
			default_model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
		else:
			default_model = os.getenv("OPENROUTER_MODEL", "qwen/qwen3-8b:free")
		self.model = model or os.getenv("MODEL_NAME") or default_model
		self.max_tokens = int(os.getenv("GROQ_MAX_TOKENS", "768"))
		self.temperature = float(os.getenv("AGENT_TEMPERATURE", "0.2"))

	def run(
		self,
		user_task: str,
		doc_id: str = "",
	) -> tuple[str, list[dict[str, Any]]]:
		messages: list[dict[str, Any]] = [
			{"role": "system", "content": SYSTEM_PROMPT},
			{"role": "user", "content": f"{user_task}\nDocument ID: {doc_id}" if doc_id else user_task},
		]
		trace: list[dict[str, Any]] = []

		for step in range(1, MAX_STEPS + 1):
			response = self.provider.complete(
				model=self.model,
				messages=messages,
				tools=TOOL_SCHEMAS,
				max_tokens=self.max_tokens,
				temperature=self.temperature,
			)
			message = response.choices[0].message
			tool_calls = _value(message, "tool_calls", []) or []
			reasoning = _extract_reasoning(message, tool_calls)

			if not tool_calls:
				output = _value(message, "content", "") or ""
				trace.append(self._entry(step, reasoning, None, None, output))
				return output, trace

			messages.append({
				"role": "assistant",
				"content": _value(message, "content", "") or None,
				"tool_calls": tool_calls,
			})
			for tool_call in tool_calls:
				function = _value(tool_call, "function", {})
				name = _value(function, "name")
				raw_arguments = _value(function, "arguments", "{}")
				arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
				output = execute_tool(name, arguments)
				trace.append(self._entry(step, reasoning, name, arguments, output))
				messages.append({
					"role": "tool",
					"tool_call_id": _value(tool_call, "id"),
					"content": output,
				})

		raise RuntimeError(f"Agent reached the {MAX_STEPS}-step limit without a final answer.")

	@staticmethod
	def _entry(
		step: int,
		reasoning: str,
		tool: str | None,
		tool_input: Any,
		output: str,
	) -> dict[str, Any]:
		return {
			"step": step,
			"timestamp": datetime.now(timezone.utc).isoformat(),
			"reasoning": reasoning,
			"tool": tool,
			"input": tool_input,
			"output": output,
		}
