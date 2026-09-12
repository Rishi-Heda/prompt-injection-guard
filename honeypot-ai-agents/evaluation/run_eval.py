import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from agent.base_agent import Agent
from evaluation.metrics import EvaluationMetrics

def run_evaluation():
    print("Starting End-to-End Agent Evaluation...")
    agent = Agent()
    metrics = EvaluationMetrics()
    
    test_cases_path = os.path.join(BASE_DIR, "injections", "test_cases.json")
    try:
        with open(test_cases_path, "r") as f:
            test_cases = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {test_cases_path}")
        return

    for case in test_cases:
        print(f"\n[*] Running case: {case['id']} ({case['category']})")
        
        try:
            # We pass the doc_id to trigger the READ_FILE flow for injections
            doc_id = f"{case['id']}.html" if case['should_flag'] else "clean-doc"
            answer, trace = agent.run("Read and summarize the document.", doc_id)
            
            allowed = True
            tier_source = "NONE"
            
            # Check the trace for security blocks
            for step in trace:
                if step["output"] and "SECURITY ALERT" in step["output"]:
                    allowed = False
                    if "Tier 0" in step["output"] or "Canary" in step["output"]:
                        tier_source = "Tier 0 Canary"
                    elif "TIER1" in step["output"]:
                        tier_source = "TIER1_FAST_GATEWAY"
                    elif "TIER2" in step["output"]:
                        tier_source = "TIER2_SENTINEL_LLM"
                    break
            
            print(f"    Result: {'ALLOWED' if allowed else 'BLOCKED by ' + tier_source}")
            metrics.log_result(
                is_attack=case["should_flag"], 
                allowed=allowed, 
                tier_source=tier_source
            )
            
        except Exception as e:
            print(f"    [!] Error running case: {e}")

    metrics.print_summary()

if __name__ == "__main__":
    run_evaluation()