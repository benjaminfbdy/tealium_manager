import os
import requests
from dotenv import load_dotenv
from database import get_active_configuration
from typing import Dict, List, Optional

class TealiumClient:
    def __init__(self, account=None, profile=None, api_key=None, email=None):
        self.account = account
        self.profile = profile
        self.api_key = api_key
        self.email = email
        
        # Load credentials if not provided
        if not all([self.account, self.profile, self.api_key, self.email]):
            active_config = get_active_configuration()
            if active_config:
                self.account = active_config.get("account")
                self.profile = active_config.get("profile")
                self.api_key = active_config.get("api_key")
                self.email = active_config.get("email")

        if not all([self.account, self.profile, self.api_key, self.email]):
            raise ValueError("Les identifiants Tealium (compte, profil, clé API, email) n'ont pas été trouvés.")

        self.base_url_v2 = "https://api.tealiumiq.com/v2"
        self.base_url_v3_auth = "https://platform.tealiumapis.com/v3"

        self.token_v2 = None
        self.token_v3 = None
        self.host_v3 = None

    def _authenticate_v2(self):
        """Authenticates with Tealium iQ API v2."""
        if self.token_v2: return True
        if not all([self.api_key, self.email]): return False

        auth_url = f"{self.base_url_v2}/auth"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {"username": self.email, "key": self.api_key}
        
        try:
            response = requests.post(auth_url, data=payload, headers=headers)
            response.raise_for_status()
            self.token_v2 = response.json().get("token")
            print("Successfully authenticated with Tealium iQ API v2.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"V2 Authentication failed: {e}")
            return False

    def _authenticate_v3(self):
        """Authenticates with Tealium API v3 to get a token and a region-specific host."""
        if self.token_v3 and self.host_v3: return True
        if not all([self.api_key, self.email, self.account, self.profile]): return False
        
        auth_url = f"{self.base_url_v3_auth}/auth/accounts/{self.account}/profiles/{self.profile}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {"username": self.email, "key": self.api_key}

        try:
            response = requests.post(auth_url, data=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.token_v3 = data.get("token")
            self.host_v3 = data.get("host")
            if self.token_v3 and self.host_v3:
                print(f"Successfully authenticated with Tealium API v3 for host: {self.host_v3}")
                return True
            return False
        except requests.exceptions.RequestException as e:
            print(f"V3 Authentication failed: {e}")
            return False

    def _get_headers_v2(self):
        if self._authenticate_v2():
            return {"Authorization": f"Bearer {self.token_v2}", "Content-Type": "application/json"}
        return None

    def _get_headers_v3(self):
        if self._authenticate_v3():
            return {"Authorization": f"Bearer {self.token_v3}", "Content-Type": "application/json"}
        return None

    def get_profile_components(self, component_types: Optional[List[str]] = None, publish_version: Optional[str] = None) -> Dict:
        """Fetches components of a Tealium iQ profile using the V3 API."""
        headers = self._get_headers_v3()
        if not headers or not self.host_v3:
            return {"error": True, "message": "Échec de l'authentification V3. Impossible d'obtenir le token ou l'hôte régional."}

        url = f"https://{self.host_v3}/v3/tiq/accounts/{self.account}/profiles/{self.profile}"
        params = {'includes': component_types} if component_types else {}
        if publish_version:
            params['publishVersion'] = publish_version
        
        print(f"DEBUG: Fetching profile components from URL: {url}")
        print(f"DEBUG: Params: {params}")

        response = None
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return {"error": False, "data": response.json()}
        except requests.exceptions.HTTPError as e:
            # ... (error handling logic remains the same)
            error_message = f"HTTP Error fetching profile components: {e}"
            print(f"DEBUG: {error_message}")
            if response is not None:
                try: body = response.json()
                except ValueError: body = response.text
                return {"error": True, "message": str(e), "status_code": response.status_code, "body": body}
            return {"error": True, "message": str(e)}
        except requests.exceptions.RequestException as e:
            return {"error": True, "message": f"Request Error: {e}"}

    def get_revisions(self) -> Optional[List[str]]:
        """Fetches a list of revision IDs for the active Tealium iQ profile using the V2 API."""
        headers = self._get_headers_v2()
        if not headers:
            print("Error: Not authenticated (v2). Cannot fetch revisions.")
            return None

        url = f"{self.base_url_v2}/manifest/accounts/{self.account}/profiles/{self.profile}/revisions"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching revisions: {e}")
            if response is not None: print(f"Response body: {response.text}")
        return None

    def get_revision_details(self, revision_id: str) -> Optional[Dict]:
        """Fetches the details of a specific revision for the active Tealium iQ profile using the V2 API."""
        headers = self._get_headers_v2()
        if not headers:
            print("Error: Not authenticated (v2). Cannot fetch revision details.")
            return None

        url = f"{self.base_url_v2}/manifest/accounts/{self.account}/profiles/{self.profile}/revisions/{revision_id}/details"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching revision details for ID {revision_id}: {e}")
            if response is not None: print(f"Response body: {response.text}")
        return None
