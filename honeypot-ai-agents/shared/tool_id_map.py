# Tool name → integer ID mapping
TOOL_ID_MAP: dict[str, int] = {
    "read_file": 1,
    "summarize": 2,
    "query_db": 3,
    "send_email": 4,
}

# Reverse mapping for display (dashboard, logs)
# dict comprehension: flips keys and values
# {1: "read_file", 2: "summarize", ...}
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
}

# Maximum sequence length — all sequences are padded to this length
# Why 8? Our agent sessions are short (2-5 tool calls typically)
# 8 gives enough room for complex sessions while keeping tensors small
MAX_SEQ_LEN = 8

# Padding value — represents "no action taken" in a sequence slot
# [1, 2, 0, 0, 0, 0, 0, 0] means "read_file, summarize, then nothing"
PAD_TOKEN = 0