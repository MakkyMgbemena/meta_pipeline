def is_missing(value) -> bool:
    """
    Returns True if a value is considered 'missing'.
    Missing means:
    - None
    - empty string
    - empty list/dict
    """
    if value is None:
        return True
    if value == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def is_type(value, expected_type) -> bool:
    """
    Checks if a value matches an expected type.
    Example:
        is_type("hello", str) -> True
        is_type(123, str) -> False
    """
    return isinstance(value, expected_type)


def validate_required_fields(payload: dict, required_fields: list) -> list:
    """
    Returns a list of missing required fields.
    """
    missing = []
    for field in required_fields:
        if field not in payload or is_missing(payload[field]):
            missing.append(field)
    return missing


def validate_numeric(value, field_name: str, warnings: list):
    """
    Adds warnings for numeric fields that look suspicious.
    Example:
    - negative revenue
    - negative cost
    """
    if value is None:
        return

    try:
        num = float(value)
    except Exception:
        warnings.append(f"{field_name} is not numeric.")
        return

    if num < 0:
        warnings.append(f"{field_name} is negative — verify correctness.")
def validate_client_id(client_id: str, config: dict) -> bool:
    return client_id in config.get("meta_pipeline", {}).get("clients", {})

def clean_client_id(client_id: str) -> str:
    """
    Normalize client IDs used by FastAPI routes.
    Keeps IDs predictable without requiring config lookup.
    """
    if client_id is None:
        return ""
    return str(client_id).strip()
