import os
from datetime import datetime, timedelta
from jose import jwt # Ensure 'jose' is in your requirements.txt

class JWTManager:
    """
    Phase 6 Security & Data Isolation.
    Handles encrypted token generation to secure the SaaS Gateway [Source 482, 673].
    """
    SECRET_KEY = os.getenv("JWT_SECRET")
    ALGORITHM = "HS256"

    def create_access_token(self, data: dict, expires_delta: timedelta = None):
        """
        Generates a secure token for authenticated SaaS dashboard access [Source 482].
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=60))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

    def verify_access_token(self, token: str) -> dict:
        """
        Decodes and validates tokens to enforce cross-tenant privacy [Source 482, 484].
        """
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            return payload
        except Exception:
            return None
