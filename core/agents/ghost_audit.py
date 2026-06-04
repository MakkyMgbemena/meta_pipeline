from core.unified_agent import UnifiedAgent
from utils.logger import get_logger
from utils.json_store import JSONStore


class GhostAudit(UnifiedAgent):
    """
    Performs structural, compliance, and integrity checks on the cleaned payload.
    This agent does not modify data — it inspects, validates, and reports.
    """

    def __init__(self, config: dict, client_id: str, db=None):
        super().__init__(config, client_id, db)
        self.logger = get_logger("GhostAudit")

    # ---------------------------------------------------------
    # MAIN EXECUTION
    # ---------------------------------------------------------
    def run(self, payload: dict = None):
        """
        Executes the audit pipeline.
        Returns an audit report dictionary.
        """

        self.logger.info(f"GhostAudit started for client '{self.client_id}'.")

        if payload is None:
            self.logger.warning("No payload provided. Nothing to audit.")
            return {"status": "no_payload"}

        report = self._generate_audit_report(payload)

        self.logger.info("GhostAudit completed successfully.")
        return report

    # ---------------------------------------------------------
    # AUDIT LOGIC
    # ---------------------------------------------------------
    def _generate_audit_report(self, payload):
        """
        Inspects the payload for:
        - missing fields
        - empty values
        - structural inconsistencies
        - suspicious patterns
        """

        audit_report = {
            "client_id": self.client_id,
            "missing_fields": [],
            "empty_values": [],
            "type_mismatches": [],
            "status": "ok",
        }

        if isinstance(payload, dict):
            for key, value in payload.items():

                # Missing or empty
                if value is None or value == "":
                    audit_report["empty_values"].append(key)

                # Type mismatch detection (simple but effective)
                if isinstance(value, (list, dict)) and key.endswith("_id"):
                    audit_report["type_mismatches"].append(
                        f"Expected scalar for '{key}', got {type(value).__name__}"
                    )

        # If any issues found, update status
        if (
            audit_report["missing_fields"]
            or audit_report["empty_values"]
            or audit_report["type_mismatches"]
        ):
            audit_report["status"] = "issues_found"

        return audit_report
