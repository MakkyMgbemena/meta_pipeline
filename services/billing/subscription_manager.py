class SubscriptionManager:
    """
    Phase 6 Billing & Gating.
    Enforces access limits based on subscription tiers [Source 483, 665].
    """
    TIERS = {
        "starter": {"mission_limit": 10, "social_access": False},
        "pro": {"mission_limit": 9999, "social_access": True}
    }

    def can_execute_mission(self, user_tier: str, mission_count: int) -> bool:
        """Determines if the user has remaining credits for the month [Source 483]."""
        tier_limits = self.TIERS.get(user_tier, self.TIERS["starter"])
        return mission_count < tier_limits["mission_limit"]