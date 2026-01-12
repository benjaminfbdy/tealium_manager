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