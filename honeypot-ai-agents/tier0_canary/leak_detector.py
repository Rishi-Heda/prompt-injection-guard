from dataclasses import dataclass


@dataclass
class LeakDetectionResult:
    """Result of scanning a tool call payload for canary leaks."""
    leaked: bool
    leaked_tokens: list[str]
    leaked_sources: list[str]
    severity: str           
    scanned_tool: str = ""  


class LeakDetector:
    """Scans tool call payloads for planted canary tokens."""

    def __init__(self, canaries: set[str], source_map: dict[str, str]):
        """
        Raises:
            TypeError:  If canaries is not a set or source_map not a dict.
            ValueError: If canaries is empty — nothing to detect.
        """
        if not isinstance(canaries, set):
            raise TypeError(f"canaries must be a set, got {type(canaries).__name__}")
        if not canaries:
            raise ValueError(
                "canaries set is empty. Did you forget to call CanaryPlanter first?"
            )
        if not isinstance(source_map, dict):
            raise TypeError(f"source_map must be a dict, got {type(source_map).__name__}")
        self.canaries = canaries
        self.source_map = source_map

    def scan(self, payload: str, tool_name: str = "") -> LeakDetectionResult:
        """
        Scan a string payload for canary tokens.

        Raises:
            TypeError: If payload is not a str. A None payload from
                       the interceptor is a bug — fail loudly, not silently.
        """
        if not isinstance(payload, str):
            raise TypeError(
                f"payload must be a str, got {type(payload).__name__!r}. "
                f"Ensure the interceptor extracts string content before scanning."
            )

        found_tokens: list[str] = []
        found_sources: list[str] = []

        for canary in self.canaries:
            if canary in payload:
                found_tokens.append(canary)
                found_sources.append(self.source_map.get(canary, "unknown"))

        if found_tokens:
            return LeakDetectionResult(
                leaked=True,
                leaked_tokens=found_tokens,
                leaked_sources=found_sources,
                severity="critical",
                scanned_tool=tool_name,
            )
        return LeakDetectionResult(
            leaked=False,
            leaked_tokens=[],
            leaked_sources=[],
            severity="none",
            scanned_tool=tool_name,
        )

    def scan_all_tool_args(
        self, tool_name: str, tool_args: dict
    ) -> LeakDetectionResult:
        """
        Scan ALL string values in a tool call's argument dict.

        Raises:
            ValueError: If tool_name is empty.
            TypeError:  If tool_args is not a dict (None crashes silently
                        in the old version — now fails loudly).
        """
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise ValueError(f"tool_name must be non-empty, got {tool_name!r}")
        if not isinstance(tool_args, dict):
            raise TypeError(
                f"tool_args must be a dict, got {type(tool_args).__name__!r}. "
                f"Interceptor must always pass the full args dict."
            )

        all_text_parts: list[str] = []
        self._extract_strings(tool_args, all_text_parts)

       
        combined = "|FIELD|".join(all_text_parts)
        return self.scan(combined, tool_name=tool_name)

    def _extract_strings(self, obj, accumulator: list[str]) -> None:
        """Recursively extract all string values from a nested structure."""
        if isinstance(obj, str):
            accumulator.append(obj)
        elif isinstance(obj, dict):
            for value in obj.values():
                self._extract_strings(value, accumulator)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                self._extract_strings(item, accumulator)