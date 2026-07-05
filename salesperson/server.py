from __future__ import annotations

from io import BytesIO
import json
from typing import Any
from wsgiref.simple_server import make_server

from .backend import PlatformNotFoundError, SalespersonPlatform


def _json_response(start_response: Any, status: str, payload: dict[str, Any]) -> list[bytes]:
    data = json.dumps(payload).encode("utf-8")
    headers = [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(data))),
    ]
    start_response(status, headers)
    return [data]


def _read_json(environ: dict[str, Any]) -> dict[str, Any]:
    length = int(environ.get("CONTENT_LENGTH") or 0)
    if length == 0:
        return {}
    raw_body = environ.get("wsgi.input", BytesIO()).read(length)
    if not raw_body:
        return {}
    return json.loads(raw_body.decode("utf-8"))


def create_app(platform: SalespersonPlatform | None = None):
    platform = platform or SalespersonPlatform()

    def app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        try:
            body = _read_json(environ)
            if method == "GET" and path == "/health":
                return _json_response(start_response, "200 OK", {"status": "ok"})

            if method == "POST" and path == "/websites":
                website = platform.create_website(
                    name=body["name"],
                    domain=body["domain"],
                    llm_provider=body["llm"]["provider"],
                    llm_model=body["llm"]["model"],
                    llm_api_base=body["llm"].get("api_base"),
                )
                return _json_response(start_response, "201 Created", website)

            parts = [part for part in path.split("/") if part]
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
        except PlatformNotFoundError:
            return _json_response(
                start_response,
                "404 Not Found",
                {"error": "Requested website or user was not found."},
            )
        except json.JSONDecodeError:
            return _json_response(
                start_response,
                "400 Bad Request",
                {"error": "Request body must be valid JSON."},
            )
        except KeyError:
            return _json_response(
                start_response,
                "400 Bad Request",
                {"error": "Request body is missing one or more required fields."},
            )
        except (TypeError, ValueError):
            return _json_response(
                start_response,
                "400 Bad Request",
                {"error": "Request body contains invalid values."},
            )

    return app


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    with make_server(host, port, create_app()) as httpd:
        print(f"Salesperson backend listening on http://{host}:{port}")
        httpd.serve_forever()
