
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
