"""Create an ignored local .env once, with a fresh secret; never overwrite existing config."""

import secrets
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    target = root / ".env"
    if target.exists():
        print(".env already exists; unchanged")
        return
    content = (root / ".env.example").read_text(encoding="utf-8")
    content = content.replace(
        "replace-with-a-random-secret-of-at-least-32-characters", secrets.token_urlsafe(48)
    )
    with target.open("x", encoding="utf-8") as output:
        output.write(content)
    print("Created .env with a generated JWT secret")


if __name__ == "__main__":
    main()
