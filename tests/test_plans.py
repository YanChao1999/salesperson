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

    def test_plan_upgrade_and_downgrade_cycle(self):
        app = create_app(SalespersonPlatform(agent_base_url="http://127.0.0.1:8000"))
        _, website, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Cycle Shop",
                "domain": "cycle.example.com",
                "plan": "basic",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )
        api_key = website["api_key"]
        website_id = website["website_id"]

        status, updated, _ = request(
            app,
            "PUT",
            f"/websites/{website_id}/plan",
            {"plan": "custom"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["plan"], "custom")

        status, updated, _ = request(
            app,
            "PUT",
            f"/websites/{website_id}/plan",
            {"plan": "advanced"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["plan"], "advanced")

        status, updated, _ = request(
            app,
            "PUT",
            f"/websites/{website_id}/plan",
            {"plan": "free"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["plan"], "free")

        status, error, _ = request(app, "GET", "/v1/usage", api_key=api_key)
        self.assertEqual(status, 403)

        status, dashboard, _ = request(app, "GET", "/v1/dashboard", api_key=api_key)
        self.assertEqual(status, 200)
        self.assertEqual(dashboard["plan"], "free")
        self.assertFalse(dashboard["metrics"]["available"])

        status, _, _ = request(
            app,
            "PUT",
            f"/websites/{website_id}/plan",
            {"plan": "basic"},
        )
        self.assertEqual(status, 200)

        status, usage, _ = request(app, "GET", "/v1/usage", api_key=api_key)
        self.assertEqual(status, 200)

        status, dashboard, _ = request(app, "GET", "/v1/dashboard", api_key=api_key)
        self.assertEqual(dashboard["plan"], "basic")
        self.assertEqual(dashboard["metrics"]["usage_events"], 0)

    def test_set_plan_rejects_invalid_plan(self):
        app = create_app(SalespersonPlatform(agent_base_url="http://127.0.0.1:8000"))
        _, website, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Invalid Plan Shop",
                "domain": "invalid-plan.example.com",
                "plan": "basic",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )

        status, error, _ = request(
            app,
            "PUT",
            f"/websites/{website['website_id']}/plan",
            {"plan": "enterprise"},
        )
        self.assertEqual(status, 400)
        self.assertIn("Invalid plan", error["error"])


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

    def test_dashboard_includes_deals_on_basic_plan(self):
        platform = SalespersonPlatform(agent_base_url="http://127.0.0.1:8000")
        app = create_app(platform)
        _, website, _ = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Dash Deals",
                "domain": "dash-deals.example.com",
                "plan": "basic",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )
        website_id = website["website_id"]
        api_key = website["api_key"]

        user = platform.create_user(website_id, external_user_id="buyer-1")
        platform.trace_deal(
            website_id,
            user_id=user["user_id"],
            stage="won",
            value=149.99,
            note="Test deal",
        )

        status, dashboard, _ = request(app, "GET", "/v1/dashboard", api_key=api_key)
        self.assertEqual(status, 200)
        self.assertEqual(dashboard["metrics"]["deals"], 1)
        self.assertEqual(dashboard["metrics"]["deal_value"], 149.99)
        self.assertEqual(len(dashboard["recent_deals"]), 1)


if __name__ == "__main__":
    unittest.main()
