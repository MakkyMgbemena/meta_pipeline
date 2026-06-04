import os
import google.auth
import google.auth.transport.requests
from google.oauth2 import id_token
from selenium import webdriver
from selenium.webdriver.remote.remote_connection import RemoteConnection
from utils.logger import get_logger
from services.fastapi.models import ClientRegistry

logger = get_logger("Auth")

class AuthenticatedRemoteConnection(RemoteConnection):
    """Custom connection to inject OIDC Bearer tokens into every request."""
    def __init__(self, remote_server_addr, token, keep_alive=True):
        super().__init__(remote_server_addr, keep_alive=keep_alive)
        self.token = token

    def _request(self, method, url, body=None):
        # Inject header before sending the request
        self._headers['Authorization'] = f'Bearer {self.token}'
        return super()._request(method, url, body)

def get_browser_token(audience_url):
    """Fetches the OIDC token required to bypass the 403 lock."""
    auth_req = google.auth.transport.requests.Request()
    # The audience_url MUST be the base URL of your Browser Service
    return id_token.fetch_id_token(auth_req, audience_url)

def init_secure_driver():
    """Initializes the Remote WebDriver with the required OIDC Bearer Token."""
    browser_url = os.environ.get("SELENIUM_REMOTE_URL")
    
    if not browser_url:
        logger.error("SELENIUM_REMOTE_URL not detected. Ensure your environment variables are set.")
        raise EnvironmentError("SELENIUM_REMOTE_URL is not set. Point this to your cloud service URL.")

    logger.info(f"Connecting to Cloud Selenium instance: {browser_url}")

    # 1. Fetch the fresh token for the specific browser service audience
    token = get_browser_token(browser_url)
    
    # 2. Configure Chrome options for the cloud environment
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # 3. Use custom connection to ensure headers are sent during session creation
    # Standard RemoteConnection doesn't send the token on the first POST /session
    remote_conn = AuthenticatedRemoteConnection(
        f"{browser_url}/wd/hub", 
        token=token
    )
    
    driver = webdriver.Remote(
        command_executor=remote_conn,
        options=options
    )
    return driver

def ensure_client_registered(client_id: str, orchestrator):
    """Ensures client exists in the registry DB; inserts if missing."""
    if not orchestrator.db:
        return
    with orchestrator.db.session_scope() as session:
        client = session.query(ClientRegistry).filter_by(client_id=client_id).first()
        if not client:
            new_client = ClientRegistry(client_id=client_id, status="onboarding", last_sync=None)
            session.add(new_client)
            orchestrator.logger.info(f"Auto-onboarded new client: {client_id}")
        return client is not None
