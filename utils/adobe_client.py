import time
import jwt
import requests
from typing import Dict, Optional, Any

class AdobeAnalyticsClient:
    """
    Client for interacting with the Adobe Analytics 2.0 API.
    Handles JWT authentication, token management, and paginated report requests.
    """
    TOKEN_ENDPOINT = "https://ims-na1.adobelogin.com/ims/exchange/jwt/"
    JWT_META_SCOPE = "https://ims-na1.adobelogin.com/c/ent_analytics_bulk_ingest_sdk"

    def __init__(self, config: Dict[str, str]):
        """
        Initializes the client with a configuration dictionary.
        
        Args:
            config (Dict[str, str]): A dictionary containing Adobe API credentials.
        """
        # Common
        self.global_company_id = config.get("global_company_id")
        self.api_key = config.get("api_key")
        self.auth_method = config.get("auth_method", "jwt")

        # JWT-specific
        self.client_secret = config.get("client_secret")
        self.tech_account_id = config.get("technical_account_id")
        self.org_id = config.get("organization_id")
        self.private_key = config.get("private_key")
        
        # Manual token-specific
        self.manual_access_token = config.get("manual_access_token")

        self.access_token = None
        self.token_expiry = 0
        self.api_base_url = f"https://analytics.adobe.io/api/{self.global_company_id}"

    def _generate_jwt(self) -> str:
        """Generates the JSON Web Token for authentication."""
        payload = {
            "exp": int(time.time()) + 600,  # Token expires in 10 minutes
            "iss": self.org_id,
            "sub": self.tech_account_id,
            "aud": f"https://ims-na1.adobelogin.com/c/{self.api_key}",
            self.JWT_META_SCOPE: True
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def _refresh_access_token(self):
        """
        Exchanges the JWT for an access token from Adobe's identity service.
        """
        jwt_token = self._generate_jwt()
        data = {
            "client_id": self.api_key,
            "client_secret": self.client_secret,
            "jwt_token": jwt_token
        }
        
        response = requests.post(self.TOKEN_ENDPOINT, data=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        # Set expiry to be 60 seconds less than the actual expiry for a safety margin
        self.token_expiry = time.time() + (token_data.get("expires_in", 86400000) / 1000) - 60

    def _ensure_token(self):
        """Ensures a valid, non-expired access token is available."""
        if self.auth_method == "manual":
            if not self.manual_access_token:
                raise ValueError("Manual authentication method selected, but no access token was provided.")
            self.access_token = self.manual_access_token
            return

        # Default to JWT flow
        if not self.access_token or time.time() >= self.token_expiry:
            self._refresh_access_token()

    def get_report(self, report_definition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a report request and handles pagination to retrieve all data.

        Args:
            report_definition (Dict[str, Any]): The JSON definition of the report.

        Returns:
            Dict[str, Any]: The consolidated report response from all pages.
        """
        self._ensure_token()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Ensure settings exist
        if "settings" not in report_definition:
            report_definition["settings"] = {}
        
        # Set a reasonable limit, e.g., 1000, if not provided
        report_definition["settings"].setdefault("limit", 1000)
        report_definition["settings"]["page"] = 0

        final_report = None
        
        while True:
            response = requests.post(f"{self.api_base_url}/reports", headers=headers, json=report_definition)
            response.raise_for_status()
            page_data = response.json()

            if final_report is None:
                # This is the first page, use it as the base
                final_report = page_data
            else:
                # This is a subsequent page, append its rows
                if "rows" in page_data:
                    final_report["rows"].extend(page_data["rows"])

            if page_data.get("lastPage", True):
                # If lastPage is true or not present, we're done.
                break
            
            # Prepare for the next page
            report_definition["settings"]["page"] += 1
        
        return final_report

    def get_report_suites(self) -> Dict[str, Any]:
        """Retrieves all report suites for the company."""
        self._ensure_token()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": self.api_key,
            "Accept": "application/json"
        }
        # The endpoint for collections/report-suites is standard
        rs_endpoint = f"https://analytics.adobe.io/api/{self.global_company_id}/collections/suites"
        
        response = requests.get(rs_endpoint, headers=headers, params={"limit": 1000}) # High limit
        response.raise_for_status()
        return response.json()
