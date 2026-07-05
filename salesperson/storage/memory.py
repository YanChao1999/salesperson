from __future__ import annotations

from salesperson.errors import PlatformNotFoundError
from salesperson.models import DealRecord, SalesBehavior, UsageRecord, Website, WebsiteUser


class MemoryRepository:
    def __init__(self) -> None:
        self._websites: dict[str, Website] = {}
        self._users: dict[str, dict[str, WebsiteUser]] = {}
        self._usage: dict[str, list[UsageRecord]] = {}
        self._deals: dict[str, list[DealRecord]] = {}
        self._user_sequence: dict[str, int] = {}

    def save_website(self, website: Website) -> None:
        self._websites[website.website_id] = website
        self._users.setdefault(website.website_id, {})
        self._usage.setdefault(website.website_id, [])
        self._deals.setdefault(website.website_id, [])
        self._user_sequence.setdefault(website.website_id, 0)

    def get_website(self, website_id: str) -> Website:
        try:
            return self._websites[website_id]
        except KeyError as exc:
            raise PlatformNotFoundError(f"Unknown website '{website_id}'.") from exc

    def list_api_key_hashes(self) -> dict[str, str]:
        return {
            website_id: website.api_key_hash
            for website_id, website in self._websites.items()
            if website.api_key_hash
        }

    def save_user(self, user: WebsiteUser) -> None:
        self.get_website(user.website_id)
        self._users[user.website_id][user.user_id] = user

    def get_user(self, website_id: str, user_id: str) -> WebsiteUser:
        self.get_website(website_id)
        try:
            return self._users[website_id][user_id]
        except KeyError as exc:
            raise PlatformNotFoundError(
                f"Unknown user '{user_id}' for website '{website_id}'."
            ) from exc

    def next_user_number(self, website_id: str) -> int:
        self.get_website(website_id)
        next_number = self._user_sequence[website_id] + 1
        self._user_sequence[website_id] = next_number
        return next_number

    def update_behavior(self, website_id: str, behavior: SalesBehavior) -> SalesBehavior:
        website = self.get_website(website_id)
        website.behavior = behavior
        return behavior

    def append_usage(self, usage: UsageRecord) -> UsageRecord:
        self.get_website(usage.website_id)
        self._usage[usage.website_id].append(usage)
        return usage

    def append_deal(self, deal: DealRecord) -> DealRecord:
        self.get_website(deal.website_id)
        self._deals[deal.website_id].append(deal)
        return deal

    def list_usage(self, website_id: str) -> list[UsageRecord]:
        self.get_website(website_id)
        return list(self._usage[website_id])

    def list_deals(self, website_id: str) -> list[DealRecord]:
        self.get_website(website_id)
        return list(self._deals[website_id])

    def count_users(self, website_id: str) -> int:
        self.get_website(website_id)
        return len(self._users[website_id])

    def website_exists(self, website_id: str) -> bool:
        return website_id in self._websites

    def next_website_id(self, base: str) -> str:
        if not self.website_exists(base):
            return base
        suffix = 2
        while self.website_exists(f"{base}-{suffix}"):
            suffix += 1
        return f"{base}-{suffix}"
