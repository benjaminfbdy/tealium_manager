# Documentation du Projet Tealium Manager

## [Sprint 1] - Initialisation du Projet & Panneau de Configuration

**👔 Vue Métier** :
Ce sprint a permis de mettre en place les fondations de l'application "Tealium Manager". L'utilisateur peut désormais lancer l'application et accéder à un panneau de configuration initial. Ce panneau valide la capacité de l'application à charger les identifiants Tealium de manière sécurisée (via un fichier `.env`) et à établir une connexion de base avec l'API Tealium. Bien qu'il n'y ait pas encore de fonctionnalités de management avancées, cette étape assure que l'application est prête à interagir avec les API Tealium.

**⚙️ Vue Technique** :
*   **Choix d'architecture** : Adoption d'une architecture MVC simplifiée pour une application Streamlit.
    *   `main.py` agit comme le point d'entrée et gère la navigation via `st.session_state`.
    *   Le dossier `views/` contient les composants UI (ex: `config_view.py`).
    *   Le dossier `controllers/` contient la logique métier liant vues et modèles (ex: `config_controller.py`).
    *   Le dossier `utils/` contient les utilitaires comme le wrapper API (`tealium_client.py`).
*   **Modules créés** :
    *   **Structure de dossiers** : `utils`, `views`, `controllers` ont été créés.
    *   `main.py` : Fichier principal de l'application Streamlit, intégrant la navigation et le panneau de configuration.
    *   `requirements.txt` : Liste des dépendances Python (`streamlit`, `python-dotenv`, `requests`).
    *   `.env` : Fichier pour la gestion sécurisée des variables d'environnement (credentials Tealium), ajouté au `.gitignore`.
    *   `utils/tealium_client.py` : Classe `TealiumClient` pour encapsuler l'accès à l'API Tealium. Inclut le chargement des credentials via `python-dotenv` et une méthode d'authentification initiale (API v2).
    *   `views/config_view.py` : Composant Streamlit pour afficher l'état de la connexion Tealium.
    *   `controllers/config_controller.py` : Logique pour vérifier la connexion à l'API Tealium et instancier `TealiumClient`.
*   **Dette technique restante** :
    *   Le `TealiumClient` est encore basique et ne gère que l'authentification V2. Il faudra étendre la gestion de l'API V3 et ajouter des méthodes pour les endpoints spécifiques (profils, révisions, publication).
    *   La gestion des erreurs dans le `TealiumClient` est rudimentaire (simple print), nécessitant une implémentation plus robuste (logging, exceptions spécifiques).
    *   Le panneau de configuration n'offre pas pas encore la possibilité de modifier les credentials directement via l'UI, ni de tester la connexion avec de nouvelles valeurs.
    *   L'application ne gère pas encore les états de chargement ou les messages d'erreur détaillés pour l'utilisateur final.

## [Sprint 2] - Persistance des Identifiants & Configuration In-App

**👔 Vue Métier** :
Ce sprint a introduit une amélioration majeure de l'expérience utilisateur en permettant la configuration des identifiants Tealium directement depuis l'application, via un panneau dédié. Plus important encore, ces identifiants sont désormais stockés de manière persistante dans une base de données locale, éliminant ainsi le besoin de les re-saisir à chaque démarrage de l'application. L'utilisateur peut sauvegarder ses identifiants et tester immédiatement la connexion, recevant un feedback visuel sur le succès ou l'échec.

**⚙️ Vue Technique** :
*   **Choix d'architecture** : Introduction d'une couche de persistance simple avec SQLite. Le fichier `database.py` a été créé pour encapsuler les opérations CRUD (Create, Read, Update, Delete) sur les identifiants.
*   **Modules modifiés/créés** :
    *   `database.py` : **Nouveau fichier**. Gère la base de données SQLite (`tealium_config.db`) pour le stockage des identifiants Tealium (`account`, `profile`, `api_key`, `email`). Inclut des fonctions `init_db`, `save_credentials`, et `load_credentials`.
    *   `tealium_config.db` : Le fichier de base de données SQLite créé par `database.py`, ajouté au `.gitignore`.
    *   `utils/tealium_client.py` : La classe `TealiumClient` a été refactorisée pour :
        *   Accepter des identifiants directement dans son constructeur.
        *   Tenter de charger les identifiants depuis `database.py` si non fournis.
        *   Conserver un fallback de chargement depuis `.env` pour la flexibilité (développement, autres secrets non user-editable).
    *   `views/config_view.py` : La fonction `render_config_panel` a été étendue pour :
        *   Afficher des champs de saisie pour l'account, le profile, l'API Key et l'email.
        *   Pré-remplir ces champs avec les identifiants chargés depuis la base de données.
        *   Inclure un bouton "Sauvegarder et Tester la Connexion" qui soumet les valeurs saisies.
    *   `controllers/config_controller.py` : Ce contrôleur a été mis à jour pour :
        *   Charger les identifiants actuels (`get_current_credentials`).
        *   Gérer la soumission du formulaire (`handle_config_submission`) en sauvegardant les nouvelles valeurs dans la DB et en re-testant la connexion.
        *   `get_tealium_connection_status` peut maintenant prendre des identifiants en paramètre pour tester une connexion spécifique.
    *   `main.py` : Le fichier principal a été modifié pour orchestrer la logique de configuration :
        *   Chargement des identifiants existants au démarrage de la page de configuration.
        *   Passage des identifiants à la vue pour pré-remplissage.
        *   Gestion de la soumission du formulaire et appel de `handle_config_submission`.
        *   Utilisation de `st.rerun()` (suite à la dépréciation de `st.experimental_rerun()`) pour rafraîchir l'interface après une sauvegarde.
*   **Dette technique restante** :
    *   **Sécurité des credentials** : Les identifiants sont stockés en clair dans la base SQLite locale. Pour une application de production, un chiffrement des données sensibles serait impératif.
    *   Le `TealiumClient` nécessite toujours l'extension pour l'API V3 et les endpoints spécifiques.
    *   Gestion plus robuste des erreurs et des messages utilisateur (ex: messages spécifiques lors de l'échec de sauvegarde).
    *   Pas encore de gestion des profils multiples ou de commutation entre identifiants.

## [Sprint 3] - Gestion Multi-Comptes/Profils

**👔 Vue Métier** :
Ce sprint a introduit une capacité essentielle : la gestion de multiples configurations de comptes et profils Tealium. Les utilisateurs peuvent désormais sauvegarder, sélectionner, éditer, définir comme active et supprimer différentes configurations d'accès à l'API. Cela offre une flexibilité considérable pour travailler avec divers environnements (développement, staging, production) ou différents clients sans avoir à saisir manuellement les identifiants à chaque fois. Une configuration peut être désignée comme "active", et c'est celle-ci qui sera utilisée par défaut pour les opérations de l'application.

**⚙️ Vue Technique** :
*   **Choix d'architecture** : Extension de la couche de persistance SQLite pour supporter plusieurs enregistrements de configuration.
*   **Modules modifiés** :
    *   `database.py` : Le fichier a été entièrement refactorisé pour gérer des collections de configurations nommées.
        *   La table `config` a été renommée `configurations` et a été augmentée avec une colonne `name` (TEXT UNIQUE NOT NULL) pour identifier chaque configuration et une colonne `is_active` (INTEGER DEFAULT 0) pour marquer la configuration actuellement sélectionnée.
        *   Les fonctions existantes (`save_credentials`, `load_credentials`) ont été remplacées ou augmentées par `save_configuration`, `load_all_configurations`, `get_active_configuration`, `set_active_configuration`, et `delete_configuration`.
    *   `utils/tealium_client.py` : La classe `TealiumClient` a été mise à jour pour charger ses identifiants depuis la configuration `active` de la base de données via `get_active_configuration()`, tout en conservant la possibilité d'être initialisée avec des identifiants passés directement en paramètres.
    *   `views/config_view.py` : La fonction `render_config_panel` a été entièrement refactorisée pour prendre en charge la gestion multi-configurations :
        *   Affichage d'une liste déroulante (`st.selectbox`) pour sélectionner une configuration existante.
        *   Présentation des détails de la configuration sélectionnée dans des champs de saisie éditables.
        *   Boutons pour "Mettre à Jour et Tester", "Définir comme Active" et "Supprimer" une configuration.
        *   Une section dédiée pour "Ajouter une Nouvelle Configuration" avec un champ de nom unique.
        *   La fonction retourne maintenant un dictionnaire décrivant l'action effectuée par l'utilisateur (par exemple, "add_new", "update", "set_active", "delete") et les données pertinentes.
    *   `controllers/config_controller.py` : Le contrôleur a été mis à jour pour :
        *   Importer les nouvelles fonctions de `database.py`.
        *   Fournir des fonctions pour récupérer toutes les configurations (`get_all_configurations`), les détails de la configuration active (`get_active_configuration_details`).
        *   Implémenter des gestionnaires spécifiques pour chaque action utilisateur de la vue (`handle_add_new_config`, `handle_update_config`, `handle_set_active_config`, `handle_delete_config`).
        *   La fonction `get_tealium_connection_status` a été adaptée pour utiliser la configuration active ou une configuration spécifiée.
    *   `main.py` : Le script principal a été mis à jour pour orchestrer la nouvelle logique :
        *   Chargement de toutes les configurations et de la configuration active au démarrage de la page de configuration.
        *   Passage de ces données à `render_config_panel`.
        *   Interprétation de l'action retournée par `render_config_panel` et appel des fonctions de gestion du contrôleur correspondantes.
        *   Utilisation de `st.rerun()` après chaque action pour rafraîchir l'interface utilisateur.
*   **Dette technique restante** :
    *   **Sécurité des credentials** : Les identifiants sont stockés en clair dans la base SQLite locale. Pour une application de production, un chiffrement des données sensibles serait impératif.
    *   Le `TealiumClient` nécessite toujours l'extension pour l'API V3 (au-delà de l'authentification) et l'intégration de ses endpoints spécifiques (par exemple, la gestion du `host` régionaux).
    *   Gestion plus robuste des erreurs et messages utilisateur pour toutes les opérations (par exemple, messages d'erreur spécifiques si le nom d'une configuration existe déjà).
    *   Amélioration de l'UX pour la suppression (confirmation).

## [Sprint 4] - Explorateur de Composants de Profil

**👔 Vue Métier** :
Ce sprint a introduit la capacité d'explorer les différents composants d'un profil Tealium iQ (variables, tags, load rules, extensions, événements) directement depuis l'application. Cela permet aux utilisateurs de visualiser rapidement le contenu d'un profil actif sans avoir à se connecter à l'interface web de Tealium. C'est un pas important vers la gestion et la compréhension facilitée des configurations Tealium.

**⚙️ Vue Technique** :
*   **Choix d'architecture** : Extension du modèle MVC pour inclure une nouvelle vue et un nouveau contrôleur dédiés à l'exploration des profils.
*   **Modules créés/modifiés** :
    *   `utils/tealium_client.py` : Ajout de la méthode `get_profile_components` qui utilise l'API Tealium V3 (`/v3/tiq/accounts/{ACCOUNT}/profiles/{PROFILE}?includes=...`) pour récupérer les données structurées d'un profil.
    *   `views/profile_explorer_view.py` : **Nouveau fichier**. Contient la fonction `render_profile_explorer` qui affiche les données de profil récupérées. L'affichage est structuré en sections (utilisant `st.expander` ou `st.json` pour la visualisation) pour chaque type de composant (variables, tags, etc.).
    *   `controllers/profile_controller.py` : **Nouveau fichier**. Contient la fonction `get_profile_data` qui orchestre l'appel au `TealiumClient` pour récupérer les données du profil actif et les prépare pour la vue. Il gère également l'initialisation du `TealiumClient` avec la configuration active.
    *   `main.py` : Intégration de la nouvelle fonctionnalité :
        *   Ajout d'un bouton 'Explorateur de Profil' dans la barre latérale de navigation.
        *   Un nouveau bloc `elif st.session_state.page == "profile_explorer"` a été ajouté pour :
            *   Récupérer la configuration Tealium active.
            *   Appeler `get_profile_data()` pour obtenir les informations du profil.
            *   Afficher ces informations en utilisant `render_profile_explorer()`.
            *   Gérer les cas où aucune configuration active n'est définie ou si le chargement du profil échoue.
*   **Dette technique restante** :
    *   **Sécurité des credentials** : Toujours stockés en clair dans SQLite, le chiffrement est un prérequis pour la production.
    *   Amélioration de l'interface utilisateur de l'explorateur : Actuellement, `st.json` est utilisé pour les détails des composants, ce qui peut être trop brut. Il faudra développer des affichages plus 'beautified' et spécifiques à chaque type de composant (tableaux pour les listes, cartes pour les détails, etc.).
    *   Le `TealiumClient` doit être étendu pour gérer d'autres endpoints de l'API V3 (au-delà de l'authentification et de la récupération des profils) et de l'API V2 (pour les révisions par exemple), y compris la gestion du `host` spécifique à la région pour l'API V3.
    *   Implémenter la fonctionnalité de comparaison des révisions.
    *   Gestion plus granulaire des erreurs et des messages de feedback utilisateur (par exemple, pour indiquer pourquoi un composant est manquant).
    *   Ajout de la fonctionnalité de filtre/recherche dans l'explorateur de profils.

## [Sprint 5] - Historique des Révisions & Comparaison

**👔 Vue Métier** :
Ce sprint a permis d'implémenter l'accès à l'historique des révisions d'un profil Tealium iQ. Les utilisateurs peuvent désormais visualiser la liste des révisions, ainsi que leurs détails, directement depuis l'application. La fonctionnalité de comparaison rudimentaire entre deux versions a également été mise en place, offrant une première approche pour identifier les changements.

**⚙️ Vue Technique** :
*   **Choix d'architecture** : Extension du `TealiumClient` pour interagir avec les endpoints de l'API V2 dédiés aux révisions. Introduction d'une nouvelle vue et d'un nouveau contrôleur pour gérer l'affichage et la logique de l'historique.
*   **Modules créés/modifiés** :
    *   `utils/tealium_client.py` : Ajout de deux nouvelles méthodes :
        *   `get_revision_ids()` : Récupère la liste des identifiants de révision pour le profil actif (`GET /v2/manifest/accounts/{account}/profiles/{profile}/revisions`).
        *   `get_revision_details(revision_id)` : Récupère les détails complets d'une révision spécifique (`GET /v2/manifest/accounts/{account}/profiles/{profile}/revisions/{revision_id}/details`).
    *   `views/revision_history_view.py` : **Nouveau fichier**. Contient la fonction `render_revision_history` qui :
        *   Affiche la liste des révisions dans un `st.dataframe`.
        *   Propose deux `st.selectbox` pour sélectionner les révisions à comparer.
        *   Affiche les détails des révisions sélectionnées côte à côte (actuellement via `st.json`).
        *   Contient un placeholder pour une logique de comparaison plus avancée (`compare_revision_details`).
    *   `controllers/revision_controller.py` : **Nouveau fichier**. Contient les fonctions :
        *   `get_revisions_data()` : Orchestre l'appel au `TealiumClient` pour récupérer tous les IDs de révision, puis leurs détails complets.
        *   `compare_revisions(rev_id_1, rev_id_2)` : Récupère les détails de deux révisions spécifiques pour une future comparaison.
    *   `main.py` : Intégration de la nouvelle fonctionnalité :
        *   Ajout d'un bouton 'Historique des Révisions' dans la barre latérale de navigation.
        *   Un nouveau bloc `elif st.session_state.page == "revision_history"` a été ajouté pour :
            *   Récupérer la configuration Tealium active.
            *   Appeler `get_revisions_data()` pour obtenir l'historique complet.
            *   Afficher cet historique en utilisant `render_revision_history()`.
            *   Gérer les cas où aucune configuration active n'est définie ou si l'historique ne peut être chargé.
*   **Dette technique restante** :
    *   **Sécurité des credentials** : Les identifiants sont stockés en clair dans la base SQLite locale. Le chiffrement reste un prérequis pour une utilisation en production.
    *   **Comparaison de versions** : La fonction de comparaison est actuellement très basique (affichage JSON côte à côte). Il est nécessaire d'implémenter une logique de différenciation visuelle et sémantique plus avancée (par exemple, mise en évidence des ajouts/suppressions/modifications).
    *   **Amélioration UI/UX** : L'affichage des détails des révisions et des composants pourrait être amélioré pour être plus 'beautified' et moins brut que du JSON.
    *   **TealiumClient** : Intégration complète de l'API V3 pour les appels autres que le chargement de profil, notamment la gestion du `host` spécifique à la région renvoyé par l'authentification V3.
    *   Filtrage et pagination pour l'historique des révisions si le volume est très important.
    *   Messages d'erreur plus conviviaux pour l'utilisateur final.

## [Sprint 6] - Cache de Données API & Amélioration UX

**👔 Vue Métier** :
Pour améliorer drastiquement la réactivité de l'application, ce sprint introduit un système de cache pour les données récupérées depuis l'API Tealium. Désormais, les informations telles que les composants de profil et l'historique des révisions sont stockées localement après le premier chargement. Les accès ultérieurs à ces données sont quasi instantanés, éliminant les temps d'attente répétés. De plus, des barres de progression ont été ajoutées lors des appels API initiaux pour fournir un retour visuel clair à l'utilisateur et améliorer l'expérience globale.

**⚙️ Vue Technique** :
*   **Choix d'architecture** : Le module `database.py` a été étendu pour inclure une table `api_cache` dédiée au stockage des réponses API. Cette table utilise un système clé-valeur avec un timestamp pour gérer la fraîcheur des données (TTL - Time-To-Live). La logique de récupération de données dans les contrôleurs a été mise à jour pour suivre un schéma "cache-then-network".
*   **Modules modifiés** :
    *   `database.py` :
        *   Création de la table `api_cache` avec les colonnes `cache_key`, `data`, `timestamp`, et `etag`.
        *   Ajout des fonctions `get_cached_data(key, ttl)` et `set_cached_data(key, data)` pour interagir avec le cache.
        *   Correction et consolidation des fonctions de gestion de configuration pour coexister avec le système de cache dans le même fichier de base de données (`tealium_manager.db`).
    *   `controllers/profile_controller.py` :
        *   La fonction `get_profile_data` vérifie maintenant d'abord si les données du profil sont dans le cache.
        *   Si les données ne sont pas en cache ou sont expirées, un appel API est effectué.
        *   Les nouvelles données sont ensuite stockées dans le cache pour les futurs accès.
        *   Une barre de progression `st.progress` est affichée pendant le chargement initial depuis l'API.
    *   `controllers/revision_controller.py` :
        *   Logique de mise en cache similaire appliquée à `get_revisions_data`.
        *   La liste des IDs de révision est mise en cache avec un TTL court.
        *   Les détails de chaque révision individuelle sont mis en cache avec un TTL plus long, accélérant à la fois l'affichage initial et les comparaisons futures.
        *   Une barre de progression informe l'utilisateur du chargement des détails de chaque révision.
    *   `main.py` : Correction d'un bug mineur (`st.session_session` remplacé par `st.session_state`) pour assurer une navigation fiable.
    *   `.gitignore` : Mise à jour pour ignorer tous les fichiers de base de données (`*.db`) plutôt que des noms spécifiques.
*   **Dette technique restante** :
    *   **Gestion du ETag** : Le champ `etag` est présent dans la table de cache mais n'est pas encore utilisé pour des requêtes conditionnelles (If-None-Match), ce qui pourrait encore optimiser l'utilisation de l'API.
    *   **Invalidation du cache** : Aucune stratégie d'invalidation manuelle du cache n'est implémentée. Un bouton "Forcer le rafraîchissement" pourrait être utile pour l'utilisateur.
    *   **Comparaison de versions** : La logique de différenciation reste un placeholder et doit être implémentée.
    *   **Sécurité** : Les secrets et les données en cache (qui peuvent contenir des informations de configuration) sont toujours stockés en clair.

## [Sprint 7] - Améliorations Visuelles & Stabilité

**👔 Vue Métier** :
Ce sprint s'est concentré sur la stabilisation et l'amélioration de l'expérience visuelle de l'application. L'interface a été entièrement relookée avec des couleurs personnalisées et une icône d'application, la rendant plus professionnelle et alignée avec une identité de marque. En parallèle, des bugs critiques liés à l'exécution de l'application ont été résolus, assurant que l'utilisateur dispose d'une base stable et fiable pour les futures fonctionnalités.

**⚙️ Vue Technique** :
*   **Stabilité de l'application** :
    *   Résolution de plusieurs bugs bloquants (`NameError`, `AttributeError`) qui empêchaient l'application de fonctionner.
    *   Mise en place d'un processus de redémarrage propre du serveur Streamlit pour s'assurer que les modifications du code sont bien prises en compte, en corrigeant les problèmes de `PATH` et en utilisant `python -m streamlit run` pour plus de robustesse.
*   **Refonte Visuelle** :
    *   `main.py` a été modifié pour injecter un bloc de CSS personnalisé via `st.markdown(..., unsafe_allow_html=True)`.
    *   **Icône d'application** : L'icône de page (favicon) a été définie sur celle de Tealium via `st.set_page_config`.
    *   **Palette de couleurs** :
        *   Barre latérale : Fond (`#051838`), Police (`white`).
        *   Header : Un header personnalisé a été créé avec un fond (`#118aaf`) et une police (`white`).
        *   Police générale : La police par défaut du corps de l'application a été définie sur `#545f70`.
    *   Le titre par défaut de Streamlit a été remplacé par un header HTML personnalisé pour un contrôle total du style.
*   **Dette technique restante** :
    *   Le CSS est injecté directement dans `main.py`. Pour une application plus grande, il serait préférable de le déplacer dans un fichier `.css` séparé et de le charger, bien que Streamlit ne supporte pas cela nativement de manière simple.

## [Sprint 8] - Gestion de la Base de Données

**👔 Vue Métier** :
Pour donner à l'utilisateur plus de contrôle et de visibilité sur l'application, une fonctionnalité de gestion de la base de données a été ajoutée. Directement depuis la barre latérale, l'utilisateur peut maintenant consulter l'état de la base de données locale (sa taille, le nombre de configurations sauvegardées, le nombre d'éléments en cache) et, si nécessaire, la réinitialiser complètement. Cette fonction de "reset" est sécurisée par une double confirmation pour prévenir toute suppression accidentelle.

**⚙️ Vue Technique** :
*   **Choix d'architecture** : La fonctionnalité a été implémentée en suivant le pattern MVC existant.
*   **Modules modifiés** :
    *   `database.py` :
        *   Ajout des imports `os` et `datetime`.
        *   **Nouvelle fonction `get_db_status()`** : Renvoie un dictionnaire contenant des statistiques sur le fichier de BDD (taille, date de modification) et son contenu (nombre de configurations, nombre d'objets en cache).
        *   **Nouvelle fonction `reset_database()`** : Supprime le fichier de BDD (`os.remove`) et appelle `initialize_database()` pour en recréer une nouvelle, vierge.
    *   `controllers/config_controller.py` :
        *   Ajout des fonctions `get_database_status()` et `handle_database_reset()` qui agissent comme des wrappers pour les nouvelles fonctions du module `database`.
    *   `main.py` :
        *   Import des nouvelles fonctions du contrôleur.
        *   Ajout d'une section `st.sidebar.expander("Gestion Base de Données")` dans la barre latérale.
        *   À l'intérieur de l'expander, les informations de `get_database_status()` sont affichées de manière formatée.
        *   Implémentation d'un processus de réinitialisation sécurisé en deux étapes à l'aide de `st.session_state` et de boutons de confirmation/annulation, prévenant les actions destructrices accidentelles.
*   **Dette technique restante** :
    *   Le formatage de la taille du fichier est basique.
    *   La fonction de reset est globale. Des options plus granulaires (vider le cache uniquement, supprimer une seule configuration, etc.) pourraient être envisagées à l'avenir.
    *   La sécurité des données stockées en clair reste une préoccupation majeure.