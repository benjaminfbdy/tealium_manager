## [Sprint 1] - Initial Setup & Bugfixes

### How to Run the Application

To run the application, navigate to the project's root directory in your terminal and execute the following command:

```bash
python3 -m streamlit run main.py
```

This will start the Streamlit server, and you can access the application in your web browser, typically at `http://localhost:8501`.

## [Sprint 2] - Feature: Inventory

**👔 Vue Métier** : Offrir aux utilisateurs un moyen rapide et efficace de faire l'inventaire des composants (tags, extensions) sur plusieurs profils Tealium simultanément. L'utilisateur peut sélectionner des profils et rechercher des composants par mots-clés, ce qui lui permet d'identifier où des technologies spécifiques sont déployées, de vérifier la cohérence des configurations ou de planifier des migrations.

**⚙️ Vue Technique** :
*   **Architecture**: La fonctionnalité est implémentée comme une nouvelle vue dans Streamlit (`views/inventory_view.py`), assurant une intégration cohérente avec l'existant.
*   **Modules Créés**:
    *   `views/inventory_view.py`: Contient toute la logique de l'interface utilisateur, y compris la sélection des profils, la saisie des mots-clés et l'affichage des résultats.
    *   La logique de récupération des données s'appuie sur le `TealiumClient` existant pour les appels API, garantissant la réutilisation du code et la centralisation de la communication avec Tealium.
*   **Processus**:
    1.  Charge les profils disponibles depuis `database.py`.
    2.  Pour chaque profil sélectionné, il récupère la dernière version.
    3.  Il parcourt les tags et les extensions de cette version, en comparant leur nom (en minuscules) avec les mots-clés fournis.
    4.  Les résultats sont agrégés et affichés dans un tableau `pandas.DataFrame` pour une visualisation claire.
*   **Dette Technique**:
    *   La recherche se limite actuellement au nom (`name`) des composants. Une recherche plus avancée pourrait inclure d'autres champs (par exemple, la configuration des extensions, les variables de mapping des tags).
    *   Les erreurs sont gérées profil par profil, mais une stratégie de "retry" plus robuste pourrait être envisagée pour les appels API.
    *   Les résultats sont affichés dans un tableau simple. Des fonctionnalités de filtrage avancé ou d'exportation pourraient être ajoutées.

## [Sprint 3] - Refactoring & Feature Enhancement

**👔 Vue Métier** :
*   **Inventaire Amélioré**: L'utilisateur peut désormais filtrer sa recherche par type de composant (Tag, Extension, Load Rule, Variable), en plus des mots-clés, pour des recherches plus rapides et ciblées.
*   **Configuration Simplifiée**: L'interface de configuration est plus claire. Les identifiants (clé API, email), qui sont souvent les mêmes pour tous les profils, sont maintenant gérés dans une section globale, évitant la répétition.
*   **Performance Accrue**: Grâce à un système de cache, l'analyse des profils pour l'inventaire est quasi-instantanée après un premier "téléchargement". L'utilisateur n'attend plus les appels API à chaque recherche.

**⚙️ Vue Technique** :
*   **Architecture & Refactoring**:
    *   **Configuration Globale**: La gestion des configurations a été revue. La base de données (`database.py`) sépare maintenant les identifiants globaux (`global_settings`) des configurations de profils (`configurations`). Cela simplifie l'ajout de nouveaux profils.
    *   **Mise en Cache des Profils**: Une nouvelle table `profile_cache` a été ajoutée à la base de données. La vue de configuration permet de "télécharger" la dernière version d'un profil, qui est ensuite stockée localement.
    *   **Dépendance au Cache**: La fonctionnalité d'inventaire (`inventory_view.py`) ne fait plus d'appels API directs. Elle utilise exclusivement les données du cache (`get_cached_profile`), ce qui la rend plus rapide et moins sujette aux erreurs réseau. Si un profil n'est pas en cache, l'utilisateur est invité à le télécharger.
*   **Corrections de Bugs**:
    *   L'erreur `AttributeError: 'TealiumClient' object has no attribute 'get_revisions'` a été corrigée en renommant la méthode `get_revision_ids` en `get_revisions` dans `tealium_client.py` pour plus de cohérence.
*   **Dette Technique**:
    *   Le cache n'a pas de mécanisme d'expiration automatique (TTL). L'utilisateur doit manuellement retélécharger un profil pour le mettre à jour. Une stratégie de rafraîchissement périodique pourrait être envisagée.
    *   La gestion des erreurs de l'API Tealium lors du téléchargement pourrait être plus détaillée pour l'utilisateur.

## [Sprint 4] - Feature: Live vs Latest Profile Comparison

**👔 Vue Métier**: Les utilisateurs peuvent désormais comparer la dernière version non publiée d'un profil avec sa version "live" (actuellement publiée). Cela offre un filet de sécurité crucial avant de publier des modifications, permettant aux développeurs et aux gestionnaires de visualiser précisément ce qui va changer, réduisant ainsi le risque de mettre en production des configurations involontaires ou boguées.

**⚙️ Vue Technique**:
*   **Architecture & Refactoring**:
    *   La vue de comparaison (`views/comparison_view.py`) a été simplifiée pour ne demander qu'un seul profil à l'utilisateur, améliorant l'expérience.
    *   Le contrôleur (`controllers/comparison_controller.py`) a été profondément remanié. La fonction `process_comparison` orchestre maintenant la récupération de toutes les révisions d'un profil, identifie la révision "live" et la plus récente via le `TealiumClient`.
    *   La fonctionnalité s'appuie sur les méthodes existantes de `TealiumClient` (`get_revisions`, `get_revision_details`, `get_profile_components`) pour récupérer les données des deux versions.
    *   La logique de comparaison existante (`compare_profiles`) est ensuite utilisée pour générer le différentiel entre ces deux versions spécifiques.
*   **Gestion des Cas Limites**:
    *   La fonctionnalité gère correctement les cas où un profil n'a jamais été publié (aucun "live" à comparer) ou lorsqu'il n'y a aucune modification non publiée (la version la plus récente est la version live).
*   **Correction de Bug**:
    *   Un bug latent dans l'instanciation de `TealiumClient` (passage de `api_email` au lieu de `email`) a été corrigé pendant le refactoring.
*   **Dette Technique**: Aucune dette technique significative introduite. L'implémentation est propre et s'intègre bien à l'architecture existante.

## [Sprint 5] - Amélioration de la Page d'Accueil

**👔 Vue Métier**: Remplacer la page d'accueil vide par un guide de démarrage rapide et une présentation des fonctionnalités. L'objectif est de permettre aux nouveaux utilisateurs de comprendre immédiatement la valeur de l'outil et de savoir comment utiliser chaque fonctionnalité, améliorant ainsi l'adoption et la satisfaction.

**⚙️ Vue Technique**:
*   **Modification**: Mise à jour du fichier `main.py`.
*   **Implémentation**: Remplacement d'un simple `st.write` par un `st.markdown` contenant une description détaillée des fonctionnalités et des guides "comment faire".
*   **Dette Technique**: Aucune. C'est une simple mise à jour de contenu qui n'introduit pas de complexité technique.

## [Sprint 6] - Intégration Adobe Analytics API & Dashboard

**👔 Vue Métier**: Permettre aux utilisateurs de se connecter à l'API Adobe Analytics et de visualiser des données de performance directement dans l'application. L'objectif est de créer un mini-dashboard pour suivre des métriques clés (pages vues, visites) sur une période donnée et avec une granularité choisie, sans avoir à ouvrir Analysis Workspace. Cela offre un gain de temps et une première étape vers un monitoring consolidé.

**⚙️ Vue Technique**:
*   **Architecture**:
    *   **Base de Données**: Extension de `database.py` avec une nouvelle table `adobe_configurations` pour stocker les credentials de multiples organisations Adobe (y compris la clé privée, le secret client, etc.).
    *   **Client API**: Création d'un client API robuste, `utils/adobe_client.py`, gérant l'authentification complexe JWT (génération, échange de token) et la pagination automatique des rapports. Les dépendances `PyJWT` et `cryptography` ont été ajoutées.
    *   **Stack MVC**: Ajout d'une nouvelle stack complète pour la fonctionnalité :
        *   **Vue**: `views/adobe_dashboard_view.py` pour l'interface utilisateur en Streamlit (sélecteurs, graphiques, tableaux).
        *   **Contrôleur**: `controllers/adobe_controller.py` pour la logique métier (construction des requêtes, formatage des données en DataFrame).
    *   **Configuration**: Mise à jour majeure de la page de configuration (`config_view.py`, `config_controller.py`, `main.py`) pour permettre la gestion CRUD (Créer, Lire, Mettre à jour, Supprimer) de ces nouvelles configurations Adobe.
*   **Dette Technique**:
    *   Le dashboard est une première version "light" : les dimensions et métriques sont pour l'instant codées en dur dans la vue. Une évolution future serait de les charger dynamiquement depuis l'API Adobe pour offrir plus de flexibilité.
    *   La gestion des erreurs de l'API Adobe pourrait être plus fine et mieux présentée à l'utilisateur (actuellement, les erreurs sont principalement loguées dans la console).
    *   Les filtres (segments), bien que prévus dans l'architecture de la requête, ne sont pas encore implémentés dans l'interface utilisateur du dashboard.

## [Sprint 7] - Amélioration de l'Authentification Adobe

**👔 Vue Métier**: Simplifier la configuration initiale de l'intégration Adobe. Les utilisateurs peuvent maintenant choisir de coller un "Access Token" généré manuellement, ce qui leur permet de tester la fonctionnalité immédiatement sans passer par le processus complexe de création d'un projet Service Account (JWT). Cela réduit la barrière à l'entrée et facilite le dépannage.

**⚙️ Vue Technique**:
*   **Architecture**: Le système d'authentification Adobe a été rendu polymorphe.
    *   **Base de Données**: La table `adobe_configurations` dans `database.py` a été enrichie avec une colonne `auth_method` ('jwt' ou 'manual') et `manual_access_token`. La fonction de sauvegarde a été adaptée pour gérer une structure de données flexible.
    *   **API Client (`adobe_client.py`)**: Le client est maintenant capable de gérer les deux modes. La méthode `_ensure_token` a été modifiée pour soit utiliser le token manuel, soit déclencher le flux de rafraîchissement JWT.
    *   **UI/UX (`config_view.py`)**: L'interface de configuration affiche dynamiquement les champs de saisie pertinents en fonction du mode d'authentification choisi par l'utilisateur via un bouton radio, améliorant l'expérience utilisateur.
*   **Dette Technique**: Aucune nouvelle dette significative. Cette modification rend au contraire le système plus flexible et plus facile à maintenir ou à faire évoluer (par exemple, pour supporter OAuth 2.0 à l'avenir).

## [Sprint 8] - Optimisation des Performances Adobe Dashboard

**👔 Vue Métier**: Améliorer significativement la réactivité du Dashboard Adobe. Le chargement des composants (dimensions, métriques, segments) pour une suite de rapports est maintenant quasi-instantané après le premier chargement. L'utilisateur n'a plus à attendre plusieurs secondes à chaque fois qu'il sélectionne une suite de rapports, rendant l'exploration beaucoup plus fluide. Il peut également forcer la mise à jour des composants depuis la page de configuration si nécessaire.

**⚙️ Vue Technique**:
*   **Architecture**:
    *   **Mise en Cache des Composants Adobe**: Une nouvelle table `adobe_components` a été ajoutée à `database.py`. Elle stocke les listes de dimensions, métriques et segments sous forme de JSON, associées à une `rsid` (Report Suite ID) et un timestamp de dernière mise à jour.
    *   **Logique de Cache dans le Client API**: La responsabilité de la mise en cache a été centralisée dans `utils/adobe_client.py`. La méthode `get_adobe_dashboard_components` a été mise à jour pour :
        1.  Tenter de charger les composants depuis la base de données via `load_adobe_components`.
        2.  Si les données sont trouvées et qu'un rafraîchissement n'est pas forcé, les retourner immédiatement.
        3.  Sinon, appeler l'API Adobe pour récupérer les données fraîches.
        4.  Sauvegarder ces nouvelles données dans la base de données avec `save_adobe_components` avant de les retourner.
    *   **Interface de Gestion du Cache**: La vue `views/config_view.py` a été dotée d'une section "Gestion du Cache des Composants Adobe". Elle liste toutes les suites de rapports en cache avec leur date de dernière mise à jour et propose un bouton "Rafraîchir" qui appelle la logique de rafraîchissement forcé.
    *   **Simplification du Contrôleur**: Le contrôleur `controllers/adobe_controller.py` a été simplifié. Sa fonction `get_or_refresh_components` agit désormais comme un simple passe-plat vers le client, déléguant entièrement la gestion du cache.
*   **Dette Technique**: Aucune. Cette évolution est une optimisation propre qui réduit la charge sur l'API Adobe, améliore l'UX et renforce la séparation des responsabilités entre le client (gestion des données) et le contrôleur (orchestration).
