## [Sprint 3] - Mise en Cache des Révisions Tealium & Harmonisation Graphique

**👔 Vue Métier** :
*   Le processus de mise en cache des révisions est maintenant robuste et fonctionne comme prévu, garantissant une meilleure performance et moins de dépendance aux appels API directs.
*   L'application présente une expérience utilisateur plus cohérente grâce à l'application uniforme de la charte graphique sur toutes les pages.

**⚙️ Vue Technique** :
*   **Correction de Bug (UI - `pages/1_⚙_Configuration.py`)** :
    *   Correction de l'erreur `'str' object has no attribute 'get'` lors de la mise en cache des révisions. La logique a été adaptée pour gérer le format de réponse de l'API Tealium qui renvoie les IDs de révision sous forme de liste de chaînes de caractères.
*   **Harmonisation Graphique (Toutes les pages)** :
    *   Suppression des configurations de page spécifiques (`st.set_page_config`) dans `pages/0_🕰️_Historique.py`, `pages/1_⚙_Configuration.py`, `pages/2_🔎_Exploration.py` et `pages/3_🔄_Comparaison.py`.
    *   Ajout du CSS personnalisé et du code d'en-tête global (`st.markdown`) à chacune de ces pages pour assurer une cohérence visuelle avec `app.py`.

**Dette Technique Restante** :
*   Ajouter des tests unitaires pour le `TealiumClient`, les `services` et les fonctions `database`.
*   Explorer l'utilisation de `st.session_state.page` si une navigation plus complexe est requise au-delà de la navigation par fichier de Streamlit.
*   Revoir la possibilité d'utiliser `st.data_editor` avec `ButtonColumn` si l'environnement Streamlit de l'utilisateur est mis à jour à une version plus récente et stable.

## [Sprint 4] - Correction d'erreurs critiques et amélioration de l'exploration des révisions

**👔 Vue Métier** :
*   La fonctionnalité de comparaison entre deux publications est désormais opérationnelle, permettant une analyse des changements sans erreur.
*   L'exploration des révisions affiche désormais correctement tous les éléments attendus, offrant une visibilité complète sur le contenu des versions passées.

**⚙️ Vue Technique** :
*   **Correction de Bug (`pages/3_🔄_Comparaison.py`)** :
    *   Résolution d'un `SyntaxError` dans l'expression régulière utilisée par `re.findall` due à une mauvaise formation de la chaîne littérale. Le pattern `r""[(?:'([^']+)'|(\d+))""]"` a été corrigé en `r"\[(?:'([^']+)'|(\d+))\]"` à deux occurrences dans le fichier.
*   **Correction de Bug & Amélioration (Mise en cache des révisions - `pages/1_⚙️_Configuration.py` et affichage - `pages/2_🔎_Exploration.py`)** :
    *   Le processus de mise en cache des révisions a été amélioré pour stocker à la fois les métadonnées de la révision (obtenues via `client.get_revision_details`) et la configuration complète (obtenue via `client.get_revision_configuration`). Ces deux ensembles de données sont maintenant combinés en un seul objet JSON avant d'être sauvegardés dans la base de données.
    *   Cette modification garantit que la page "Historique" (`pages/0_🕰️_Historique.py`) dispose des métadonnées nécessaires pour le filtrage et l'affichage des révisions, et que la page "Exploration" (`pages/2_🔎_Exploration.py`) peut accéder à la configuration complète pour afficher les éléments de la révision.

**Dette Technique Restante** :
*   Ajouter des tests unitaires pour le `TealiumClient`, les `services` et les fonctions `database`.
*   Explorer l'utilisation de `st.session_state.page` si une navigation plus complexe est requise au-delà de la navigation par fichier de Streamlit.
*   Revoir la possibilité d'utiliser `st.data_editor` avec `ButtonColumn` si l'environnement Streamlit de l'utilisateur est mis à jour à une version plus récente et stable.

## [Sprint 5] - Améliorations de l'interface utilisateur et de l'expérience de navigation

**👔 Vue Métier** :
*   L'application est désormais plus intuitive grâce à l'affichage cohérent du thème lumineux par défaut de Streamlit, tout en conservant l'identité visuelle de l'entreprise.
*   La navigation a été optimisée en définissant la page "Historique des MEP" comme page d'accueil par défaut, réduisant les clics et améliorant l'accès aux informations clés.
*   La section de configuration des profils est désormais toujours accessible, même si aucun compte n'est trouvé via l'API, permettant une configuration manuelle plus flexible.

**⚙️ Vue Technique** :
*   **Correction de Bug (Accès Configuration Manuelle - `pages/1_⚙️_Configuration.py`)** :
    *   Correction de la logique de conditionnement de l'affichage de la section de configuration manuelle des profils. La variable `st.session_state.client` est maintenant toujours initialisée après une tentative de connexion réussie, même si l'API ne retourne aucun compte, garantissant l'accès aux sections de configuration suivantes.
*   **Amélioration (Homepage de l'application)** :
    *   Le fichier `pages/0_🕰️_Historique.py` a été renommé en `pages/🏠_Historique.py` pour être automatiquement reconnu comme la page d'accueil par Streamlit.
*   **Amélioration (Thème et Charte Graphique)** :
    *   Le thème global de l'application est maintenant défini sur "light" via `st.set_page_config(theme="light")` dans `app.py`.
    *   Le bloc de style CSS personnalisé (`custom_css`) a été centralisé dans `app.py` pour inclure uniquement le style de l'en-tête de l'application (`.app-header`).
    *   Les blocs `custom_css` et les appels `st.markdown` correspondants ont été supprimés de toutes les pages individuelles (`pages/🏠_Historique.py`, `pages/1_⚙️_Configuration.py`, `pages/2_🔎_Exploration.py`, `pages/3_🔄_Comparaison.py`) afin d'éviter les redondances et de permettre au thème global de Streamlit de gérer le style du corps et de la sidebar.

**Dette Technique Restante** :
*   Ajouter des tests unitaires pour le `TealiumClient`, les `services` et les fonctions `database`.
*   Explorer l'utilisation de `st.session_state.page` si une navigation plus complexe est requise au-delà de la navigation par fichier de Streamlit.
*   Revoir la possibilité d'utiliser `st.data_editor` avec `ButtonColumn` si l'environnement Streamlit de l'utilisateur est mis à jour à une version plus récente et stable.

## [Sprint 6] - Améliorations de l'expérience utilisateur pour la mise en cache

**👔 Vue Métier** :
*   Le processus de mise en cache des révisions offre désormais un feedback visuel détaillé, avec des barres de progression et des messages d'état clairs pour chaque étape et chaque révision traitée.
*   L'utilisateur est informé en temps réel des erreurs spécifiques rencontrées lors de la récupération des données de révision, ce qui facilite le diagnostic et améliore la transparence du processus.
*   La navigation dans l'application est plus propre grâce à la suppression du raccourci 'App' non pertinent dans la barre latérale.

**⚙️ Vue Technique** :
*   **Correction de Bug (Visibilité Raccourci 'App')** :
    *   Suppression des appels `st.markdown` qui affichaient le CSS personnalisé et l'en-tête de l'application directement dans `app.py`. Cela permet à `app.py` d'agir uniquement comme un fichier de configuration global, empêchant son apparition indésirable dans la barre latérale de Streamlit.
*   **Amélioration (Barre de Progression et Feedback - `pages/1_⚙️_Configuration.py`)** :
    *   Implémentation d'une barre de progression imbriquée dans la section de mise en cache des révisions. Une barre `overall_progress_bar` affiche la progression globale des profils, et une `rev_progress_bar` dédiée suit le traitement des révisions au sein de chaque profil.
    *   Le placeholder `status_text_placeholder` a été affiné pour fournir des mises à jour dynamiques et granulaires, indiquant le profil et la révision en cours de traitement.
    *   La gestion des erreurs a été améliorée avec des messages `st.success`, `st.info`, `st.warning`, et `st.error` affichés via `status_text_placeholder` pour chaque étape de récupération de révision, offrant un feedback immédiat sur le succès ou l'échec d'une opération spécifique.

**Dette Technique Restante** :
*   Ajouter des tests unitaires pour le `TealiumClient`, les `services` et les fonctions `database`.
*   Explorer l'utilisation de `st.session_state.page` si une navigation plus complexe est requise au-delà de la navigation par fichier de Streamlit.
*   Revoir la possibilité d'utiliser `st.data_editor` avec `ButtonColumn` si l'environnement Streamlit de l'utilisateur est mis à jour à une version plus récente et stable.

## [Sprint 7] - Résolution de l'erreur `TypeError` sur `theme`

**👔 Vue Métier** :
*   L'application peut maintenant démarrer sans rencontrer de `TypeError` lié à la configuration du thème, garantissant une meilleure stabilité au lancement.
*   L'expérience utilisateur reste agréable, avec un thème par défaut clair de Streamlit et la charte graphique de l'en-tête de l'application.

**⚙️ Vue Technique** :
*   **Correction de Bug (`app.py`)** :
    *   Suppression de l'argument `theme="light"` de l'appel `st.set_page_config` dans `app.py`. Cet argument n'est pas supporté par les versions plus anciennes de Streamlit, ce qui provoquait un `TypeError`.
    *   **Note sur la compatibilité**: Pour utiliser nativement l'argument `theme` dans `st.set_page_config`, une mise à jour de Streamlit vers la version 1.16.0 ou ultérieure est nécessaire.
    *   Si l'utilisateur souhaite définir un thème spécifiquement "light" sans mettre à jour Streamlit, il peut le faire via le fichier de configuration `.streamlit/config.toml` (par exemple, en ajoutant `[theme] primaryColor="#F63366" backgroundColor="#FFFFFF" secondaryBackgroundColor="#F0F2F6" textColor="#262730" font="sans serif"`).

**Dette Technique Restante** :
*   Ajouter des tests unitaires pour le `TealiumClient`, les `services` et les fonctions `database`.
*   Explorer l'utilisation de `st.session_state.page` si une navigation plus complexe est requise au-delà de la navigation par fichier de Streamlit.
*   Revoir la possibilité d'utiliser `st.data_editor` avec `ButtonColumn` si l'environnement Streamlit de l'utilisateur est mis à jour à une version plus récente et stable.