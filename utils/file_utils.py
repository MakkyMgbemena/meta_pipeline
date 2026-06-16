import re
import unicodedata
from typing import Any, List

def clean_whitespace(text: str) -> str:
    """Removes excessive whitespace, newlines, tabs, and normalizes spacing."""
    if not isinstance(text, str):
        return text
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def normalize_text(text: str) -> str:
    """Normalizes Unicode and removes invisible artifacts."""
    if not isinstance(text, str):
        return text
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
    return text

# --- NEW: ENTERPRISE IMPUTATION & VALIDATION ---

def impute_value(value: Any, config: dict) -> Any:
    """
    Implements meta_pipeline.imputation logic.
    If value is missing, resolves fallback according to Enterprise Policy.
    """
    if value not in [None, "", "null", "NaN"]:
        return value

    impute_cfg = config.get("meta_pipeline", {}).get("imputation", {}).get("system_defaults", {}).get("imputation", {})
    strategy = impute_cfg.get("missing_value_strategy", "preserve_and_flag")
    fallback = impute_cfg.get("fallback_vector_target", "unknown")

    if strategy == "impute_fallback":
        return fallback
    
    # Default: preserve None so VerifierAgent can flag it
    return None

def validate_platform(platform: str, config: dict) -> bool:
    """
    Validates if a platform is within the meta_pipeline.platform_capabilities.supported_platforms list.
    """
    supported = config.get("meta_pipeline", {}).get("platform_capabilities", {}).get("supported_platforms", [])
    if platform.lower() in [p.lower() for p in supported]:
        return True
    return False
