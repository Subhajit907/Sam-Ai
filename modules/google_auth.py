"""Shared Google OAuth2 authentication for Gmail and Sheets APIs."""

import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Both Gmail (send + read) and Sheets (read + write)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(_BASE_DIR, "google_token.pkl")
CREDENTIALS_FILE = os.path.join(_BASE_DIR, "credentials.json")


def get_credentials() -> Credentials:
    """
    Return valid Google OAuth2 credentials.
    - First run: opens browser for user to authorize → saves token.
    - Subsequent runs: loads saved token, refreshes if expired.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    "\n\ncredentials.json not found!\n"
                    "Please follow the setup steps:\n"
                    "  1. Go to https://console.cloud.google.com\n"
                    "  2. Create a project → Enable Gmail API + Google Sheets API\n"
                    "  3. Create OAuth 2.0 credentials (Desktop App)\n"
                    "  4. Download credentials.json → place it in the project root\n"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return creds
