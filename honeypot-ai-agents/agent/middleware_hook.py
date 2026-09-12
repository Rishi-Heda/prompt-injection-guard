import os
import requests
from typing import List, Dict, Any

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

def check_trajectory_guard(history_tool_names: List[str], next_tool_name: str) -> Dict[str, Any]:
    """
    Evaluates the trajectory sequence against Tier 1 before allowing execution.
    """
    full_chain = history_tool_names + [next_tool_name]
    token_sequence = [TOOL_MAP[name] for name in full_chain if name in TOOL_MAP]

    if not token_sequence:
        return {"allowed": True, "action": "ALLOW"}

    try:
        response = requests.post(
            TIER1_URL,
            json={"sequence": token_sequence},
            timeout=1.0  # 1s timeout to guarantee sub-second execution
        )
        response.raise_for_status()
        data = response.json()

        decision = data.get("decision", "ALLOW")

        if decision == "BLOCK":
            return {
                "allowed": False,
                "action": "BLOCK",
                "reason": f"Tier 1 Anomaly Killswitch (Score: {data['anomaly_score']:.4f} > {data['threshold']:.4f})"
            }

        if decision == "ESCALATE_TIER2":
            return {
                "allowed": True,  # Route to Tier 2 Sentinel LLM audit
                "action": "ESCALATE_TIER2",
                "reason": "Trajectory in gray-zone, requires semantic audit"
            }

        return {"allowed": True, "action": "ALLOW"}

    except requests.exceptions.RequestException as e:
        # Fallback to allow or fail-closed based on security posture
        print(f"[!] Tier 1 service unreachable: {e}")
        return {"allowed": False, "action": "ERROR", "reason": "Security gateway offline"}