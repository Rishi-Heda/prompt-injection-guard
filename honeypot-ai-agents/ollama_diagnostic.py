import os
from pprint import pprint

from dotenv import load_dotenv
import ollama

from agent.tools import TOOL_SCHEMAS


load_dotenv()
MODEL = os.getenv("MODEL_NAME", "qwen3:4b")
THINK = os.getenv("OLLAMA_THINK", "true").lower() in {"1", "true", "yes", "on"}


def show_response(label: str, response: object) -> None:
    print(f"\n=== {label} ===")
    print(f"type: {type(response)!r}")
    print(f"repr: {response!r}")
    if isinstance(response, dict):
        print("dict keys:", list(response.keys()))
        pprint(response)
    else:
        print("attributes:", getattr(response, "__dict__", "<no __dict__>"))


def main() -> None:
    print("=== CONFIGURATION ===")
    print(f"model={MODEL!r}")
    print(f"think={THINK!r}")
    print("=== OLLAMA MODEL LIST ===")
    try:
        models = ollama.list()
        show_response("ollama.list()", models)
    except Exception as error:
        print(f"ollama.list() error: {type(error).__name__}: {error}")

    plain_kwargs = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Say hello and explain what 2+2 is."}],
        "think": THINK,
    }
    print("\n=== EXACT PLAIN ollama.chat KWARGS ===")
    pprint(plain_kwargs)
    try:
        show_response("PLAIN RAW RESPONSE", ollama.chat(**plain_kwargs))
    except Exception as error:
        print(f"plain ollama.chat() error: {type(error).__name__}: {error}")

    tool_kwargs = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Read the clean-doc document using READ_FILE."}],
        "tools": TOOL_SCHEMAS,
        "think": THINK,
    }
    print("\n=== EXACT TOOL ollama.chat KWARGS ===")
    pprint(tool_kwargs)
    try:
        show_response("TOOL RAW RESPONSE", ollama.chat(**tool_kwargs))
    except Exception as error:
        print(f"tool ollama.chat() error: {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
