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

## [Sprint 9] - Générateur de Rapports & Batching

**👔 Vue Métier**: Offrir une capacité d'automatisation et de sauvegarde complète.
*   **Gestion Complète**: Création, **Édition** et Suppression de rapports personnalisés (métriques, dimensions, segments).
*   **Batching**: Exécution en masse de plusieurs rapports sur différents comptes Adobe en un clic.
*   **Visualisation**: Tableaux de résultats dynamiques avec ventilation temporelle (Jour/Semaine/Mois) et **génération de courbes de tendance** instantanée au sein du tableau.

**⚙️ Vue Technique**:
*   **Architecture**:
    *   **Persistance**: Nouvelle table `saved_reports` dans `database.py` avec migration automatique du schéma (ajout colonnes `definition`, `created_at`).
    *   **Backend**: `controllers/adobe_controller.py` gère désormais le pivot des données pour afficher les dates en colonnes et supporte le mode "Comparaison de Segments" vs "Top Items".
    *   **Frontend**: Refonte de `views/adobe_reports_view.py` avec gestion d'état avancée pour la navigation (redirection après sauvegarde) et l'édition (pré-remplissage du formulaire). Utilisation de `st.data_editor` pour l'interactivité (checkbox courbe).
*   **Dette Technique**:
    *   La gestion de la navigation Streamlit repose sur des hacks d'état (`st.session_state`) pour contourner les limitations des widgets natifs. À surveiller lors des mises à jour de Streamlit.
    *   Le parsing des dates pour les graphiques repose sur le format des noms de colonnes, ce qui crée un couplage fort entre le contrôleur et la vue.

## [Sprint 10] - Feature: Inventory Crawler & Bulk Selection

**👔 Vue Métier**:
*   **Mode Crawler**: L'inventaire n'est plus limité à la recherche par mots-clés. Les utilisateurs peuvent désormais lancer une extraction complète de tous les composants (Tags, Extensions, etc.) pour les profils sélectionnés. Cela permet des audits exhaustifs.
*   **Sélection de Masse**: Ajout de boutons "Tout sélectionner" / "Tout désélectionner" pour faciliter la gestion d'un grand nombre de profils simultanément.

**⚙️ Vue Technique**:
*   **Modification**: Mise à jour de `views/inventory_view.py`.
*   **Logique**:
    *   Le champ `keywords` est devenu optionnel. Si vide, la boucle de filtrage accepte tous les items.
    *   Utilisation du `st.session_state` pour manipuler dynamiquement la sélection du widget `multiselect` via des boutons externes.
    *   Ajout d'un bouton `st.download_button` pour exporter le DataFrame résultant en CSV.
*   **Dette Technique**:
    *   L'affichage d'un très grand nombre de lignes (plusieurs milliers) dans le tableau final pourrait nécessiter une pagination côté serveur à l'avenir, bien que `st.dataframe` gère bien la charge actuelle.

## [Sprint 11] - Feature: Adobe System Audit (Dimensions)

**👔 Vue Métier**:
*   **Audit de Couverture**: Permet aux analystes de vérifier rapidement l'utilisation des 200 eVars et 75 Props sur deux segments (ex: Site vs App) et deux périodes.
*   **Automatisation**: Remplace une tâche manuelle fastidieuse (créer des dizaines de rapports) par un seul clic.

**⚙️ Vue Technique**:
*   **Architecture**:
    *   Ajout d'une fonction `run_system_audit_report` dans le contrôleur Adobe. Elle génère dynamiquement les IDs de dimensions (`variables/evar1`...`200`).
    *   Utilisation intensive de `concurrent.futures.ThreadPoolExecutor` pour lancer ~550 requêtes API en parallèle (275 dimensions * 2 plages de dates).
    *   Chaque requête récupère les totaux pour 2 segments simultanément pour optimiser le quota API.
    *   **Correction Sprint 12**: Le client API est maintenant correctement initialisé avec les paramètres globaux (Proxy) à l'intérieur des threads, résolvant le bug des résultats "-1".
*   **UI**:
    *   Intégration complète de l'Audit dans le flux "Mes Rapports".
    *   Ajout d'un sélecteur de type (Standard vs Audit) lors de la création d'un rapport.
    *   Sauvegarde des configurations d'audit (Segments, Périodes) en base de données via le champ JSON `definition`.
    *   Sélecteurs de segments intelligents (recherche par défaut "site" et "app").

## [Sprint 12] - Performance: Async Audit

**👔 Vue Métier**:
*   **Vitesse Extrême**: L'audit système est passé de plusieurs minutes à quelques secondes.
*   **Fiabilité**: Moins d'erreurs de timeout ou de "Rate Limit" grâce à une gestion intelligente du trafic API.

**⚙️ Vue Technique**:
*   **Architecture Asynchrone**: Remplacement du threading (`concurrent.futures`) par `asyncio` et `aiohttp`.
*   **Optimisation API**: Utilisation des `metricFilters` avec `predicates` pour récupérer 4 points de données (2 segments x 2 périodes) en un seul appel API, divisant le nombre de requêtes par 4.
*   **Nouvelle Dépendance**: Ajout de la librairie `aiohttp`.
*   **Robustesse**: Ajout d'un calcul de plage de date globale (Union) pour satisfaire les exigences de l'API Adobe (Fix erreur 400) et réintroduction d'une boucle de retry exponentielle pour gérer les Rate Limits (Fix erreur 429).
*   **Logique Métier**: Retour à la métrique `Pageviews` mais avec un filtre `search: {excludeItemIds: ["0"]}` pour exclure les valeurs "Unspecified". Cela garantit que le volume rapporté correspond uniquement aux cas où la dimension est explicitement définie. Ajout automatique des colonnes de Variation (%).
*   **Gestion des Erreurs**: Prise en charge du code HTTP 206 (Partial Content) pour identifier les dimensions non activées ("not_enabled_dimension_global") et afficher "Non actif" dans le rapport au lieu d'une erreur technique.
*   **UX**: Arrondi des valeurs à l'entier supérieur (`math.ceil`) et raccourcissement automatique des noms de segments dans les en-têtes de colonnes pour optimiser l'affichage du tableau d'audit.
*   **Visualisation**: Ajout d'un code couleur (Emojis) pour les variations (🔴 Critique -100%, 🔻 Baisse, 💚 Hausse) et implémentation d'un graphique en barres spécifique pour visualiser les écarts P1/P2 dans les rapports d'audit.
*   **Performance Custom**: Extension du moteur asynchrone (`aiohttp`) aux rapports personnalisés de type "Comparaison de Segments". Le traitement est désormais parallélisé (jusqu'à 10 segments simultanés), réduisant drastiquement le temps d'exécution pour les rapports volumineux.
*   **Scope**: Validation finale et réactivation du périmètre complet (200 eVars + 75 Props).

## [Release] - Alpha 7

**🔖 Versioning** : Snapshot de l'application incluant toutes les fonctionnalités jusqu'au Sprint 9 (Générateur de Rapports & Batching).
**📅 Statut** : Stable
**🌿 Branche** : `alpha7`
**📝 Note** : Cette version sert de point de référence avant l'intégration potentielle de fonctionnalités d'écriture (POST/PATCH) plus poussées ou de refonte UI majeure.
