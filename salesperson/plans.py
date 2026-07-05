from __future__ import annotations

from salesperson.errors import PlanError

VALID_PLANS = ("free", "basic", "custom", "advanced")

PLAN_LABELS = {
    "free": "Free",
    "basic": "Basic API",
    "custom": "Custom · Self-integrate",
    "advanced": "Advanced · We integrate",
}

# Features included per plan (cumulative tiers).
_PLAN_FEATURES: dict[str, frozenset[str]] = {
    "free": frozenset({"widget", "default_behavior", "deals", "admin"}),
    "basic": frozenset({"widget", "default_behavior", "deals", "admin", "public_chat", "usage_api"}),
    "custom": frozenset(
        {
            "widget",
            "default_behavior",
            "deals",
            "admin",
            "public_chat",
            "usage_api",
            "custom_behavior",
            "byok",
        }
    ),
    "advanced": frozenset(
        {
            "widget",
            "default_behavior",
            "deals",
            "admin",
            "public_chat",
            "usage_api",
            "custom_behavior",
            "byok",
            "advanced_api",
        }
    ),
}


def normalize_plan(plan: str) -> str:
    normalized = plan.strip().lower()
    if normalized not in VALID_PLANS:
        choices = ", ".join(VALID_PLANS)
        raise ValueError(f"Invalid plan '{plan}'. Must be one of: {choices}.")
    return normalized


def plan_features(plan: str) -> frozenset[str]:
    return _PLAN_FEATURES[normalize_plan(plan)]


def has_feature(plan: str, feature: str) -> bool:
    return feature in plan_features(plan)


def require_feature(plan: str, feature: str) -> None:
    if not has_feature(plan, feature):
        label = PLAN_LABELS.get(normalize_plan(plan), plan)
        raise PlanError(
            f"Your {label} plan does not include this feature. "
            "Upgrade at https://yanchao1999.github.io/salesperson/#plans"
        )


def allows_chat_channel(plan: str, channel: str) -> bool:
    if channel == "website-widget":
        return has_feature(plan, "widget")
    return has_feature(plan, "public_chat")
