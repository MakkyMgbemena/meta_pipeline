import os
import stripe
from fastapi import Request, HTTPException
from utils.logger import get_logger
from services.auth.user_store import UserStore
from core.agents.ledger import LedgerAgent

class StripeWebhookHandler:
    """
    Phase 6 Monetization Engine (Live).
    Automates subscription gating and financial ledger writes [Source 483, 672].
    """
    def __init__(self):
        self.logger = get_logger("Stripe_Webhook")
        stripe.api_key = os.getenv("STRIPE_API_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        self.user_store = UserStore()

    async def handle_event(self, request: Request):
        """Processes live payment signals from Stripe [Source 483, 673]."""
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except Exception as e:
            self.logger.error(f"Live Webhook Signature Failed: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid Signature")

        # Event: Successful Checkout [Source 662]
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            self._process_fulfillment(session)

        return {"status": "success"}

    def _process_fulfillment(self, session):
        """Triggers Dual-Write: User Registry + Financial Ledger [Source 478, 672]."""
        client_email = session.get("customer_details", {}).get("email")
        amount = session.get("amount_total") / 100 # Convert to CAD
        
        self.logger.info(f"Fulfillment Triggered: {client_email} | ${amount} CAD")
        
        # 1. Update User Tier to PRO in PostgreSQL
        self.user_store.create_user(client_email, tier="pro")
        
        # 2. Log Revenue in the Phase 3 Financial Ledger
        ledger = LedgerAgent(config={}, client_id=client_email)
        ledger.run({
            "revenue": amount,
            "cost": 0.00,
            "description": "Live SaaS Subscription - PRO Tier"
        })