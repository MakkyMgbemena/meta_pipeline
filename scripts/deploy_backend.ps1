<#
Deploy FastAPI backend to Cloud Run (PowerShell)

Usage:
  ./scripts/deploy_backend.ps1
#>

param()

$image = "northamerica-northeast2-docker.pkg.dev/project-24b04b3d-fdd9-4b07-855/meta-pipeline/meta-pipeline-main:latest"
$region = "northamerica-northeast2"
$service = "meta-pipeline-backend"
$db_instance = "project-24b04b3d-fdd9-4b07-855:northamerica-northeast2:meta-pipeline-db"

Write-Host "Deploying FastAPI backend to Cloud Run ($service)"

gcloud run deploy $service `
  --image $image `
  --region $region `
  --memory 4Gi `
  --cpu 2 `
  --timeout 300 `
  --set-env-vars INSTANCE_CONNECTION_NAME=$db_instance,SERVICE_TYPE=fastapi `
  --add-cloudsql-instances $db_instance `
  --allow-unauthenticated

Write-Host "Done. Backend deployed."
