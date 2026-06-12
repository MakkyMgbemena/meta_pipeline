<#
Deploy Streamlit dashboard to Cloud Run (PowerShell)

Usage:
  ./scripts/deploy_streamlit.ps1

Notes:
 - Make sure you're authenticated: gcloud auth login
 - This script uses the image tag already built. Use the build script first.
#>

param()

$image = "northamerica-northeast2-docker.pkg.dev/project-24b04b3d-fdd9-4b07-855/meta-pipeline/meta-pipeline-main:latest"
$region = "northamerica-northeast2"
$service = "meta-pipeline-dashboard"
$db_instance = "project-24b04b3d-fdd9-4b07-855:northamerica-northeast2:meta-pipeline-db"
$backend_url = "https://meta-pipeline-backend-680132354800.northamerica-northeast2.run.app"

Write-Host "Deploying Streamlit dashboard to Cloud Run ($service)"

gcloud run deploy $service `
  --image $image `
  --region $region `
  --memory 4Gi `
  --cpu 2 `
  --timeout 300 `
  --set-env-vars INSTANCE_CONNECTION_NAME=$db_instance,SERVICE_TYPE=streamlit,BACKEND_URL=$backend_url `
  --add-cloudsql-instances $db_instance `
  --allow-unauthenticated

Write-Host "Done. Open the Cloud Run URL from the gcloud output or the Console."
