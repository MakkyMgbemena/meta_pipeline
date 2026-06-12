from utils.json_store import JSONStore
import datetime

class UserStore:
    """
    Phase 6 Monetization Infrastructure.
    Persists user account records and tier status [Source 482].
    Anchors multi-tenant data isolation logic.
    """
    def __init__(self):
        # Initializing within the data/ folder for persistence
        self.store = JSONStore("data/user_registry.json")

    def create_user(self, email: str, tier: str = "starter"):
        """Registers a new paying client in the system [Source 665]."""
        user_entry = {
            "email": email,
            "tier": tier,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "status": "active"
        }
        self.store.append(user_entry)
        return user_entry
