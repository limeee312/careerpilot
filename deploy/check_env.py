"""Fail closed before a production Compose command; never print secret values."""

import argparse
import re
from pathlib import Path

REQUIRED = {
    "APP_DOMAIN", "BASIC_AUTH_USER", "BASIC_AUTH_HASH", "POSTGRES_DB",
    "POSTGRES_USER", "POSTGRES_PASSWORD", "JWT_SECRET", "OPENAI_API_KEY",
    "OPENAI_MODEL",
}
DOMAIN = re.compile(r"(?=.{4,253}$)[a-z0-9-]+(?:\.[a-z0-9-]+)+$")
IDENTIFIER = re.compile(r"[a-zA-Z][a-zA-Z0-9_]*$")
URL_SAFE_SECRET = re.compile(r"[a-zA-Z0-9_-]{32,}$")


def check_file(path: Path, *, template: bool = False) -> None:
    values: dict[str, str] = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"line {lineno}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key in values:
            raise ValueError(f"line {lineno}: duplicate {key}")
        if not IDENTIFIER.fullmatch(key):
            raise ValueError(f"line {lineno}: invalid key")
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        values[key] = value

    missing = REQUIRED - values.keys()
    if missing:
        raise ValueError(f"missing: {', '.join(sorted(missing))}")
    if template:
        return
    for key in REQUIRED:
        if not values[key] or "REPLACE" in values[key].upper():
            raise ValueError(f"{key}: replace placeholder or empty value")
    if not DOMAIN.fullmatch(values["APP_DOMAIN"]) or values["APP_DOMAIN"].endswith(".example.com"):
        raise ValueError("APP_DOMAIN: use a real DNS hostname (no scheme)")
    for key in ("POSTGRES_USER", "POSTGRES_DB", "BASIC_AUTH_USER"):
        if not IDENTIFIER.fullmatch(values[key]):
            raise ValueError(f"{key}: use letters, numbers and underscores")
    if not URL_SAFE_SECRET.fullmatch(values["POSTGRES_PASSWORD"]):
        raise ValueError("POSTGRES_PASSWORD: use at least 32 URL-safe characters")
    if len(values["JWT_SECRET"]) < 32 or values["JWT_SECRET"] == values["POSTGRES_PASSWORD"]:
        raise ValueError("JWT_SECRET: use a separate secret of at least 32 characters")
    if not values["BASIC_AUTH_HASH"].startswith(("$2a$", "$2b$", "$2y$", "$argon2id$")):
        raise ValueError("BASIC_AUTH_HASH: use a Caddy password hash")
    if any("\n" in value or "\r" in value for value in values.values()):
        raise ValueError("multiline values are not supported")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("env_file", type=Path)
    parser.add_argument("--template", action="store_true", help="check keys without real secrets")
    args = parser.parse_args()
    try:
        check_file(args.env_file, template=args.template)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Production environment invalid: {error}\n")
    print("Production environment checks passed (secret values hidden).")
