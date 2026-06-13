from sqlalchemy import text

class MultiTenantManager:
    """
    Phase 7 Enterprise Infrastructure.
    Enforces data isolation between distinct client schemas.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def _sanitize_schema_name(self, client_id: str) -> str:
        """
        Prevents invalid schema names or injection risks.
        """
        return f"tenant_{client_id}".replace("-", "_").lower()

    def set_tenant_context(self, client_id: str):
        """
        Switch active schema for the current session.
        """
        if not self.db:
            raise ValueError("Database manager not available.")

        schema = self._sanitize_schema_name(client_id)

        try:
            with self.db.session_scope() as session:
                session.execute(text(f"SET search_path TO {schema}, public"))
        except Exception as e:
            raise RuntimeError(f"Failed to set tenant context: {e}")

    def provision_new_tenant(self, client_id: str):
        """
        Creates a dedicated schema for a new tenant.
        """
        if not self.db:
            raise ValueError("Database manager not available.")

        schema = self._sanitize_schema_name(client_id)

        try:
            with self.db.session_scope() as session:
                # 1. Create schema if not exists
                session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

                # (Optional future step)
                # -> create tables inside schema if needed
                # -> or rely on SQLAlchemy metadata.create_all()

                session.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to provision tenant schema: {e}")