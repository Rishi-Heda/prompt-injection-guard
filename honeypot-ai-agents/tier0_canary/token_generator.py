import secrets

def generate_canary_token(prefix: str = "CANARY", length: int = 24) -> str:
    """
    Generate one cryptographically random canary token.

    token_hex(n) generates n random bytes as hex (2 chars per byte).
    token_hex(12) = 24 hex characters = 96 bits of randomness.
    """
    random_part = secrets.token_hex(length // 2)
    return f"{prefix}-{random_part}"


def generate_canary_set(count: int = 3) -> list[str]:
    return [generate_canary_token() for _ in range(count)]


def generate_fake_api_key() -> str:
    """
    Generate a realistic-looking but fake API key.

    Format: sk-proj-<random> (mimics OpenAI API key format)
    """
    random_part = secrets.token_urlsafe(32)
    return f"sk-proj-{random_part}"


if __name__ == "__main__":
    print("Generated canary tokens:")
    for token in generate_canary_set(3):
        print(f"  {token}")
    print(f"\nGenerated fake API key:")
    print(f"  {generate_fake_api_key()}")