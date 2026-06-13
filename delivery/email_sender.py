import os
import resend

class EmailSender:
    """
    Phase 6 Automated Delivery.
    Supports both client-facing reports and multi-stage internal HITL alerts.
    Provides native handling of Cloud Storage (GCS) URLs and local files for attachments.
    """

    def __init__(self):
        # Configure resend API key
        resend.api_key = os.getenv("RESEND_API_KEY")

    def _convert_file_to_attachment(self, file_path: str, filename: str) -> dict:
        """
        Standardizes attachments.
        If file_path is an HTTP/GCS URL, uses Resend's native cloud 'path' mechanism.
        If file_path is a local path, converts it to raw content bytes.
        """
        if not file_path:
            return None

        # --- Case A: Cloud Storage URL (No downloading, saves container RAM!) ---
        if file_path.startswith("http://") or file_path.startswith("https://"):
            return {
                "filename": filename,
                "path": file_path  # Resend natively fetches public/signed URLs!
            }

        # --- Case B: Local File System Fallback ---
        if os.path.exists(file_path):
            try:
                with open(file_path, "rb") as f:
                    content = list(f.read())
                return {
                    "filename": filename,
                    "content": content
                }
            except Exception as e:
                print(f"Failed to read local attachment {file_path}: {e}")
                return None

        return None

    def send_mission_report(
        self,
        to_email: str,
        client_id: str,
        status: str,
        human_html_content: str,
        before_img_path: str = None,
        after_img_path: str = None,
    ) -> dict:
        """
        Dispatches the final client outcome email.
        Supports automatic resolution of both cloud and local screenshot attachments.
        """
        try:
            params = {
                "from": "Universal Headquarters <reports@travelbunny.services>",
                "to": ["annastecias@gmail.com", "makky@travelbunny.services", to_email],
                "subject": f"Mission Update: {client_id} - [{status.upper()}]",
                "html": human_html_content,
            }
            
            # Dynamically resolve attachments
            attachments = []
            if before_img_path:
                att_before = self._convert_file_to_attachment(before_img_path, "before.png")
                if att_before:
                    attachments.append(att_before)
            if after_img_path:
                att_after = self._convert_file_to_attachment(after_img_path, "after.png")
                if att_after:
                    attachments.append(att_after)
            
            if attachments:
                params["attachments"] = attachments

            resend.Emails.send(params)
            return {"delivery_status": "dispatched"}
        except Exception as e:
            return {"delivery_status": "failed", "error": str(e)}

    def send_internal_alert(self, client_id: str, stage_name: str, details: str) -> dict:
        """
        Used for multi-stage internal Human-in-the-loop (HITL) alerts.
        """
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
