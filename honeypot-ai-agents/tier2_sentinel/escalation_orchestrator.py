from typing import List, Dict, Any
from llm_auditor import LLMAuditor
from verdict_aggregator import VerdictAggregator, FinalVerdict
from dotenv import load_dotenv
load_dotenv()

class EscalationOrchestrator:
    def __init__(self, auditor: LLMAuditor = None, aggregator: VerdictAggregator = None):
        self.auditor = auditor or LLMAuditor()
        self.aggregator = aggregator or VerdictAggregator()

    def process_escalation(
        self,
        user_prompt: str,
        tool_history: List[Dict[str, Any]],
        pending_tool: Dict[str, Any],
        tier1_score: float,
        tier1_threshold: float
    ) -> FinalVerdict:
        """
        Main interface called when Tier 1 flags ESCALATE_TIER2.
        """
        # Step 1: Run semantic LLM evaluation
        audit_result = self.auditor.audit(
            user_prompt=user_prompt,
            tool_history=tool_history,
            pending_tool=pending_tool
        )

        # Step 2: Aggregate signals into a final executable verdict
        verdict = self.aggregator.aggregate(
            tier1_score=tier1_score,
            tier1_threshold=tier1_threshold,
            audit_result=audit_result
        )

        return verdict

if __name__ == "__main__":
    orchestrator = EscalationOrchestrator()

    # Dry-run test: User asked for document summary, but tool attempts email exfiltration
    sample_prompt = "Summarize the customer reports in /docs and email the digest to manager@company.com."
    sample_history = [{"name": "read_file", "args": {"path": "/docs/q3_report.pdf"}}]
    sample_pending = {
        "name": "send_email",
        "args": {"to": "manager@company.com", "body": "Digest attached..."}
    }

    result = orchestrator.process_escalation(
        user_prompt=sample_prompt,
        tool_history=sample_history,
        pending_tool=sample_pending,
        tier1_score=0.0052,
        tier1_threshold=0.006025
    )

    print(f"Action Allowed: {result.allowed}")
    print(f"Decision:       {result.decision}")
    print(f"Reason:         {result.reason}")