import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from injections.payloads import INJECTION_PAYLOADS
from agent.middleware_hook import guard_tool_execution

def test_attack_suite():
    print("==================================================")
    print("RUNNING ADVERSARIAL INJECTION BENCHMARK")
    print("==================================================\n")

    for attack in INJECTION_PAYLOADS:
        print(f"[*] Testing: {attack['id']} ({attack['type']})")
        print(f"    Description: {attack['description']}")

        # Split trajectory: all previous calls are history, final call is pending
        traj = attack["trajectory"]
        history = traj[:-1]
        pending = traj[-1]

        result = guard_tool_execution(
            user_prompt=attack["user_prompt"],
            tool_history=history,
            pending_tool=pending
        )

        status = "BLOCKED" if not result["allowed"] else "ALLOWED / APPROVED"
        print(f"    Result:      {status}")
        print(f"    Tier Source: {result.get('tier_source')}")
        if result.get("score") is not None:
            print(f"    Score:       {result.get('score'):.6f}")
        print(f"    Reason:      {result.get('reason')}\n")

if __name__ == "__main__":
    test_attack_suite()