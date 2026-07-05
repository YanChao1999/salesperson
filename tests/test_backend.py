from __future__ import annotations

from io import BytesIO
import json
import unittest

from salesperson import SalespersonPlatform, create_app


def request(app, method: str, path: str, payload: dict | None = None):
    body = json.dumps(payload or {}).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    response = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split()[0]), json.loads(response.decode("utf-8"))


class SalespersonPlatformTests(unittest.TestCase):
    def test_platform_tracks_users_usage_and_deals_per_website(self):
        platform = SalespersonPlatform(agent_base_url="https://sales.example.com")

        website = platform.create_website(
            name="Demo Store",
            domain="demo.example.com",
            llm_provider="openai",
            llm_model="gpt-4.1",
        )
        user = platform.create_user(website["website_id"], external_user_id="customer-7")
        platform.set_behavior(
            website["website_id"],
            system_prompt="Recommend products using the shopper's budget.",
            tone="friendly",
            sales_goals=["capture-email", "cross-sell"],
        )
        platform.record_usage(
            website["website_id"],
            user_id=user["user_id"],
            channel="website-widget",
            messages=4,
            tokens=220,
            outcome="quote-requested",
        )
        platform.trace_deal(
            website["website_id"],
            user_id=user["user_id"],
            stage="won",
            value=149.99,
            note="Closed after bundled offer.",
        )

        summary = platform.get_summary(website["website_id"])

        self.assertEqual(summary["tracked_users"], 1)
        self.assertEqual(summary["usage_events"], 1)
        self.assertEqual(summary["messages"], 4)
        self.assertEqual(summary["tokens"], 220)
        self.assertEqual(summary["deals"], 1)
        self.assertEqual(summary["deal_value"], 149.99)
        self.assertEqual(summary["latest_behavior"]["tone"], "friendly")
        self.assertIn(website["website_id"], website["plugin"]["embed_code"])

    def test_wsgi_backend_supports_full_agent_setup_flow(self):
        app = create_app(SalespersonPlatform(agent_base_url="https://sales.example.com"))

        status, website = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Northwind",
                "domain": "northwind.example.com",
                "llm": {"provider": "anthropic", "model": "claude-sonnet-5"},
            },
        )
        self.assertEqual(status, 201)

        status, user = request(
            app,
            "POST",
            f"/websites/{website['website_id']}/users",
            {"external_user_id": "crm-42", "metadata": {"plan": "enterprise"}},
        )
        self.assertEqual(status, 201)
        self.assertEqual(user["user_id"], f"{website['website_id']}-user-1")

        status, behavior = request(
            app,
            "PUT",
            f"/websites/{website['website_id']}/behavior",
            {
                "system_prompt": "Upsell premium support when intent is high.",
                "tone": "expert",
                "sales_goals": ["upsell-support"],
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(behavior["sales_goals"], ["upsell-support"])

        status, usage = request(
            app,
            "POST",
            f"/websites/{website['website_id']}/usage",
            {
                "user_id": user["user_id"],
                "messages": 3,
                "tokens": 180,
                "outcome": "meeting-booked",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(usage["channel"], "website-widget")

        status, deal = request(
            app,
            "POST",
            f"/websites/{website['website_id']}/deals",
            {
                "user_id": user["user_id"],
                "stage": "qualified",
                "value": 5000,
                "currency": "USD",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(deal["stage"], "qualified")

        status, summary = request(app, "GET", f"/websites/{website['website_id']}/summary")
        self.assertEqual(status, 200)
        self.assertEqual(summary["tracked_users"], 1)
        self.assertEqual(summary["usage_events"], 1)
        self.assertEqual(summary["deals"], 1)
        self.assertEqual(summary["deal_value"], 5000.0)

    def test_wsgi_backend_rejects_unknown_user(self):
        app = create_app(SalespersonPlatform())
        _, website = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Fallback Store",
                "domain": "fallback.example.com",
                "llm": {"provider": "openai", "model": "gpt-4.1-mini"},
            },
        )

        status, error = request(
            app,
            "POST",
            f"/websites/{website['website_id']}/usage",
            {"user_id": "missing-user", "messages": 1, "tokens": 10},
        )

        self.assertEqual(status, 404)
        self.assertIn("Unknown user", error["error"])

    def test_wsgi_backend_rejects_invalid_usage_values(self):
        app = create_app(SalespersonPlatform())
        _, website = request(
            app,
            "POST",
            "/websites",
            {
                "name": "Validation Store",
                "domain": "validation.example.com",
                "llm": {"provider": "openai", "model": "gpt-4.1"},
            },
        )
        _, user = request(app, "POST", f"/websites/{website['website_id']}/users", {})

        status, error = request(
            app,
            "POST",
            f"/websites/{website['website_id']}/usage",
            {"user_id": user["user_id"], "messages": -1, "tokens": 10},
        )

        self.assertEqual(status, 400)
        self.assertIn("non-negative", error["error"])


if __name__ == "__main__":
    unittest.main()
