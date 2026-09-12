import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

from .middleware_hook import guard_tool_execution
from .providers import create_provider
from .system_prompt import SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, execute_tool

# --- Tier 0 Canary Imports ---
from tier0_canary.canary_planter import CanaryPlanter
from tier0_canary.leak_detector import LeakDetector
from tier0_canary.kill_switch import KillSwitch

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
        # 1. Initialize Tier 0 Canary System for this session
        session_id = str(uuid.uuid4())
        planter = CanaryPlanter()
        detector = LeakDetector(planter.get_all_canaries(), planter.get_canary_source_map())
        kill_switch = KillSwitch(session_id)

        full_user_prompt = f"{user_task}\nDocument ID: {doc_id}" if doc_id else user_task
        
        # 2. Inject Canary Tokens into the System Prompt
        secured_system_prompt = planter.inject_into_system_prompt(SYSTEM_PROMPT)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": secured_system_prompt},
            {"role": "user", "content": full_user_prompt},
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

            # Reconstruct executed tool history for firewall inspection
            executed_history = [
                {"name": t["tool"], "args": t["input"]}
                for t in trace
                if t.get("tool")
            ]

            for tool_call in tool_calls:
                function = _value(tool_call, "function", {})
                name = _value(function, "name")
                raw_arguments = _value(function, "arguments", "{}")
                if isinstance(raw_arguments, str):
                    try:
                        arguments = json.loads(raw_arguments)
                    except json.JSONDecodeError:
                        import ast
                        try:
                            # Handle unescaped raw newlines or loose single quotes
                            cleaned = raw_arguments.replace("\n", "\\n").replace("\r", "\\r")
                            arguments = json.loads(cleaned)
                        except Exception:
                            try:
                                arguments = ast.literal_eval(raw_arguments)
                            except Exception:
                                arguments = {"raw_payload": raw_arguments}
                else:
                    arguments = raw_arguments or {}

                # 3. TIER 0 FIREWALL: Fast String-Matching Canary Check
                leak_result = detector.scan_all_tool_args(name, arguments)
                if leak_result.leaked:
                    incident = kill_switch.trigger(leak_result, name, arguments)
                    output = (
                        f"[CRITICAL SECURITY ALERT] Tier 0 Kill Switch Triggered! "
                        f"Data exfiltration attempt detected. "
                        f"Leaked source(s): {', '.join(incident.compromised_sources)}. "
                        f"Session terminated immediately."
                    )
                    trace.append(self._entry(step, reasoning, name, arguments, output))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": _value(tool_call, "id"),
                        "content": output,
                    })
                    return output, trace

                # 4. Multi-Tier Firewall Interception (Tier 1 & Tier 2)
                guard_result = guard_tool_execution(
                    user_prompt=full_user_prompt,
                    tool_history=executed_history,
                    pending_tool={"name": name, "args": arguments},
                    agent_thought=reasoning,
                )

                if not guard_result["allowed"]:
                    output = (
                        f"[SECURITY ALERT] Execution blocked by {guard_result['tier_source']}: "
                        f"{guard_result['reason']}"
                    )
                    trace.append(self._entry(step, reasoning, name, arguments, output))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": _value(tool_call, "id"),
                        "content": output,
                    })
                    return f"Action blocked by AI Security Firewall: {guard_result['reason']}", trace

                # Legitimate tool dispatch
                output = execute_tool(name, arguments)
                executed_history.append({"name": name, "args": arguments})

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