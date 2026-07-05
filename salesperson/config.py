from __future__ import annotations

import os


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


HOST = _env("SALESPERSON_HOST", "127.0.0.1")
PORT = int(_env("SALESPERSON_PORT", "8000"))
AGENT_BASE_URL = _env("SALESPERSON_AGENT_BASE_URL", f"http://{HOST}:{PORT}").rstrip("/")
DB_PATH = _env("SALESPERSON_DB_PATH", "")
LLM_PROVIDER = _env("SALESPERSON_LLM_PROVIDER", "demo")
ADMIN_TOKEN = _env("SALESPERSON_ADMIN_TOKEN", "")
