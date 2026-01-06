# Ré-évaluation de la Stratégie d'Accès à l'API

Ce document acte une ré-évaluation critique de notre approche suite à l'échec persistant de la résolution de l'erreur `401 Unauthorized`.

## 1. Constat d'Échec de l'Hypothèse Précédente

L'hypothèse du Sprint 2 était que l'endpoint V2 `GET /v2/accounts/{account}/profiles/{profile}/revisions/{revision_id}` nécessitait une authentification via un token obtenu par l'API V3.

- **Résultat** : Cette hypothèse est **incorrecte**. L'utilisation d'un token V3 sur cet endpoint V2 résulte toujours en une erreur `401 Unauthorized`.
- **Conclusion** : L'endpoint lui-même est probablement une impasse. Il est soit déprécié, soit son accès est restreint d'une manière que nous ne pouvons contourner avec les identifiants fournis. Persister dans cette voie est inefficace.

## 2. Nouvelle Analyse de la Documentation API V2

En ré-examinant la documentation de l'API V2 (`api_v2.txt`), une autre méthode, documentée et officielle, se dessine : l'utilisation du **bundle de révision**.

- **Endpoint concerné** : `GET /v2/manifest/accounts/{account}/profiles/{profile}/revisions/{revision_id}/environments/{environment}`
- **Action** : Cet endpoint retourne un fichier `bundle.zip`.
- **Contenu du Bundle** : Le bundle contient tous les fichiers JavaScript déployables, incluant `utag.js`, les fichiers de tags, et un `manifest.json`.

## 3. Nouvelle Hypothèse de Travail (Hypothèse du Bundle)

La configuration complète d'une révision (tags, variables, règles, extensions) n'est pas disponible via un appel JSON direct. Elle doit être **extraite du bundle de la révision**.

La source de vérité la plus probable pour la configuration complète est le fichier `utag.js` contenu dans le bundle. Historiquement, ce fichier contient un objet JavaScript, souvent nommé `utag.data` ou `utag.cfg`, qui contient l'ensemble de la configuration du profil.

### Nouveau Plan d'Action

1.  **Abandonner** toute tentative d'appel à `GET /v2/accounts/{account}/profiles/{profile}/revisions/{revision_id}`.
2.  Modifier la méthode `get_revision_configuration` dans `TealiumClient`.
3.  Cette méthode devra maintenant :
    a. Appeler la méthode `get_revision_bundle` (qui existe déjà et fonctionne avec l'authentification V2 Bearer Token) pour télécharger le ZIP.
    b. Une fois le ZIP extrait en mémoire, trouver le fichier `utag.js`.
    c. Parser le contenu de `utag.js` pour en extraire l'objet JSON contenant la configuration.
    d. Retourner cet objet JSON parsé, qui correspondra à la structure attendue par l'interface utilisateur.

Cette approche est plus complexe mais repose sur des endpoints documentés et fonctionnels, et représente donc une voie de résolution beaucoup plus robuste.
