import requests
import io
import zipfile
import json
import re
import time

class TealiumClient:
    """
    Client pour interagir avec les APIs Tealium V2 et V3.
    """
    def __init__(self, username, api_key):
        """
        Initialise le client, stocke les identifiants.
        """
        if not username or not api_key:
            raise ValueError("Le nom d'utilisateur et la clé API sont requis.")

        self.base_url_v2 = "https://api.tealiumiq.com/v2"
        self.base_url_v3 = "https://platform.tealiumapis.com/v3"
        self.session = requests.Session()
        self.api_username = username
        self.api_key = api_key

        self.v2_token = None
        self.v3_token = None
        self.v3_token_expiry = 0
        self.v3_host = None

        self._authenticate_v2()

    def _authenticate_v2(self):
        """
        S'authentifie à l'API V2 pour obtenir un token Bearer.
        """
        if self.v2_token:
            return # Déjà authentifié

        auth_url = f"{self.base_url_v2}/auth"
        payload = {'username': self.api_username, 'key': self.api_key}
        try:
            response = self.session.post(auth_url, data=payload)
            response.raise_for_status()
            self.v2_token = response.json().get("token")
            if not self.v2_token:
                raise ValueError("La réponse de l'API d'authentification V2 ne contient pas de token.")
            # N'ajoute le token que pour les appels V2 qui en ont besoin.
            # self.session.headers.update({"Authorization": f"Bearer {self.v2_token}"})
            print("INFO: Authentification V2 (Bearer Token) réussie.")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Échec de l'authentification V2 : {e}")

    def get_accounts(self) -> list:
        """
        Récupère la liste des comptes accessibles via l'API V2.
        """
        accounts_url = f"{self.base_url_v2}/accounts"
        headers = {"Authorization": f"Bearer {self.v2_token}"}
        try:
            response = self.session.get(accounts_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"ERREUR: Impossible de récupérer les comptes. {e}")
            return []

    def _authenticate_v3(self, account, profile):
        """
        S'authentifie à l'API V3 pour obtenir un token JWT et un hôte régional.
        Réutilise le token s'il est encore valide.
        """
        if self.v3_token and time.time() < self.v3_token_expiry:
            print("INFO: Utilisation du token V3 existant.")
            return

        auth_url = f"{self.base_url_v3}/auth/accounts/{account}/profiles/{profile}"
        payload = {'username': self.api_username, 'key': self.api_key}
        try:
            print("INFO: Demande d'un nouveau token d'authentification V3.")
            response = requests.post(auth_url, data=payload)
            response.raise_for_status()
            auth_data = response.json()
            self.v3_token = auth_data.get("token")
            self.v3_host = auth_data.get("host")
            if not self.v3_token or not self.v3_host:
                raise ValueError("La réponse de l'API d'authentification V3 ne contient pas de token ou d'hôte.")
            
            # Le token expire en 30 minutes, on prend une marge de sécurité de 1 minute.
            self.v3_token_expiry = time.time() + (29 * 60)
            print(f"INFO: Authentification V3 réussie. Hôte régional : {self.v3_host}")

        except requests.exceptions.RequestException as e:
            error_details = e.response.text if e.response else str(e)
            raise ValueError(f"Échec de l'authentification V3 pour {account}/{profile}: {e} - {error_details}")

    def get_profiles(self, account: str) -> list:
        """
        Récupère la liste des profils pour un compte en utilisant l'authentification directe par clé API V2.
        """
        # Cette méthode V2 n'utilise pas le token Bearer mais une clé directe.
        profiles_url = f"{self.base_url_v2}/accounts/{account}/profiles"
        headers = {"Tealium-Api-Key": self.api_key}
        try:
            response = requests.get(profiles_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"ERREUR: Impossible de récupérer les profils pour le compte '{account}'. {e}")
            return []

    def get_revisions(self, account, profile):
        """
        Récupère la liste des révisions via l'API V2 manifest (token V2).
        """
        revisions_url = f"{self.base_url_v2}/manifest/accounts/{account}/profiles/{profile}/revisions"
        headers = {"Authorization": f"Bearer {self.v2_token}"}
        try:
            response = self.session.get(revisions_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"ERREUR: Impossible de récupérer les révisions pour '{account}/{profile}'. {e}")
            return []
    
    def get_revision_details(self, account, profile, revision_id):
        """
        Récupère les métadonnées d'une révision via l'API V2 manifest (token V2).
        """
        details_url = f"{self.base_url_v2}/manifest/accounts/{account}/profiles/{profile}/revisions/{revision_id}/details"
        headers = {"Authorization": f"Bearer {self.v2_token}"}
        try:
            response = self.session.get(details_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = f"Impossible de récupérer les détails pour la révision '{revision_id}'. Détails : {e}"
            print(f"ERREUR: {error_msg}")
            return {"error": error_msg}

    def get_profile_configuration_v3(self, account, profile, revision_id):
        """
        Récupère la configuration complète d'une révision spécifique via l'API V3.
        """
        try:
            self._authenticate_v3(account, profile)
        except ValueError as e:
            return {"error": str(e)}

        includes = [
            "variables", "tags", "loadRules", "extensions", "events", 
            "versionIds", "tags.template"
        ]
        
        params = [("includes", item) for item in includes]
        params.append(("publishVersion", revision_id))

        config_url = f"https://{self.v3_host}/v3/tiq/accounts/{account}/profiles/{profile}"
        
        headers = {"Authorization": f"Bearer {self.v3_token}"}

        print(f"INFO: Appel de l'API V3 pour la configuration de la révision {revision_id}.")
        try:
            response = requests.get(config_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_details = e.response.text if e.response else str(e)
            error_msg = f"Impossible de récupérer la configuration V3 pour la révision '{revision_id}'. Détails : {e} - {error_details}"
            print(f"ERREUR: {error_msg}")
            return {"error": error_msg}


    def get_revision_configuration(self, account, profile, revision_id):
        """
        Récupère la configuration complète d'une révision en utilisant l'API V3.
        C'est la méthode à privilégier.
        """
        print(f"INFO: Lancement de la récupération de la configuration via l'API V3 pour la révision {revision_id}.")
        
        config = self.get_profile_configuration_v3(account, profile, revision_id)

        if not config or 'error' in config:
            error_msg = f"Erreur de l'API lors du chargement de la configuration : {config.get('error', 'Erreur inconnue')}"
            print(f"ERREUR: {error_msg}")
            return {"error": error_msg}
        
        # Le bundle n'est plus nécessaire pour la configuration, mais on peut le garder pour d'autres usages.
        # Pour l'instant, on se concentre sur la configuration V3.
        # On pourrait vouloir extraire le code JS d'une extension spécifique par exemple.
        # bundle = self.get_revision_bundle(account, profile, revision_id)
        
        print("INFO: Configuration V3 récupérée avec succès.")
        return config


    def get_revision_bundle(self, account, profile, revision_id, environment="prod"):
        """
        Télécharge le bundle d'une révision, l'extrait en mémoire,
        et retourne un dictionnaire des fichiers contenus (nom: contenu).
        NOTE : Cette fonction est moins utilisée maintenant que la config est via V3.
        """
        bundle_url = f"{self.base_url_v2}/manifest/accounts/{account}/profiles/{profile}/revisions/{revision_id}/environments/{environment}"
        headers = {"Authorization": f"Bearer {self.v2_token}"}
        print(f"INFO: Téléchargement du bundle de la révision (V2): {bundle_url}")
        
        try:
            response = self.session.get(bundle_url, headers=headers)
            response.raise_for_status()
            
            bundle_files = {}
            with io.BytesIO(response.content) as zip_buffer:
                with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                    for file_info in zip_file.infolist():
                        with zip_file.open(file_info) as file:
                            try:
                                bundle_files[file_info.filename] = file.read().decode('utf-8')
                            except UnicodeDecodeError:
                                # Pour les fichiers non-texte comme les images ou binaires
                                bundle_files[file_info.filename] = file.read()
            
            print(f"INFO: Bundle extrait. {len(bundle_files)} fichiers trouvés.")
            return bundle_files

        except zipfile.BadZipFile:
            error_msg = "Le fichier téléchargé (bundle) n'est pas un zip valide."
            print(f"ERREUR: {error_msg}")
            return {"error": error_msg}
        except requests.exceptions.RequestException as e:
            error_msg = f"Impossible de télécharger le bundle pour la révision '{revision_id}'. Détails: {e}"
            print(f"ERREUR: {error_msg}")
            return {"error": error_msg}
