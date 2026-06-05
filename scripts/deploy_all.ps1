# scripts/deploy_all.ps1

Write-Host "Deploying backend..." -ForegroundColor Cyan
& "$PSScriptRoot\deploy_backend.ps1"

Write-Host "Deploying Streamlit..." -ForegroundColor Cyan
& "$PSScriptRoot\deploy_streamlit.ps1"

Write-Host "All services deployed." -ForegroundColor Green

