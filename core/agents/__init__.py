from .smart_cleaner import SmartCleaner
from .ghost_audit import GhostAudit
from .ledger import LedgerAgent
from .registry import RegistryAgent
from .lead_nurturer import LeadNurturer
from .verifier_agent import VerifierAgent
from .seo_agent import SEOAgent
from .google_manager import GoogleManager
from .upwork_manager import UpworkManager
from .linkedin_manager import LinkedInManager
from .dual_write_gate import DualWriteGate

# The Single Source of Truth for the Orchestrator [Source 397]
# These keys MUST match the entries in your routing_chain in config.yaml
AGENT_REGISTRY = {
    "smart_cleaner": SmartCleaner,
    "ghost_audit": GhostAudit,
    "verifier_agent": VerifierAgent,
    "ledger_entry": LedgerAgent,
    "client_registry": RegistryAgent,
    "lead_nurture": LeadNurturer,
    "seo_optimize": SEOAgent,      # Strategic Agent 1
    "google_manage": GoogleManager, # Strategic Agent 2
    "upwork_manage": UpworkManager,
    "linkedin_manage": LinkedInManager,
    "dual_write": DualWriteGate
}