from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from typing import Any
from wsgiref.simple_server import make_server

from .backend import SalespersonPlatform
from .config import ADMIN_TOKEN, AGENT_BASE_URL, HOST, LLM_PROVIDER, PORT
from .errors import AuthError, PlatformNotFoundError
from .gateway.service import ChatGateway
from .models import ChatCompletionRequest

_STATIC_DIR = Path(__file__).resolve().parent / "static"

_CORS_PUBLIC_PATHS = {"/widget.js", "/v1/chat/completions", "/v1/usage"}


def _normalize_path(path: str) -> str:
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")
    return path


def _cors_enabled(path: str) -> bool:
    return path in _CORS_PUBLIC_PATHS


def _cors_headers(environ: dict[str, Any]) -> list[tuple[str, str]]:
    if not environ.get("HTTP_ORIGIN"):
        return []
    return [
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
        ("Access-Control-Allow-Headers", "Authorization, Content-Type"),
    ]


def _json_response(
    start_response: Any,
    status: str,
    payload: dict[str, Any],
    *,
    environ: dict[str, Any] | None = None,
    path: str = "",
) -> list[bytes]:
    data = json.dumps(payload).encode("utf-8")
    headers = [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(data))),
    ]
    if environ is not None and _cors_enabled(path):
        headers.extend(_cors_headers(environ))
    start_response(status, headers)
    return [data]


def _text_response(
    start_response: Any,
    status: str,
    body: bytes,
    content_type: str,
    *,
    environ: dict[str, Any] | None = None,
    path: str = "",
) -> list[bytes]:
    headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(body))),
    ]
    if environ is not None and _cors_enabled(path):
        headers.extend(_cors_headers(environ))
    start_response(status, headers)
    return [body]


def _read_json(environ: dict[str, Any]) -> dict[str, Any]:
    length = int(environ.get("CONTENT_LENGTH") or 0)
    if length == 0:
        return {}
    raw_body = environ.get("wsgi.input", BytesIO()).read(length)
    if not raw_body:
        return {}
    return json.loads(raw_body.decode("utf-8"))


def _bearer_token(environ: dict[str, Any]) -> str | None:
    header = environ.get("HTTP_AUTHORIZATION", "")
    if not header.startswith("Bearer "):
        return None
    return header[7:].strip() or None


def _is_admin_route(method: str, path: str, parts: list[str]) -> bool:
    if path == "/websites" and method == "POST":
        return True
    return bool(parts and parts[0] == "websites" and len(parts) >= 2)


def _require_admin(environ: dict[str, Any], start_response: Any) -> list[bytes] | None:
    if not ADMIN_TOKEN:
        return None
    token = _bearer_token(environ)
    if token == ADMIN_TOKEN:
        return None
    return _json_response(
        start_response,
        "401 Unauthorized",
        {"error": "Admin authorization required."},
    )


def create_app(platform: SalespersonPlatform | None = None):
    platform = platform or SalespersonPlatform(agent_base_url=AGENT_BASE_URL)
    gateway: ChatGateway = platform.gateway

    def app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = _normalize_path(environ.get("PATH_INFO", "/"))
        try:
            if method == "OPTIONS" and _cors_enabled(path):
                headers = _cors_headers(environ) + [("Content-Length", "0")]
                start_response("204 No Content", headers)
                return []

            body = _read_json(environ)

            if method == "GET" and path == "/":
                return _json_response(
                    start_response,
                    "200 OK",
                    {
                        "service": "salesperson-platform",
                        "llm_provider": LLM_PROVIDER,
                        "routes": {
                            "health": "GET /health",
                            "widget": "GET /widget.js",
                            "chat": "POST /v1/chat/completions",
                            "usage": "GET /v1/usage",
                            "register": "POST /websites",
                        },
                    },
                )

            if method == "GET" and path == "/health":
                return _json_response(start_response, "200 OK", {"status": "ok"})

            if method == "GET" and path == "/widget.js":
                widget = (_STATIC_DIR / "widget.js").read_bytes()
                return _text_response(
                    start_response,
                    "200 OK",
                    widget,
                    "application/javascript",
                    environ=environ,
                    path=path,
                )

            if method == "POST" and path == "/v1/chat/completions":
                messages = gateway.parse_messages(body["messages"])
                response = gateway.forward_chat(
                    api_key=_bearer_token(environ),
                    request=ChatCompletionRequest(
                        messages=messages,
                        user_id=body.get("user_id"),
                        channel=body.get("channel", "website-widget"),
                    ),
                )
                return _json_response(
                    start_response,
                    "200 OK",
                    gateway.completion_to_dict(response),
                    environ=environ,
                    path=path,
                )

            if method == "GET" and path == "/v1/usage":
                summary = gateway.usage_summary(api_key=_bearer_token(environ))
                return _json_response(
                    start_response,
                    "200 OK",
                    summary,
                    environ=environ,
                    path=path,
                )

            if method == "POST" and path == "/websites":
                denied = _require_admin(environ, start_response)
                if denied:
                    return denied
                website = platform.create_website(
                    name=body["name"],
                    domain=body["domain"],
                    llm_provider=body["llm"]["provider"],
                    llm_model=body["llm"]["model"],
                    llm_api_base=body["llm"].get("api_base"),
                )
                return _json_response(start_response, "201 Created", website)

            parts = [part for part in path.split("/") if part]
            if _is_admin_route(method, path, parts):
                denied = _require_admin(environ, start_response)
                if denied:
                    return denied

            if len(parts) == 3 and parts[0] == "websites" and parts[2] == "users" and method == "POST":
                user = platform.create_user(
                    parts[1],
                    external_user_id=body.get("external_user_id"),
                    metadata=body.get("metadata"),
                )
                return _json_response(start_response, "201 Created", user)

            if len(parts) == 3 and parts[0] == "websites" and parts[2] == "behavior" and method == "PUT":
                behavior = platform.set_behavior(
                    parts[1],
                    system_prompt=body["system_prompt"],
                    tone=body.get("tone", "consultative"),
                    sales_goals=body.get("sales_goals"),
                )
                return _json_response(start_response, "200 OK", behavior)

            if len(parts) == 3 and parts[0] == "websites" and parts[2] == "usage" and method == "POST":
                usage = platform.record_usage(
                    parts[1],
                    user_id=body["user_id"],
                    channel=body.get("channel", "website-widget"),
                    messages=int(body.get("messages", 0)),
                    tokens=int(body.get("tokens", 0)),
                    outcome=body.get("outcome"),
                )
                return _json_response(start_response, "201 Created", usage)

            if len(parts) == 3 and parts[0] == "websites" and parts[2] == "deals" and method == "POST":
                deal = platform.trace_deal(
                    parts[1],
                    user_id=body["user_id"],
                    stage=body["stage"],
                    value=float(body["value"]),
                    currency=body.get("currency", "USD"),
                    note=body.get("note", ""),
                )
                return _json_response(start_response, "201 Created", deal)

            if len(parts) == 3 and parts[0] == "websites" and parts[2] == "summary" and method == "GET":
                summary = platform.get_summary(parts[1])
                return _json_response(start_response, "200 OK", summary)

            return _json_response(start_response, "404 Not Found", {"error": "Route not found."})
        except AuthError as exc:
            return _json_response(
                start_response,
                "401 Unauthorized",
                {"error": str(exc)},
                environ=environ,
                path=path,
            )
        except PlatformNotFoundError:
            return _json_response(
                start_response,
                "404 Not Found",
                {"error": "Requested website or user was not found."},
                environ=environ,
                path=path,
            )
        except json.JSONDecodeError:
            return _json_response(
                start_response,
                "400 Bad Request",
                {"error": "Request body must be valid JSON."},
                environ=environ,
                path=path,
            )
        except KeyError:
            return _json_response(
                start_response,
                "400 Bad Request",
                {"error": "Request body is missing one or more required fields."},
                environ=environ,
                path=path,
            )
        except (TypeError, ValueError) as exc:
            message = str(exc) if str(exc) else "Request body contains invalid values."
            return _json_response(
                start_response,
                "400 Bad Request",
                {"error": message},
                environ=environ,
                path=path,
            )
        except Exception:
            return _json_response(
                start_response,
                "500 Internal Server Error",
                {"error": "Internal server error."},
                environ=environ,
                path=path,
            )

    return app


def run_server(host: str | None = None, port: int | None = None) -> None:
    bind_host = host or HOST
    bind_port = port or PORT
    with make_server(bind_host, bind_port, create_app()) as httpd:
        print(f"Salesperson platform listening on http://{bind_host}:{bind_port}")
        httpd.serve_forever()
