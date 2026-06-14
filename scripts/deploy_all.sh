#!/bin/sh
# Build and deploy both services (bash)

# Exit immediately if any command fails. This prevents hanging on broken deployments.
set -e

IMAGE="northamerica-northeast2-docker.pkg.dev/project-24b04b3d-fdd9-4b07-855/meta-pipeline/meta-pipeline-main:latest"
REGION="northamerica-northeast2"
DB_INSTANCE="project-24b04b3d-fdd9-4b07-855:northamerica-northeast2:meta-pipeline-db"

echo "Building image..."
gcloud builds submit --tag $IMAGE

echo "Deploying FastAPI backend (waiting for startup)..."
gcloud run deploy meta-pipeline-backend \
  --image $IMAGE \
  --region $REGION \
  --memory 4Gi \
  --cpu 2 \
  --timeout 120 \
  --set-env-vars INSTANCE_CONNECTION_NAME=$DB_INSTANCE,SERVICE_TYPE=fastapi \
  --add-cloudsql-instances $DB_INSTANCE \
  --allow-unauthenticated --quiet

# Dynamically retrieve the backend URL to ensure environment consistency
BACKEND_URL=$(gcloud run services describe meta-pipeline-backend --region "$REGION" --format 'value(status.url)')
echo "Backend detected at: $BACKEND_URL"

echo "Deploying Streamlit dashboard (waiting for startup)..."
gcloud run deploy meta-pipeline-dashboard \
  --image $IMAGE \
  --region $REGION \
  --memory 4Gi \
  --cpu 2 \
  --timeout 120 \
  --set-env-vars INSTANCE_CONNECTION_NAME=$DB_INSTANCE,SERVICE_TYPE=streamlit,BACKEND_URL=$BACKEND_URL \
  --add-cloudsql-instances $DB_INSTANCE \
  --allow-unauthenticated --quiet

echo "Done."
