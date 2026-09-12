"""
When a canary leaks, we TERMINATE THE ENTIRE SESSION because:
- The agent's reasoning is hijacked
- Blocking one call still leaves a poisoned agent running
- It might retry with different parameters or methods
- Only safe response = kill everything
"""

import time
from dataclasses import dataclass
from tier0_canary.leak_detector import LeakDetectionResult


@dataclass
class IncidentReport:
    """Complete forensic record of a canary leak incident."""
    timestamp: float
    session_id: str
    blocked_tool: str
    blocked_args: dict
    leaked_canaries: list[str]
    compromised_sources: list[str]
    tier: str = "tier_0_canary"
    action_taken: str = "session_terminated"
    severity: str = "critical"


class KillSwitch:
    """
    One-way session termination switch.
    Once triggered, CANNOT be un-triggered. Session is permanently dead.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.triggered = False
        self.incident_report = None

    def trigger(
        self,
        leak_result: LeakDetectionResult,
        tool_name: str,
        tool_args: dict,
    ) -> IncidentReport:
        """Execute the kill switch. Irreversible."""
        self.triggered = True

        report = IncidentReport(
            timestamp=time.time(),
            session_id=self.session_id,
            blocked_tool=tool_name,
            blocked_args=tool_args,
            leaked_canaries=leak_result.leaked_tokens,
            compromised_sources=leak_result.leaked_sources,
        )

        self.incident_report = report
        return report

    def is_session_dead(self) -> bool:
        """Check if session has been terminated."""
        return self.triggered

    def to_dashboard_event(self) -> dict | None:
        """Format incident for WebSocket broadcast to dashboard."""
        if not self.incident_report:
            return None

        report = self.incident_report
        return {
            "event_type": "canary_leak_detected",
            "tier": report.tier,
            "severity": report.severity,
            "timestamp": report.timestamp,
            "session_id": report.session_id,
            "blocked_tool": report.blocked_tool,
            "compromised_sources": report.compromised_sources,
            "action_taken": report.action_taken,
            "message": (
                f"CRITICAL: Canary token leaked via {report.blocked_tool}. "
                f"Compromised context areas: {', '.join(report.compromised_sources)}. "
                f"Session terminated immediately."
            ),
        }