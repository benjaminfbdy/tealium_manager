import streamlit as st
import pandas as pd
import asyncio
import aiohttp
import logging
from typing import Dict, Optional, List, Coroutine

from utils.adobe_client import AdobeClient

logger = logging.getLogger(__name__)

USER_MANAGEMENT_SCOPE = "openid,AdobeID,user_management_sdk"
USER_MANAGEMENT_BASE_URL = "https://usermanagement.adobe.io/v2/usermanagement"

def _get_user_management_client(config: Dict) -> Optional[AdobeClient]:
    """
    Initializes and returns an AdobeClient configured for the User Management API
    using a provided configuration dictionary.
    """
    if not config:
        st.error("La configuration du profil Adobe est manquante.")
        return None
    
    if "organization_id" not in config:
        st.error("Le profil Adobe sélectionné ne contient pas d' 'organization_id', qui est requis pour l'API User Management.")
        st.info("Veuillez ajouter 'organization_id = \"VOTRE_ID_ORGANISATION\"' à votre profil dans secrets.toml.")
        return None

    try:
        client_config = config.copy()
        if "proxy" in st.secrets:
            client_config["proxy"] = st.secrets.proxy.to_dict()

        client_config['auth_method'] = 'oauth'
        client = AdobeClient(
            config=client_config, 
            scope=USER_MANAGEMENT_SCOPE, 
            api_base_url=USER_MANAGEMENT_BASE_URL,
            use_token_v2=True
        )
        return client
    except Exception as e:
        logger.error(f"Erreur lors de l'instanciation du client Adobe User Management : {e}")
        st.error(f"Erreur lors de la création du client API : {e}")
        return None

async def _get_users_for_organization_async(_config: Dict) -> List[Dict]:
    """
    Internal async function to fetch all users for a given Adobe configuration.
    """
    client = _get_user_management_client(_config)
    if not client:
        return []

    try:
        client._ensure_token()
    except Exception as e:
        logger.error(f"Échec de l'authentification OAuth auprès d'Adobe : {e}")
        st.error(f"Échec de l'authentification : {e}")
        st.info("Vérifiez vos credentials et les scopes du projet Adobe I/O.")
        return []

    all_users = []
    page = 0
    org_id = client.organization_id
    api_key = client.api_key
    access_token = client.access_token
    
    proxy_url = client.proxy_url_string
    connector = aiohttp.TCPConnector(ssl=client.verify_ssl)
    
    headers = {"Authorization": f"Bearer {access_token}", "x-api-key": api_key}

    async with aiohttp.ClientSession(headers=headers, proxy=proxy_url, connector=connector) as session:
        while True:
            url = f"{USER_MANAGEMENT_BASE_URL}/users/{org_id}/{page}"
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    users_on_page = data.get("users", [])
                    all_users.extend(users_on_page)
                    if data.get("lastPage"): break
                    page += 1
            except Exception as e:
                st.error(f"Erreur API Adobe lors de la récupération des utilisateurs: {e}")
                break
    
    return all_users

@st.cache_data(ttl=900)
def get_users_for_organization(config_tuple: tuple) -> List[Dict]:
    """
    Synchronous wrapper to fetch and cache users.
    Accepts a tuple representation of the config to make it hashable for the cache.
    """
    config = dict(config_tuple)
    logger.info(f"Chargement des utilisateurs pour l'organisation {config.get('organization_id')} depuis l'API (ou le cache).")
    return asyncio.run(_get_users_for_organization_async(config))


async def add_user(config: Dict, email: str, firstname: str, lastname: str, groups: List[str]) -> Dict:
    """
    Adds a new user to the Adobe organization and assigns them to product profiles (groups).
    """
    client = _get_user_management_client(config)
    if not client:
        return {"success": False, "error": "Impossible d'initialiser le client API."}

    try:
        client._ensure_token()
    except Exception as e:
        logger.error(f"Échec de l'authentification OAuth auprès d'Adobe : {e}")
        return {"success": False, "error": f"Échec de l'authentification : {e}"}

    org_id = client.organization_id
    api_key = client.api_key
    access_token = client.access_token

    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-api-key": api_key,
        "Content-type": "application/json"
    }

    # Construct the command payload
    payload = [{
        "user": email,
        "requestID": f"add_{email}",
        "do": [
            {
                "createAdobeID": {
                    "email": email,
                    "firstname": firstname,
                    "lastname": lastname,
                    "country": "FR", # Defaulting to FR, can be made a form field
                    "option": "updateIfAlreadyExists"
                }
            },
            {
                "add": {
                    "group": groups
                }
            }
        ]
    }]

    url = f"{USER_MANAGEMENT_BASE_URL}/action/{org_id}"
    
    proxy_url = client.proxy_url_string
    connector = aiohttp.TCPConnector(ssl=client.verify_ssl)
    async with aiohttp.ClientSession(headers=headers, proxy=proxy_url, connector=connector) as session:
        try:
            async with session.post(url, json=payload) as response:
                response_json = await response.json()
                if response.status >= 400:
                    logger.error(f"Erreur API Adobe lors de l'ajout de l'utilisateur : {response.status} - {response_json}")
                    error_message = response_json.get("errors", [{}])[0].get("message", "Erreur inconnue")
                    return {"success": False, "error": f"Erreur {response.status}: {error_message}"}
                
                if response_json.get("result") == "success":
                    logger.info(f"Utilisateur {email} ajouté avec succès.")
                    return {"success": True, "details": response_json}
                else:
                    logger.error(f"Erreur lors de l'ajout de l'utilisateur (résultat non-succès): {response_json}")
                    error_detail = response_json.get("errors", "Détail non fourni.")
                    return {"success": False, "error": f"Erreur de l'API : {error_detail}", "details": response_json}

        except aiohttp.ClientResponseError as e:
            logger.error(f"Erreur de connexion API Adobe lors de l'ajout de l'utilisateur : {e.status} {e.message}")
            return {"success": False, "error": f"Erreur de connexion : {e.status} - {e.message}"}
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'ajout de l'utilisateur : {e}")
            return {"success": False, "error": f"Erreur inattendue : {e}"}

async def delete_user(config: Dict, email: str) -> Dict:
    """
    Removes a user from the Adobe organization.
    """
    client = _get_user_management_client(config)
    if not client:
        return {"success": False, "error": "Impossible d'initialiser le client API."}

    try:
        client._ensure_token()
    except Exception as e:
        logger.error(f"Échec de l'authentification OAuth auprès d'Adobe : {e}")
        return {"success": False, "error": f"Échec de l'authentification : {e}"}

    org_id = client.organization_id
    api_key = client.api_key
    access_token = client.access_token

    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-api-key": api_key,
        "Content-type": "application/json"
    }

    # Construct the command payload for deletion
    payload = [{
        "user": email,
        "requestID": f"delete_{email}",
        "do": [
            {
                "removeFromOrg": {
                    "deleteAccount": True 
                }
            }
        ]
    }]

    url = f"{USER_MANAGEMENT_BASE_URL}/action/{org_id}"
    
    proxy_url = client.proxy_url_string
    connector = aiohttp.TCPConnector(ssl=client.verify_ssl)
    async with aiohttp.ClientSession(headers=headers, proxy=proxy_url, connector=connector) as session:
        try:
            async with session.post(url, json=payload) as response:
                response_json = await response.json()
                if response.status >= 400:
                    logger.error(f"Erreur API Adobe lors de la suppression de l'utilisateur : {response.status} - {response_json}")
                    error_message = response_json.get("errors", [{}])[0].get("message", "Erreur inconnue")
                    return {"success": False, "error": f"Erreur {response.status}: {error_message}"}

                if response_json.get("result") == "success":
                    logger.info(f"Utilisateur {email} supprimé avec succès.")
                    return {"success": True, "details": response_json}
                else:
                    logger.error(f"Erreur lors de la suppression (résultat non-succès): {response_json}")
                    error_detail = response_json.get("errors", "Détail non fourni.")
                    return {"success": False, "error": f"Erreur de l'API : {error_detail}", "details": response_json}

        except aiohttp.ClientResponseError as e:
            logger.error(f"Erreur de connexion API Adobe lors de la suppression : {e.status} {e.message}")
            return {"success": False, "error": f"Erreur de connexion : {e.status} - {e.message}"}
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la suppression : {e}")
            return {"success": False, "error": f"Erreur inattendue : {e}"}

async def update_user(config: Dict, email: str, commands: List[Dict]) -> Dict:
    """
    Updates a user in the Adobe organization using a list of commands.
    """
    if not commands:
        return {"success": True, "message": "Aucune modification détectée."}

    client = _get_user_management_client(config)
    if not client:
        return {"success": False, "error": "Impossible d'initialiser le client API."}

    try:
        client._ensure_token()
    except Exception as e:
        return {"success": False, "error": f"Échec de l'authentification : {e}"}

    org_id = client.organization_id
    api_key = client.api_key
    access_token = client.access_token

    headers = { "Authorization": f"Bearer {access_token}", "x-api-key": api_key, "Content-type": "application/json" }
    payload = [{"user": email, "requestID": f"update_{email}", "do": commands}]
    url = f"{USER_MANAGEMENT_BASE_URL}/action/{org_id}"

    proxy_url = client.proxy_url_string
    connector = aiohttp.TCPConnector(ssl=client.verify_ssl)
    async with aiohttp.ClientSession(headers=headers, proxy=proxy_url, connector=connector) as session:
        try:
            async with session.post(url, json=payload) as response:
                response_json = await response.json()
                if response.status >= 400:
                    error_message = response_json.get("errors", [{}])[0].get("message", "Erreur inconnue")
                    return {"success": False, "error": f"Erreur {response.status}: {error_message}"}

                if response_json.get("result") == "success":
                    return {"success": True, "details": response_json}
                else:
                    error_detail = response_json.get("errors", "Détail non fourni.")
                    return {"success": False, "error": f"Erreur de l'API : {error_detail}", "details": response_json}
        except Exception as e:
            return {"success": False, "error": f"Erreur inattendue : {e}"}
