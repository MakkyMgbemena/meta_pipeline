import os
import resend # Ensure 'resend' is in your requirements.txt

class EmailSender:
    """
    Phase 6 Automated Delivery.
    Dispatches mission bundles and audit receipts via Resend.
    """
    def __init__(self):
        # Uses the live API key integrated during .env hardening
        resend.api_key = os.getenv("RESEND_API_KEY")

    def _convert_file_to_attachment(self, file_path: str, filename: str):
        """Helper to convert local files to Resend attachment format."""
        if not file_path or not os.path.exists(file_path):
            return None
        with open(file_path, "rb") as f:
            content = list(f.read())
        return {"filename": filename, "content": content}

    def send_mission_report(self, to_email: str, client_id: str, status: str, human_html_content: str, before_img_path: str = None, after_img_path: str = None):
        """
        Delivers the final multi-agent mission outcome bundle.
        """
        try:
            recipient_list = ["annastecias@gmail.com", "makky@travelbunny.services", to_email]
            params = {
                "from": "Universal Headquarters <reports@travelbunny.services>",
                "to": recipient_list,
                "subject": f"Mission Update: {client_id} - [{status}]",
                "html": human_html_content
            }

            attachments = []
            if before_img_path: attachments.append(self._convert_file_to_attachment(before_img_path, "before.png"))
            if after_img_path: attachments.append(self._convert_file_to_attachment(after_img_path, "after.png"))
            
            # Filter out None values from attachments if files weren't found
            if attachments:
                params["attachments"] = [a for a in attachments if a]

            resend.Emails.send(params)
            return {"delivery_status": "dispatched"}
        except Exception as e:
            return {"delivery_status": "failed", "error": str(e)}