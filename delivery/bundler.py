import zipfile
import os
from datetime import datetime

class DeliveryBundler:
    """
    Phase 6 Delivery Infrastructure.
    Packages cleaned datasets and audit reports for client delivery [Source 483].
    """
    def bundle_mission_assets(self, client_id: str, file_paths: list) -> str:
        """
        Creates a timestamped bundle containing the final mission results [Source 667].
        Returns the path to the consolidated delivery bundle.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
        bundle_path = f"reports/bundles/{client_id}_mission_{timestamp}.zip"
        
        # Ensure bundle directory exists
        os.makedirs(os.path.dirname(bundle_path), exist_ok=True)
        
        with zipfile.ZipFile(bundle_path, 'w') as zipf:
            for file in file_paths:
                if os.path.exists(file):
                    zipf.write(file, os.path.basename(file))
        
        return bundle_path