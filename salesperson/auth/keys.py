from __future__ import annotations

import hashlib
import secrets


def generate_api_key(*, prefix: str = "sk_live") -> str:
    return f"{prefix}_{secrets.token_urlsafe(24)}"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def resolve_website_id(api_key_hashes: dict[str, str], api_key: str) -> str | None:
    digest = hash_api_key(api_key)
    for website_id, stored in api_key_hashes.items():
        if secrets.compare_digest(stored, digest):
            return website_id
    return None
