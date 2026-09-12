from typing import Dict, Any
from pydantic import BaseModel
from llm_auditor import AuditResponse

class FinalVerdict(BaseModel):
    allowed: bool
    decision: str  # "ALLOW" or "BLOCK"
    tier1_score: float
    tier2_confidence: float
    reason: str

class VerdictAggregator:
    def __init__(self, block_confidence_threshold: float = 0.60):
        self.block_confidence_threshold = block_confidence_threshold

    def aggregate(
        self,
        tier1_score: float,
        tier1_threshold: float,
        audit_result: AuditResponse
    ) -> FinalVerdict:
        """
        Combines Tier 1 quantitative reconstruction error with Tier 2 qualitative audit.
        """
        # Rule 1: Hard block if Tier 2 flags an attack with sufficient confidence
        if audit_result.decision == "BLOCK" and audit_result.confidence >= self.block_confidence_threshold:
            return FinalVerdict(
                allowed=False,
                decision="BLOCK",
                tier1_score=tier1_score,
                tier2_confidence=audit_result.confidence,
                reason=f"[Tier 2 Rejection] {audit_result.violation_type}: {audit_result.rationale}"
            )

        # Rule 2: LLM approves the tool call
        if audit_result.decision == "ALLOW":
            return FinalVerdict(
                allowed=True,
                decision="ALLOW",
                tier1_score=tier1_score,
                tier2_confidence=audit_result.confidence,
                reason=f"[Tier 2 Approved] {audit_result.rationale}"
            )

        # Rule 3: Fail-closed fallback
        return FinalVerdict(
            allowed=False,
            decision="BLOCK",
            tier1_score=tier1_score,
            tier2_confidence=audit_result.confidence,
            reason=f"[Tier 2 Inconclusive] Low confidence audit fallback: {audit_result.rationale}"
        )