from __future__ import annotations

from io import BytesIO
import json
import unittest

from salesperson import SalespersonPlatform, create_app


def request(
    app,
    method: str,
    path: str,
    payload: dict | None = None,
    *,
    api_key: str | None = None,
):
    body = json.dumps(payload or {}).encode("utf-8")
    headers = {}
    if api_key:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {api_key}"
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
        **headers,
    }
    captured: dict[str, object] = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = response_headers

    response = b"".join(app(environ, start_response))
    status_code = int(str(captured["status"]).split()[0])
    if not response:
        return status_code, {}
    return status_code, json.loads(response.decode("utf-8"))


class PlatformGatewayTests(unittest.TestCase):
    def test_public_chat_forwards_and_meters_usage(self):
        platform = SalespersonPlatform(agent_base_url="http://127.0.0.1:8000")
        app = create_app(platform)

        _, website = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Gateway Store",
                "domain": "gateway.example.com",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )
        api_key = website["api_key"]

        status, completion = request(
            app,
            "POST",
            "/v1/chat/completions",
            {"messages": [{"role": "user", "content": "Need pricing for 5 seats"}]},
            api_key=api_key,
        )
        self.assertEqual(status, 200)
        self.assertEqual(completion["message"]["role"], "assistant")
        self.assertGreater(completion["usage"]["total_tokens"], 0)

        status, usage = request(app, "GET", "/v1/usage", api_key=api_key)
        self.assertEqual(status, 200)
        self.assertEqual(usage["usage_events"], 1)
        self.assertGreater(usage["tokens"], 0)

    def test_public_chat_rejects_missing_api_key(self):
        app = create_app(SalespersonPlatform())
        status, error = request(
            app,
            "POST",
            "/v1/chat/completions",
            {"messages": [{"role": "user", "content": "Hello"}]},
        )
        self.assertEqual(status, 401)
        self.assertIn("API key", error["error"])

    def test_widget_script_is_served(self):
        app = create_app(SalespersonPlatform())
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/widget.js",
            "CONTENT_LENGTH": "0",
            "wsgi.input": BytesIO(b""),
        }
        captured: dict[str, object] = {}

        def start_response(status, headers):
            captured["status"] = status

        body = b"".join(app(environ, start_response))
        self.assertEqual(int(str(captured["status"]).split()[0]), 200)
        self.assertIn(b"data-api-key", body)


if __name__ == "__main__":
    unittest.main()
