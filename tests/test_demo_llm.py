from __future__ import annotations

import unittest
from unittest.mock import patch

from salesperson import SalespersonPlatform, create_app
from salesperson.providers.factory import create_provider
from tests.test_platform import request


class DemoLLMProviderTests(unittest.TestCase):
    def test_create_provider_defaults_to_demo(self):
        provider = create_provider()
        self.assertEqual(provider.__class__.__name__, "StubLLMProvider")

    def test_create_provider_accepts_demo_and_stub_aliases(self):
        self.assertIsNotNone(create_provider("demo"))
        self.assertIsNotNone(create_provider("stub"))

    def test_create_provider_rejects_unimplemented_providers(self):
        with self.assertRaisesRegex(ValueError, "Unsupported LLM provider"):
            create_provider("openai")


class AdminAuthTests(unittest.TestCase):
    def test_admin_routes_open_when_token_unset(self):
        app = create_app(SalespersonPlatform(agent_base_url="http://127.0.0.1:8000"))
        status, website, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Open Admin",
                "domain": "open.example.com",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )
        self.assertEqual(status, 201)
        self.assertTrue(website["api_key"].startswith("sk_live_"))

    @patch("salesperson.server.ADMIN_TOKEN", "admin-secret")
    def test_admin_routes_require_admin_token_when_configured(self):
        app = create_app(SalespersonPlatform(agent_base_url="http://127.0.0.1:8000"))
        status, error, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Locked Admin",
                "domain": "locked.example.com",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )
        self.assertEqual(status, 401)
        self.assertIn("Admin authorization", error["error"])

        status, website, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Locked Admin",
                "domain": "locked.example.com",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
            api_key="admin-secret",
        )
        self.assertEqual(status, 201)
        self.assertTrue(website["api_key"].startswith("sk_live_"))


class WidgetUserTrackingTests(unittest.TestCase):
    def test_chat_auto_registers_widget_user_for_tracking(self):
        platform = SalespersonPlatform(agent_base_url="http://127.0.0.1:8000")
        app = create_app(platform)
        _, website, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Visitor Store",
                "domain": "visitor.example.com",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )

        status, _, _ = request(
            app,
            "POST",
            "/v1/chat/completions",
            {
                "messages": [{"role": "user", "content": "Hello"}],
                "user_id": "visitor-abc123",
            },
            api_key=website["api_key"],
        )
        self.assertEqual(status, 200)

        status, usage, _ = request(app, "GET", "/v1/usage", api_key=website["api_key"])
        self.assertEqual(status, 200)
        self.assertEqual(usage["tracked_users"], 1)


if __name__ == "__main__":
    unittest.main()
