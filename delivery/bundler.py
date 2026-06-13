import zipfile
import os
from datetime import datetime, timedelta

class DeliveryBundler:
    """
    Phase 6 Delivery Infrastructure.
    Packages cleaned datasets and audit reports in multiple industry-standard formats:
    - ZIP (Compressed Bundle)
    - DIRECT (Individual Uncompressed GCS URLs)
    - JSON (Raw programmatic payload)
    """

    def bundle_mission_assets(self, client_id: str, file_paths: list, format_preference: str = "zip") -> dict:
        """
        Consolidates and delivers assets according to the client's format preference.
        Supported formats: 'zip' (default), 'direct' (individual links), 'json' (raw preview).
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
        bucket_name = os.getenv("GCS_BUCKET_NAME")

        if not bucket_name:
            print("Warning: GCS_BUCKET_NAME not set. Ephemeral local paths will be used.")

        # --- FORMAT 1: ZIP (Standard Compressed Bundle) ---
        if format_preference.lower() == "zip":
            local_bundle_path = f"reports/bundles/{client_id}_mission_{timestamp}.zip"
            os.makedirs(os.path.dirname(local_bundle_path), exist_ok=True)

            try:
                # Zip the files
                with zipfile.ZipFile(local_bundle_path, 'w') as zipf:
                    for file in file_paths:
                        if os.path.exists(file):
                            zipf.write(file, os.path.basename(file))

                if not bucket_name:
                    return {"delivery_type": "zip", "url": local_bundle_path}

                # Upload to GCS
                from google.cloud import storage
                client = storage.Client()
                bucket = client.bucket(bucket_name)
                
                blob_name = f"delivery_bundles/{client_id}/mission_assets_{timestamp}.zip"
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(local_bundle_path)

                # Generate secure signed URL
                signed_url = blob.generate_signed_url(
                    version="v4", expiration=timedelta(days=7), method="GET"
                )

                # Cleanup local temporary file
                if os.path.exists(local_bundle_path):
                    os.remove(local_bundle_path)

                return {
                    "status": "success",
                    "delivery_type": "zip_bundle",
                    "download_url": signed_url,
                    "expires_at_utc": (datetime.utcnow() + timedelta(days=7)).isoformat()
                }

            except Exception as e:
                print(f"ZIP Delivery creation failed: {e}")
                return {"status": "error", "message": str(e)}

        # --- FORMAT 2: DIRECT (Individual Uncompressed Files) ---
        elif format_preference.lower() == "direct":
            if not bucket_name:
                return {
                    "delivery_type": "direct_local",
                    "file_paths": [path for path in file_paths if os.path.exists(path)]
                }

            try:
                from google.cloud import storage
                client = storage.Client()
                bucket = client.bucket(bucket_name)
                
                delivery_links = {}

                # Upload each file individually and get unique signed links
                for file_path in file_paths:
                    if not os.path.exists(file_path):
                        continue
                    
                    filename = os.path.basename(file_path)
                    blob_name = f"deliveries/{client_id}/{timestamp}_{filename}"
                    blob = bucket.blob(blob_name)
                    blob.upload_from_filename(file_path)

                    # Generate individual signed URL
                    signed_url = blob.generate_signed_url(
                        version="v4", expiration=timedelta(days=7), method="GET"
                    )
                    
                    # Deduce format key (e.g. "report_json", "dataset_csv")
                    extension = filename.split(".")[-1]
                    delivery_links[f"{filename.split('.')[0]}_{extension}"] = signed_url

                return {
                    "status": "success",
                    "delivery_type": "individual_assets",
                    "download_links": delivery_links,
                    "expires_at_utc": (datetime.utcnow() + timedelta(days=7)).isoformat()
                }

            except Exception as e:
                print(f"Direct Delivery upload failed: {e}")
                return {"status": "error", "message": str(e)}

        # --- FORMAT 3: JSON / RAW (Machine Readable Metadata) ---
        elif format_preference.lower() == "json":
            raw_metadata = {
                "client_id": client_id,
                "delivery_timestamp": datetime.utcnow().isoformat(),
                "assets_delivered": [os.path.basename(path) for path in file_paths if os.path.exists(path)]
            }
            return {
                "status": "success",
                "delivery_type": "json_metadata",
                "metadata": raw_metadata
            }

        else:
            return {"status": "error", "message": f"Unknown delivery format preference: {format_preference}"}
