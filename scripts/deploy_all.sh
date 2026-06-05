#!/bin/sh
# Build and deploy both services (bash)

IMAGE="northamerica-northeast2-docker.pkg.dev/project-24b04b3d-fdd9-4b07-855/meta-pipeline/meta-pipeline-main:latest"
REGION="northamerica-northeast2"
DB_INSTANCE="project-24b04b3d-fdd9-4b07-855:northamerica-northeast2:meta-pipeline-db"

echo "Building image..."
gcloud builds submit --tag $IMAGE

BACKEND_URL="https://meta-pipeline-backend-680132354800.northamerica-northeast2.run.app"

echo "Deploying Streamlit dashboard..."
gcloud run deploy meta-pipeline-dashboard \
  --image $IMAGE \
  --region $REGION \
  --memory 4Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars INSTANCE_CONNECTION_NAME=$DB_INSTANCE,SERVICE_TYPE=streamlit,BACKEND_URL=$BACKEND_URL \
  --add-cloudsql-instances $DB_INSTANCE \
  --allow-unauthenticated

echo "Deploying FastAPI backend..."
gcloud run deploy meta-pipeline-backend \
  --image $IMAGE \
  --region $REGION \
  --memory 4Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars INSTANCE_CONNECTION_NAME=$DB_INSTANCE,SERVICE_TYPE=fastapi \
  --add-cloudsql-instances $DB_INSTANCE \
  --allow-unauthenticated

echo "Done."
