from core.unified_agent import UnifiedAgent
from utils.logger import get_logger

class GhostAudit(UnifiedAgent):
    """
    Performs structural, compliance, and integrity checks on the cleaned payload.
    This agent does not modify data — it inspects, validates, and reports.
    """

    def __init__(self, config: dict = None, client_id: str = None, db=None):
        super().__init__(config or {}, client_id, db)
        self.logger = get_logger("GhostAudit")
        self.db = db

    def run(self, payload: dict = None) -> dict:
        """
        Executes the audit pipeline.
        Returns a structured audit report and logs anomalies.
        """
        self.logger.info(f"GhostAudit started for client '{self.client_id}'.")

        # Handle empty payloads gracefully
        if payload is None:
            self.logger.warning("No payload provided. Nothing to audit.")
            return {
                "status": "failure",
                "reason": "no_payload",
                "client_id": self.client_id
            }

        try:
            # 1. Generate the dynamic audit report
            report = self._generate_audit_report(payload)

            # 2. Database Integration: Log audit results if database is available
            if self.db and self.client_id:
                try:
                    status_text = f"Audit Completed - Status: {report['status']}"
                    self.db.update_registry(self.client_id, status_text)
                    
                    # If the payload is a job, we could update the job status in DB
                    job_id = payload.get("job_id") if isinstance(payload, dict) else None
                    if job_id:
                        self.db.update_job_status(
                            job_id=job_id,
                            status="AUDITED",
                            payload={"audit_report": report}
                        )
                except Exception as db_err:
                    self.logger.warning(f"Failed to record audit status to database: {db_err}")

            self.logger.info(f"GhostAudit completed with status: {report['status']}.")
            return report

        except Exception as e:
            self.logger.error(f"GhostAudit processing failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "client_id": self.client_id
            }

    def _generate_audit_report(self, payload) -> dict:
        """
        Inspects the payload (supports both dicts and list of dicts recursively).
        Populates missing fields based on configuration requirements.
        """
        # Retrieve the list of required keys for this client/mission from config
        required_keys = self.config.get("audit", {}).get("required_fields", ["client_id"])

        report = {
            "client_id": self.client_id,
            "missing_fields": [],
            "empty_values": [],
            "type_mismatches": [],
            "status": "ok",
        }

        # Handle List of Payloads (Iterate and audit each item)
        if isinstance(payload, list):
            self.logger.info(f"Batch payload detected. Auditing {len(payload)} items.")
            for index, item in enumerate(payload):
                item_report = self._audit_single_dict(item, required_keys)
                
                # Append warnings with batch index references
                for field in item_report["missing_fields"]:
                    report["missing_fields"].append(f"item[{index}].{field}")
                for field in item_report["empty_values"]:
                    report["empty_values"].append(f"item[{index}].{field}")
                for mismatch in item_report["type_mismatches"]:
                    report["type_mismatches"].append(f"item[{index}].{mismatch}")
        
        # Handle Single Dictionary Payload
        elif isinstance(payload, dict):
            report = self._audit_single_dict(payload, required_keys)

        else:
            self.logger.warning("Scalar payload received. Running base value validation.")
            if payload == "":
                report["empty_values"].append("payload_root")

        # Update status if any anomalies were discovered
        if report["missing_fields"] or report["empty_values"] or report["type_mismatches"]:
            report["status"] = "issues_found"

        return report

    def _audit_single_dict(self, data: dict, required_keys: list) -> dict:
        """Helper method to audit a single dictionary flatly or recursively."""
        sub_report = {
            "client_id": self.client_id,
            "missing_fields": [],
            "empty_values": [],
            "type_mismatches": []
        }

        if not isinstance(data, dict):
            return sub_report

        # 1. Audit for REQUIRED keys (Populating missing_fields!)
        for req_key in required_keys:
            if req_key not in data:
                sub_report["missing_fields"].append(req_key)

        # 2. Audit existing values recursively
        for key, value in data.items():
            # Check for null or empty string values
            if value is None or value == "":
                sub_report["empty_values"].append(key)

            # Deep check nested dictionary structures
            elif isinstance(value, dict):
                nested = self._audit_single_dict(value, [])
                for field in nested["empty_values"]:
                    sub_report["empty_values"].append(f"{key}.{field}")
                for mismatch in nested["type_mismatches"]:
                    sub_report["type_mismatches"].append(f"{key}.{mismatch}")

            # Simple type mismatch auditing (scalar validation)
            if isinstance(value, (list, dict)) and key.endswith("_id"):
                sub_report["type_mismatches"].append(
                    f"Expected scalar for '{key}', got {type(value).__name__}"
                )

        return sub_report
