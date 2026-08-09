"""
Vertex AI Client Initializer using service account credentials.
"""

import os
import logging
from typing import Optional

from google import genai
from google.oauth2 import service_account
from config import settings

logger = logging.getLogger(__name__)


def get_genai_client(location: Optional[str] = None) -> genai.Client:
    """Returns a Google GenAI Client authenticated via Vertex AI Service Account or API key."""

    cred_base64 = settings.VERTEX_CREDENTIALS_BASE64
    cred_path = settings.VERTEX_CREDENTIALS_PATH
    project_id = settings.VERTEX_PROJECT_ID
    target_location = location or settings.VERTEX_LOCATION

    if cred_base64:
        logger.info(f"Authenticating via VERTEX_CREDENTIALS_BASE64 env variable (location={target_location})")
        import base64
        import json
        json_acct = json.loads(base64.b64decode(cred_base64).decode("utf-8"))
        creds = service_account.Credentials.from_service_account_info(
            json_acct,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return genai.Client(
            vertexai=True,
            project=project_id,
            location=target_location,
            credentials=creds
        )
    elif cred_path.exists():
        logger.info(f"Authenticating with Vertex AI Service Account credentials at {cred_path} (location={target_location})")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path)
        creds = service_account.Credentials.from_service_account_file(
            str(cred_path),
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return genai.Client(
            vertexai=True,
            project=project_id,
            location=target_location,
            credentials=creds
        )
    elif settings.GEMINI_API_KEY:
        logger.info("Authenticating via GEMINI_API_KEY")
        return genai.Client(api_key=settings.GEMINI_API_KEY)
    else:
        logger.warning("No credentials found. Initializing default client.")
        return genai.Client()
