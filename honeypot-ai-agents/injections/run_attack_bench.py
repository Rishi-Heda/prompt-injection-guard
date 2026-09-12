import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from injections.payloads import INJECTION_PAYLOADS
from agent.middleware_hook import guard_tool_execution
from tier0_canary.canary_planter import CanaryPlanter
from tier0_canary.leak_detector import LeakDetector

def test_attack_suite():
    print("==================================================")
    print("RUNNING ADVERSARIAL INJECTION BENCHMARK")
    print("==================================================\n")

    # Initialize a mock Tier 0 session for the offline benchmark
    planter = CanaryPlanter()
    detector = LeakDetector(planter.get_all_canaries(), planter.get_canary_source_map())

    for attack in INJECTION_PAYLOADS:
        print(f"[*] Testing: {attack['id']} ({attack['type']})")
        print(f"    Description: {attack['description']}")

        traj = attack["trajectory"]
        history = traj[:-1]
        pending = traj[-1]

        # 1. Tier 0 Check (Simulated)
        # Check if the payload trajectory accidentally/intentionally includes a canary
        leak_result = detector.scan_all_tool_args(pending["name"], pending.get("args", {}))
        
        if leak_result.leaked:
            print(f"    Result:      BLOCKED")
            print(f"    Tier Source: TIER0_CANARY")
            print(f"    Reason:      Leaked tokens {leak_result.leaked_tokens}\n")
            continue

        # 2. Tier 1 & 2 Check (Your existing logic)
        result = guard_tool_execution(
            user_prompt=attack.get("user_prompt", ""),
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