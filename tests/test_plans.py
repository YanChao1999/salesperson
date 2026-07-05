from __future__ import annotations

import unittest

from salesperson import SalespersonPlatform, create_app
from salesperson.plans import normalize_plan, require_feature
from salesperson.errors import PlanError
from tests.test_platform import request


class PlanEnforcementTests(unittest.TestCase):
    def test_create_website_defaults_to_free_plan(self):
        platform = SalespersonPlatform(agent_base_url="http://127.0.0.1:8000")
        website = platform.create_website(
            name="Free Shop",
            domain="free.example.com",
            llm_provider="openai",
            llm_model="gpt-4.1",
        )
        self.assertEqual(website["plan"], "free")

    def test_free_plan_allows_widget_chat_but_blocks_public_api_channel(self):
        app = create_app(SalespersonPlatform(agent_base_url="http://127.0.0.1:8000"))
        _, website, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Free Shop",
                "domain": "free.example.com",
                "plan": "free",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )
        api_key = website["api_key"]

        status, _, _ = request(
            app,
            "POST",
            "/v1/chat/completions",
            {
                "messages": [{"role": "user", "content": "Hello"}],
                "channel": "website-widget",
                "user_id": "visitor-test001",
            },
            api_key=api_key,
        )
        self.assertEqual(status, 200)

        status, error, _ = request(
            app,
            "POST",
            "/v1/chat/completions",
            {
                "messages": [{"role": "user", "content": "Hello"}],
                "channel": "api",
            },
            api_key=api_key,
        )
        self.assertEqual(status, 403)
        self.assertIn("Free plan", error["error"])

    def test_free_plan_blocks_usage_api(self):
        app = create_app(SalespersonPlatform(agent_base_url="http://127.0.0.1:8000"))
        _, website, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Free Metrics",
                "domain": "metrics-free.example.com",
                "plan": "free",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )

        status, error, _ = request(app, "GET", "/v1/usage", api_key=website["api_key"])
        self.assertEqual(status, 403)
        self.assertIn("Upgrade", error["error"])

    def test_basic_plan_allows_usage_api(self):
        app = create_app(SalespersonPlatform(agent_base_url="http://127.0.0.1:8000"))
        _, website, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Basic Metrics",
                "domain": "metrics-basic.example.com",
                "plan": "basic",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )

        status, usage, _ = request(app, "GET", "/v1/usage", api_key=website["api_key"])
        self.assertEqual(status, 200)
        self.assertEqual(usage["usage_events"], 0)

    def test_custom_behavior_requires_custom_plan(self):
        app = create_app(SalespersonPlatform(agent_base_url="http://127.0.0.1:8000"))
        _, website, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Basic Shop",
                "domain": "basic.example.com",
                "plan": "basic",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )

        status, error, _ = request(
            app,
            "PUT",
            f"/websites/{website['website_id']}/behavior",
            {"system_prompt": "Custom pitch", "tone": "friendly"},
        )
        self.assertEqual(status, 403)

        status, _, _ = request(
            app,
            "PUT",
            f"/websites/{website['website_id']}/plan",
            {"plan": "custom"},
        )
        self.assertEqual(status, 200)

        status, behavior, _ = request(
            app,
            "PUT",
            f"/websites/{website['website_id']}/behavior",
            {"system_prompt": "Custom pitch", "tone": "friendly"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(behavior["system_prompt"], "Custom pitch")

    def test_normalize_plan_rejects_unknown_values(self):
        with self.assertRaises(ValueError):
            normalize_plan("enterprise")

    def test_require_feature_raises_plan_error(self):
        with self.assertRaises(PlanError):
            require_feature("free", "usage_api")


class OwnerDashboardTests(unittest.TestCase):
    def test_dashboard_available_on_free_plan_without_metrics(self):
        app = create_app(SalespersonPlatform(agent_base_url="http://127.0.0.1:8000"))
        _, website, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Dash Free",
                "domain": "dash-free.example.com",
                "plan": "free",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )

        status, dashboard, _ = request(
            app, "GET", "/v1/dashboard", api_key=website["api_key"]
        )
        self.assertEqual(status, 200)
        self.assertEqual(dashboard["plan"], "free")
        self.assertFalse(dashboard["metrics"]["available"])

    def test_dashboard_includes_metrics_on_basic_plan(self):
        app = create_app(SalespersonPlatform(agent_base_url="http://127.0.0.1:8000"))
        _, website, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Dash Basic",
                "domain": "dash-basic.example.com",
                "plan": "basic",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )
        api_key = website["api_key"]

        request(
            app,
            "POST",
            "/v1/chat/completions",
            {
                "messages": [{"role": "user", "content": "Hi"}],
                "channel": "website-widget",
                "user_id": "visitor-dash001",
            },
            api_key=api_key,
        )

        status, dashboard, _ = request(app, "GET", "/v1/dashboard", api_key=api_key)
        self.assertEqual(status, 200)
        self.assertEqual(dashboard["plan"], "basic")
        self.assertEqual(dashboard["metrics"]["usage_events"], 1)
        self.assertEqual(len(dashboard["recent_usage"]), 1)


if __name__ == "__main__":
    unittest.main()
