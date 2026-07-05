from __future__ import annotations

import tempfile
import unittest

from salesperson import SalespersonPlatform
from salesperson.models import LLMConfig, SalesBehavior, Website, WebsiteUser
from salesperson.storage.sqlite import SqliteRepository


class SqliteRepositoryTests(unittest.TestCase):
    def test_platform_persists_website_and_usage_in_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = f"{tmp}/test.db"
            platform = SalespersonPlatform(
                agent_base_url="http://127.0.0.1:8000",
                repository=SqliteRepository(db_path),
            )

            website = platform.create_website(
                name="Persist Store",
                domain="persist.example.com",
                llm_provider="openai",
                llm_model="gpt-4.1",
            )
            user = platform.create_user(website["website_id"])
            platform.set_behavior(
                website["website_id"],
                system_prompt="Recommend bundles.",
                tone="friendly",
            )
            platform.record_usage(
                website["website_id"],
                user_id=user["user_id"],
                channel="website-widget",
                messages=2,
                tokens=40,
            )

            reloaded = SalespersonPlatform(
                agent_base_url="http://127.0.0.1:8000",
                repository=SqliteRepository(db_path),
            )
            summary = reloaded.get_summary(website["website_id"])

            self.assertEqual(summary["tracked_users"], 1)
            self.assertEqual(summary["usage_events"], 1)
            self.assertEqual(summary["tokens"], 40)
            self.assertEqual(summary["latest_behavior"]["tone"], "friendly")

    def test_same_visitor_id_is_allowed_for_different_websites(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = f"{tmp}/test.db"
            repository = SqliteRepository(db_path)
            visitor_id = "visitor-shared123"

            for website_id, domain in (("shop-a", "a.example.com"), ("shop-b", "b.example.com")):
                repository.save_website(
                    Website(
                        website_id=website_id,
                        name=website_id,
                        domain=domain,
                        llm=LLMConfig(provider="openai", model="gpt-4.1"),
                        plugin={},
                        behavior=SalesBehavior(system_prompt="Help shoppers."),
                    )
                )
                repository.save_user(
                    WebsiteUser(
                        user_id=visitor_id,
                        website_id=website_id,
                        external_user_id=visitor_id,
                        metadata={"source": "widget"},
                    )
                )

            self.assertEqual(repository.get_user("shop-a", visitor_id).website_id, "shop-a")
            self.assertEqual(repository.get_user("shop-b", visitor_id).website_id, "shop-b")


if __name__ == "__main__":
    unittest.main()
