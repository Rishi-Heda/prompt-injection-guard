import copy
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from tier0_canary.leak_detector import LeakDetectionResult


@dataclass
class IncidentReport:
    """Complete, immutable forensic record of a canary leak."""
    timestamp_unix: float   # for sorting / comparison
    timestamp_iso: str      # ISO 8601 UTC — for dashboard display
    session_id: str
    blocked_tool: str
    blocked_args: dict      # deep copy — immutable after creation
    leaked_canaries: list[str]
    compromised_sources: list[str]
    tier: str = "tier_0_canary"
    action_taken: str = "session_terminated"
    severity: str = "critical"


class KillSwitch:
    def __init__(self, session_id: str):
        """
        Raises:
            ValueError: If session_id is empty or not a string.
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError(
                f"session_id must be a non-empty string, got {session_id!r}. "
                f"Every session needs a unique ID for forensic traceability."
            )
        self.session_id = session_id
        self._triggered = False
        self._incident_report: IncidentReport | None = None

    def trigger(
        self,
        leak_result: LeakDetectionResult,
        tool_name: str,
        tool_args: dict,
    ) -> IncidentReport:
        """
        Execute the kill switch. Idempotent — safe to call multiple times.

        If called again after the first trigger, returns the ORIGINAL
        incident report unchanged. First report always wins.

        Raises:
            TypeError: If tool_args is not a dict.
        """
        if self._triggered:
            return self._incident_report   # idempotent — first report preserved

        if not isinstance(tool_args, dict):
            raise TypeError(
                f"tool_args must be a dict, got {type(tool_args).__name__!r}"
            )

        self._triggered = True
        now = time.time()
        iso = (
            datetime.fromtimestamp(now, tz=timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
        )

        self._incident_report = IncidentReport(
            timestamp_unix=now,
            timestamp_iso=iso,
            session_id=self.session_id,
            blocked_tool=tool_name,
            blocked_args=copy.deepcopy(tool_args),  # deep copy — forensic integrity
            leaked_canaries=list(leak_result.leaked_tokens),
            compromised_sources=list(leak_result.leaked_sources),
        )
        return self._incident_report

    def is_session_dead(self) -> bool:
        """True if this session has been terminated."""
        return self._triggered

    def to_dashboard_event(self) -> dict | None:
        """
        Format the incident for WebSocket broadcast.
        Returns None if the kill switch has not been triggered yet.
        """
        if not self._incident_report:
            return None
        r = self._incident_report
        return {
            "event_type": "canary_leak_detected",
            "tier": r.tier,
            "severity": r.severity,
            "timestamp_unix": r.timestamp_unix,
            "timestamp_iso": r.timestamp_iso,
            "session_id": r.session_id,
            "blocked_tool": r.blocked_tool,
            "compromised_sources": r.compromised_sources,
            "leaked_canary_count": len(r.leaked_canaries),
            "action_taken": r.action_taken,
            "message": (
                f"CRITICAL: Canary token leaked via {r.blocked_tool}. "
                f"Compromised context areas: {', '.join(r.compromised_sources)}. "
                f"Session terminated immediately."
            ),
        }