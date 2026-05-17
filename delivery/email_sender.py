import os
import resend # Ensure 'resend' is in your requirements.txt

class EmailSender:
    """
    Phase 6 Automated Delivery.
    Dispatches mission bundles and audit receipts via Resend [Source 402, 483].
    """
    def __init__(self):
        # Uses the live API key integrated during .env hardening
        resend.api_key = os.getenv("RESEND_API_KEY")

    def send_mission_report(self, to_email: str, client_id: str, status: str, report_summary: str):
        """
        Delivers the final multi-agent mission outcome bundle [Source 483].
        """
        try:
            params = {
                "from": "Universal Headquarters <reports@yourdomain.com>",
                "to": [to_email],
                "subject": f"Mission Update: {client_id} - [{status}]",
                "html": f"<h3>Mission Result: {status}</h3><p>{report_summary}</p>"
            }
            resend.Emails.send(params)
            return {"delivery_status": "dispatched", "recipient": to_email}
        except Exception as e:
            return {"delivery_status": "failed", "error": str(e)}