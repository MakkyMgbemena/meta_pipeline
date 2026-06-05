**Deployment and persistence notes**

- **One-time vs persistent:** Cloud Run deployments (the services you create) are persistent — once deployed they remain running until you change or delete them. The Docker image pushed to Artifact Registry is also persistent.
- **What is not persistent:** local shell environment variables, virtualenv state, or temporary files in Cloud Shell are ephemeral and may need re-creating after a reboot or new session.

Quick workflow (recommended):

1. Authenticate once per machine session: `gcloud auth login` (this persists until token expiry). For CI/automation use a service account and secrets instead.
2. Build and push image: use `scripts/deploy_all.ps1` (Windows) or `scripts/deploy_all.sh` (bash).
3. The scripts deploy two Cloud Run services:
   - `meta-pipeline-dashboard` (Streamlit)
   - `meta-pipeline-backend` (FastAPI)
4. The frontend service uses the `BACKEND_URL` environment variable to connect to the backend API.

GitHub Actions template:
- A workflow template has been added at `.github/workflows/deploy.yml`.
- It builds the container and deploys both Cloud Run services.
- Requires `secrets.GCP_SA_KEY` to authenticate to Google Cloud.

Automation / one-key launch options:

- Use the included `scripts/deploy_all.ps1` (PowerShell) or `scripts/deploy_all.sh` (bash) to run a single command that builds and deploys both services.
- For CI/CD, create a GitHub Actions or Cloud Build trigger to build & deploy automatically on push to `main`. This is recommended — it avoids needing to run anything locally after reboot.

Security note:

- For fully automated deployments, use a service account with least privileges and store credentials in your CI secret store. Avoid placing long-lived JSON keys on your development machine.

If you want, I can add a GitHub Actions workflow to auto-deploy on push.
