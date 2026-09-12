import os
from typing import Any

from .groq_provider import GroqProvider


def create_provider(provider_name: str, client: Any = None) -> Any:
    if provider_name == "groq":
        return GroqProvider(client=client)
    if provider_name == "ollama":
        from .ollama_provider import OllamaProvider

        think = os.getenv("OLLAMA_THINK", "true").lower() in {"1", "true", "yes", "on"}
        return OllamaProvider(think=think)
    if provider_name == "openrouter":
        from .openrouter_provider import OpenRouterProvider

        return OpenRouterProvider(client=client)
    raise ValueError(f"Unsupported MODEL_PROVIDER: {provider_name!r}. Use 'groq', 'ollama', or 'openrouter'.")
