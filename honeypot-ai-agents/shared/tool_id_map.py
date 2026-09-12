# Tool name → integer ID mapping
TOOL_ID_MAP: dict[str, int] = {
    "read_file": 1,
    "summarize": 2,
    "query_db": 3,
    "send_email": 4,
    "search_web": 5,
    "calculate_math": 6,
    "write_file": 7,
}

# Reverse mapping for display (dashboard, logs)
ID_TOOL_MAP: dict[int, str] = {v: k for k, v in TOOL_ID_MAP.items()}

# Risk classification for each tool
# The interceptor uses this to decide whether to escalate to Tier 2
# "low" tools pass through quickly
# "high" tools ALWAYS trigger the LLM judge regardless of anomaly score
TOOL_RISK_LEVEL: dict[str, str] = {
    "read_file": "low",
    "summarize": "low",
    "query_db": "medium",
    "send_email": "high",
    "search_web": "low",
    "calculate_math": "low",
    "write_file": "medium",
}

# Maximum sequence length all sequences are padded to this length
MAX_SEQ_LEN = 12

# Padding value represents "no action taken" in a sequence slot
PAD_TOKEN = 0
NUM_TOOLS = len(TOOL_ID_MAP)