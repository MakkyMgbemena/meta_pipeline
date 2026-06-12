import os
import resend


class EmailSender:
    """
    Phase 6 Automated Delivery.
    Supports both client-facing reports and multi-stage internal HITL alerts.
    """

    def __init__(self):
        resend.api_key = os.getenv("RESEND_API_KEY")

    def _convert_file_to_attachment(self, file_path: str, filename: str):
        if not file_path or not os.path.exists(file_path):
            return None
        with open(file_path, "rb") as f:
            content = list(f.read())
        return {"filename": filename, "content": content}

    # Used for the final client outcome
    def send_mission_report(
        self,
        to_email: str,
        client_id: str,
        status: str,
        human_html_content: str,
        before_img_path: str = None,
        after_img_path: str = None,
    ):
        try:
            params = {
                "from": "Universal Headquarters <reports@travelbunny.services>",
                "to": ["annastecias@gmail.com", "makky@travelbunny.services", to_email],
                "subject": f"Mission Update: {client_id} - [{status}]",
                "html": human_html_content,
            }
            attachments = []
            if before_img_path:
                attachments.append(
                    self._convert_file_to_attachment(before_img_path, "before.png")
                )
            if after_img_path:
                attachments.append(
                    self._convert_file_to_attachment(after_img_path, "after.png")
                )
            if attachments:
                params["attachments"] = [a for a in attachments if a]

            resend.Emails.send(params)
            return {"delivery_status": "dispatched"}
        except Exception as e:
            return {"delivery_status": "failed", "error": str(e)}

    # Used for multi-stage internal verification
    def send_internal_alert(self, client_id: str, stage_name: str, details: str):
        try:
            resend.Emails.send(
                {
                    "from": "Universal Headquarters <alerts@travelbunny.services>",
                    "to": ["annastecias@gmail.com", "makky@travelbunny.services"],
                    "subject": f"HITL Verification Required: {client_id} [{stage_name}]",
                    "html": f"<h3>Stage: {stage_name}</h3><p>Mission for {client_id} is awaiting verification.</p><p>{details}</p>",
                }
            )
            return {"delivery_status": "alerted"}
        except Exception as e:
            return {"delivery_status": "failed", "error": str(e)}
