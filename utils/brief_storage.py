import json
import os
import re
from pathlib import Path
from datetime import datetime

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
BASE_DIR = Path("data/mission_briefs")

# ==============================================================================
# HELPER FUNCTIONS (SANITIZATION & VALIDATION)
# ==============================================================================
def clean_client_id(client_id: str) -> str:
    """
    Prevents path traversal attacks. Only allows letters, numbers, and underscores.
    """
    return re.sub(r'[^a-zA-Z0-9_]', '', client_id)

# ==============================================================================
# CORE OPERATIONS: SAVE & LOAD
# ==============================================================================
def save_brief(client_id: str, industry: str, brief_data: dict) -> str:
    """
    Saves a mission brief with security and concurrency hardening.
    """
    safe_id = clean_client_id(client_id)
    safe_industry = clean_client_id(industry).lower()
    
    client_dir = BASE_DIR / safe_id
    client_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = client_dir / f"brief_{timestamp}.json"
    
    brief_data["client_id"] = safe_id
    brief_data["industry"] = safe_industry
    brief_data["created_at"] = timestamp
    
    with open(filename, "w") as f:
        json.dump(brief_data, f, indent=2)
        
    return str(filename)

def load_brief(client_id: str) -> dict:
    """
    Loads the most recent mission brief for a client.
    """
    safe_id = clean_client_id(client_id)
    client_dir = BASE_DIR / safe_id
    
    if not client_dir.exists():
        return {}
        
    files = list(client_dir.glob("brief_*.json"))
    if not files:
        return {}
        
    latest_file = max(files, key=os.path.getmtime)
    
    try:
        with open(latest_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

# ==============================================================================
# CROSS-REFERENCING CAPABILITIES
# ==============================================================================
def get_briefs_by_industry(target_industry: str) -> list:
    """
    Returns all briefs matching an industry vertical.
    """
    matching_briefs = []
    safe_industry = clean_client_id(target_industry).lower()
    
    if not BASE_DIR.exists():
        return []
        
    for file_path in BASE_DIR.rglob("brief_*.json"):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                if data.get("industry") == safe_industry:
                    matching_briefs.append(data)
        except (json.JSONDecodeError, FileNotFoundError):
            continue
            
    return matching_briefs