import time
import jwt
import requests
import logging
import json
from typing import Dict, Optional, Any
from urllib.parse import quote
from database import load_adobe_components, save_adobe_components


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdobeAnalyticsClient:
    """
    Client for interacting with the Adobe Analytics 2.0 API.
    Handles different authentication methods (OAuth 2.0, JWT, Manual) and paginated report requests.
    """
    JWT_TOKEN_ENDPOINT = "https://ims-na1.adobelogin.com/ims/exchange/jwt/"
    OAUTH_TOKEN_ENDPOINT_V3 = "https://ims-na1.adobelogin.com/ims/token/v3"
    JWT_META_SCOPE = "https://ims-na1.adobelogin.com/c/ent_analytics_bulk_ingest_sdk"

    def __init__(self, config: Dict[str, str]):
        """
        Initializes the client with a configuration dictionary.
        
        Args:
            config (Dict[str, str]): A dictionary containing Adobe API credentials and global settings.
        """
        # Common
        self.global_company_id = config.get("global_company_id")
        self.auth_method = config.get("auth_method", "oauth")

        # Credentials
        self.api_key = config.get("api_key") # Also Client ID
        self.client_secret = config.get("client_secret")
        self.tech_account_id = config.get("technical_account_id")
        self.org_id = config.get("organization_id")
        self.private_key = config.get("private_key")
        self.manual_access_token = config.get("manual_access_token")

        self.access_token = None
        self.token_expiry = 0
        self.api_base_url = f"https://analytics.adobe.io/api/{self.global_company_id}"

        # --- Proxy Setup ---
        self.proxies = self._create_proxies_dict(config)

    def _create_proxies_dict(self, settings: Dict) -> Optional[Dict]:
        """Helper to create a proxy dictionary if credentials are provided."""
        proxy_user = settings.get("proxy_user")
        proxy_password = settings.get("proxy_password")
        if proxy_user and proxy_password:
            proxy_host = "proxy-users.intranet.bpce-it.fr"
            proxy_port = "8080"
            # URL-encode only the password to handle special characters, matching user's working script.
            encoded_password = quote(proxy_password, safe='')
            proxy_auth_url = f"http://{proxy_user}:{encoded_password}@{proxy_host}:{proxy_port}"
            logger.info("Proxy enabled and configured with authentication.")
            return {"http": proxy_auth_url, "https": proxy_auth_url}
        logger.info("Proxy not configured (user/password missing). Proceeding with direct connection.")
        return None

    def _generate_jwt(self) -> str:
        """Generates the JSON Web Token for JWT authentication."""
        payload = {
            "exp": int(time.time()) + 600,
            "iss": self.org_id,
            "sub": self.tech_account_id,
            "aud": f"https://ims-na1.adobelogin.com/c/{self.api_key}",
            self.JWT_META_SCOPE: True
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def _refresh_jwt_token(self):
        """Exchanges the JWT for an access token."""
        logger.info("Refreshing Adobe access token using JWT.")
        data = {
            "client_id": self.api_key,
            "client_secret": self.client_secret,
            "jwt_token": self._generate_jwt()
        }
        response = requests.post(self.JWT_TOKEN_ENDPOINT, data=data, proxies=self.proxies)
        response.raise_for_status()
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.token_expiry = time.time() + (token_data.get("expires_in", 86400000) / 1000) - 60
        logger.info("Successfully refreshed Adobe access token using JWT.")

    def _refresh_oauth_token(self):
        """Retrieves an access token using OAuth 2.0 client credentials flow."""
        logger.info("Refreshing Adobe access token using OAuth 2.0.")
        data = {
            "client_id": self.api_key,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": "openid,AdobeID,additional_info.projectedProductContext,read_organizations,analytics.read,analytics.write"
        }
        response = requests.post(self.OAUTH_TOKEN_ENDPOINT_V3, data=data, proxies=self.proxies)
        response.raise_for_status()
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.token_expiry = time.time() + token_data.get("expires_in", 86400) - 60
        logger.info("Successfully refreshed Adobe access token using OAuth 2.0.")

    def _ensure_token(self):
        """Ensures a valid, non-expired access token is available."""
        if self.auth_method == "manual":
            logger.info("Using manual Adobe access token.")
            if not self.manual_access_token:
                raise ValueError("Manual authentication method selected, but no access token was provided.")
            self.access_token = self.manual_access_token
            return
        if not self.access_token or time.time() >= self.token_expiry:
            if self.auth_method == "oauth":
                self._refresh_oauth_token()
            elif self.auth_method == "jwt":
                self._refresh_jwt_token()
            else:
                raise ValueError(f"Unsupported authentication method: {self.auth_method}")

    def get_report(self, report_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a report request and handles pagination."""
        self._ensure_token()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        report_definition.setdefault("settings", {}).setdefault("limit", 1000)
        report_definition["settings"]["page"] = 0
        final_report = None
        
        endpoint = f"{self.api_base_url}/reports"
        logger.info(f"Attempting to post report to {endpoint}.")
        logger.info(f"Report definition payload: {json.dumps(report_definition, indent=2)}")

        while True:
            try:
                response = requests.post(endpoint, headers=headers, json=report_definition, proxies=self.proxies)
                response.raise_for_status()
                page_data = response.json()

                if final_report is None:
                    final_report = page_data
                else:
                    if "rows" in page_data:
                        final_report["rows"].extend(page_data["rows"])
                
                if page_data.get("lastPage", True):
                    break
                report_definition["settings"]["page"] += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"Error during Adobe report request: {e}")
                if e.response is not None:
                    logger.error(f"Response Status: {e.response.status_code}")
                    # Log the full error response body for debugging
                    logger.error(f"Error Response Body: {e.response.text}")
                # Re-raise the exception to be handled by the controller
                raise

        return final_report

    def get_report_suites(self) -> Dict[str, Any]:
        """Retrieves all report suites for the company, handling pagination."""
        self._ensure_token()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": self.api_key,
            "Accept": "application/json"
        }
        rs_endpoint = f"https://analytics.adobe.io/api/{self.global_company_id}/collections/suites"
        final_result = None
        page = 0
        while True:
            try:
                params = {"limit": 50, "page": page}
                response = requests.get(rs_endpoint, headers=headers, params=params, proxies=self.proxies)
                logger.info(f"Get Report Suites request to {rs_endpoint} (page {page}) completed with status {response.status_code}.")
                response.raise_for_status()
                page_data = response.json()
                if final_result is None:
                    final_result = page_data
                else:
                    if "content" in page_data:
                        final_result["content"].extend(page_data.get("content", []))
                if page_data.get("lastPage", True):
                    break
                page += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to get report suites from Adobe API: {e}")
                if e.response is not None:
                    logger.error(f"Response status: {e.response.status_code}")
                    logger.error(f"Response body: {e.response.text}")
                    try:
                        return e.response.json()
                    except ValueError:
                        return {"error_code": "CLIENT_ERROR", "message": f"HTTP {e.response.status_code}: {e.response.text[:100]}"}
                return {"error_code": "NETWORK_ERROR", "message": str(e)}
        return final_result or {}

    def discover_me(self) -> Dict[str, Any]:
        """Calls the /discovery/me endpoint to get information about the user/service."""
        self._ensure_token()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": self.api_key,
            "Accept": "application/json"
        }
        discovery_endpoint = "https://analytics.adobe.io/discovery/me"
        try:
            response = requests.get(discovery_endpoint, headers=headers, proxies=self.proxies)
            logger.info(f"Discovery request to {discovery_endpoint} completed with status {response.status_code}.")
            logger.info(f"Discovery response preview: {response.text[:500]}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call discovery endpoint: {e}")
            if e.response is not None:
                try:
                    return e.response.json()
                except ValueError:
                    return {"error_code": "CLIENT_ERROR", "message": f"HTTP {e.response.status_code}: {e.response.text[:100]}"}
            return {"error_code": "NETWORK_ERROR", "message": str(e)}

    def _get_paginated_data(self, endpoint: str, params: Dict) -> Dict[str, Any]:
        """
        Generic helper to fetch data from a paginated Adobe API endpoint.
        
        Args:
            endpoint (str): The API endpoint URL.
            params (Dict): A dictionary of query parameters for the request.

        Returns:
            A dictionary containing the consolidated content from all pages.
        """
        self._ensure_token()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": self.api_key,
            "Accept": "application/json"
        }
        
        final_result = None
        page = 0
        limit = 200 # Fetch a larger number per page
        
        while True:
            request_params = params.copy()
            request_params.update({"limit": limit, "page": page})
            
            try:
                response = requests.get(endpoint, headers=headers, params=request_params, proxies=self.proxies)
                logger.info(f"Request to {endpoint} (page {page}) completed with status {response.status_code}.")
                response.raise_for_status()
                page_data = response.json()

                # Hotfix: Some Adobe APIs might return a raw list instead of a paginated object.
                # If so, wrap it in a dictionary to match the expected structure.
                if isinstance(page_data, list):
                    page_data = {"content": page_data, "lastPage": True}

                if final_result is None:
                    final_result = page_data
                elif "content" in page_data:
                    final_result.setdefault("content", []).extend(page_data.get("content", []))
                
                if page_data.get("lastPage", True):
                    break
                page += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed during paginated request to {endpoint}: {e}")
                if e.response is not None:
                    logger.error(f"Response status: {e.response.status_code}")
                    logger.error(f"Response body: {e.response.text}")
                # Re-raise to let the calling function handle it
                raise
        return final_result or {}

    def get_dimensions(self, rsid: str) -> Dict[str, Any]:
        """Retrieves all available dimensions for a given report suite."""
        endpoint = f"{self.api_base_url}/dimensions"
        params = {"rsid": rsid}
        logger.info(f"Fetching dimensions for RSID: {rsid}")
        return self._get_paginated_data(endpoint, params)

    def get_metrics(self, rsid: str) -> Dict[str, Any]:
        """Retrieves all available metrics for a given report suite."""
        endpoint = f"{self.api_base_url}/metrics"
        params = {"rsid": rsid}
        logger.info(f"Fetching metrics for RSID: {rsid}")
        return self._get_paginated_data(endpoint, params)

    def get_segments(self) -> Dict[str, Any]:
        """
        Retrieves all available segments. Note: Segments can be filtered by RSID,
        but we fetch all available to the user as they are often shared.
        """
        endpoint = f"{self.api_base_url}/segments"
        params = {"includeType": "all", "expansion": "definition"}
        logger.info("Fetching all available segments.")
        return self._get_paginated_data(endpoint, params)

    def get_segment_definition(self, segment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the full definition of a single segment by its ID."""
        self._ensure_token()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": self.api_key,
            "Accept": "application/json"
        }
        endpoint = f"{self.api_base_url}/segments/{segment_id}"
        params = {"expansion": "definition"}
        try:
            logger.info(f"Fetching definition for segment ID: {segment_id}")
            response = requests.get(endpoint, headers=headers, params=params, proxies=self.proxies)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get definition for segment {segment_id}: {e}")
            if e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None

    def get_adobe_dashboard_components(self, rsid: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Retrieves dimensions, metrics, and segments for the Adobe dashboard,
        utilizing a cache to improve performance.
        
        Args:
            rsid (str): The report suite ID.
            force_refresh (bool): If True, bypasses the cache and fetches fresh data from the API.

        Returns:
            A dictionary containing dimensions, metrics, and segments, or an error message.
        """
        # Step 1: Check cache first, unless a refresh is forced
        if not force_refresh:
            cached_components = load_adobe_components(rsid)
            if cached_components:
                logger.info(f"Loaded Adobe components for RSID '{rsid}' from cache.")
                # Ensure the format matches what the frontend expects
                return {
                    "dimensions": cached_components.get('dimensions', []),
                    "metrics": cached_components.get('metrics', []),
                    "segments": cached_components.get('segments', [])
                }

        logger.info(f"Cache miss or force refresh for RSID '{rsid}'. Fetching from Adobe API.")
        
        try:
            # Step 2: Fetch from API if cache is missed or refresh is forced
            dimensions_data = self.get_dimensions(rsid)
            metrics_data = self.get_metrics(rsid)
            segments_data = self.get_segments()

            # Step 3: Filter dimensions as per existing logic
            filtered_dimensions = []
            if dimensions_data and 'content' in dimensions_data:
                for dim in dimensions_data.get('content', []):
                    if not ('instance' in dim.get('name', '').lower() or \
                            'entry' in dim.get('name', '').lower() or \
                            'exit' in dim.get('name', '').lower()):
                        if dim.get('id', '').startswith(('variables/prop', 'variables/evar')):
                            filtered_dimensions.append(dim)
            
            logger.info(f"Filtered dimensions: from {len(dimensions_data.get('content', []))} to {len(filtered_dimensions)}.")

            # Step 4: Assemble the final components object
            final_components = {
                "dimensions": filtered_dimensions,
                "metrics": metrics_data.get('content', []),
                "segments": segments_data.get('content', [])
            }

            # Step 5: Save the newly fetched data to the cache
            save_adobe_components(rsid, final_components)
            logger.info(f"Saved fresh Adobe components for RSID '{rsid}' to cache.")

            return final_components

        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred while fetching Adobe components for dashboard: {e}")
            return {"error": str(e), "dimensions": [], "metrics": [], "segments": []}
