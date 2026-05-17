import requests
import json
from utils.logger import get_logger

class WebhookSender:
    """
    Phase 6 Automated Delivery Engine.
    Dispatches real-time mission outcome signals to client endpoints [Source 483].
    Enables integration with Slack, Discord, or custom enterprise middleware [Source 673].
    """
    def __init__(self):
        self.logger = get_logger("Webhook_Sender")

    def dispatch_event(self, endpoint_url: str, payload: dict):
        """
        Sends a POST request to a client-specified webhook URL [Source 483].
        """
        if not endpoint_url:
            return {"status": "skipped", "reason": "No endpoint provided"}

        try:
            self.logger.info(f"Dispatching mission signal to: {endpoint_url}")
            response = requests.post(
                endpoint_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            return {"status": "dispatched", "code": response.status_code}
        except Exception as e:
            self.logger.error(f"Webhook Dispatch FAILED: {str(e)}")
            return {"status": "failed", "error": str(e)}
