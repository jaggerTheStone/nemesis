# ADR-008 — Versionnement du réseau

- **Statut** : proposé
- **Date** : 2026-11-04
- **Casquettes consultées** : architecte, ingénieur géomatique, data scientist, SRE

## Contexte

La partie 6.3 demande que toute modification du réseau passe par une proposition, une revue et une publication. Il faut aussi :
- garder l'historique, comparer deux versions et pouvoir revenir en arrière ;
- appliquer chaque version à une date d'effet ;
- exporter et importer en GTFS.

Le moteur d'itinéraires et les packs hors ligne doivent indiquer la version du réseau qu'ils utilisent, pour que les résultats soient reproductibles. Enfin, un changement de réglementation doit pouvoir être corrigé dans l'heure (parcours 10 de la partie 4.2).

## Options envisagées

| Critère | 1. Versionner chaque ligne (validité de version en version) | 2. État publié et journal des modifications | 3. Instantanés complets par version |
|---------|-------------------------------------------------------------|---------------------------------------------|-------------------------------------|
| Clés étrangères | Difficiles : une entité a plusieurs lignes | Simples : une ligne par entité | Simples |
| Requêtes courantes (moteur, API) | Filtre de version partout | Directes | Directes |
| Comparaison de deux versions | Requête sur les plages de validité | Journal avant et après, entre les deux versions | Différence de deux instantanés |
| Retour arrière | Rouvrir les anciennes lignes | Nouvelle version qui applique l'inverse des modifications | Republier un ancien instantané |
| Reproductibilité du moteur | Oui | Oui, avec l'export GTFS et le pack de chaque version | Oui |
| Volume | Moyen | Faible | Élevé |

## Décision proposée

**Option 2 : état publié et journal des modifications**, complétée par un export par version.

- Les tables de `network` portent l'**état publié courant**. Le moteur et l'API les lisent directement.
- Une modification est d'abord une **demande** (`change_request`), sous forme d'une liste d'opérations. Une **autre personne** l'approuve ou la rejette ; le rejet exige une raison. La base l'impose par des contraintes.
- La publication crée une **version** (`network_version`), numérotée par ville, avec une date d'effet. Elle applique les opérations des demandes approuvées et inscrit chaque changement, avant et après, dans `entity_change`.
- Une version publiée est **immuable**, garantie par un déclencheur. On corrige par une nouvelle version, et le retour arrière consiste à appliquer l'inverse des changements enregistrés.
- Chaque version publiée produit un **export** GTFS et un pack ville (`export_uri`). C'est ce que le moteur et les téléphones utilisent : un résultat d'itinéraire est donc reproductible.
- **Garde-fou sur les données fictives** :
  - une clé étrangère composite `(city_id, is_fictional)` empêche toute ligne fictive dans une ville réelle ;
  - `network.publish_version()` refuse de publier une ville fictive si `nemesis.environment = 'production'`.

La logique d'application des opérations reste dans l'API (module `admin`, phase 1). La base, elle, garantit les invariants : revue par une autre personne, raison de rejet, immutabilité, cohérence fictive et cohérence entre villes.

**Désaccord entre casquettes.** Le data scientist préférait l'option 1, qui permet d'interroger n'importe quelle version passée directement en SQL. L'architecte et le SRE préfèrent l'option 2 : requêtes courantes simples et clés étrangères ordinaires. Les exports par version couvrent le besoin d'analyse historique.

## Conséquences

- **Mise en œuvre** : en I0.4 (migrations `20261104000300_versions_reseau.sql`), testée dans `data/schema/tests`.
- **Coût** : le code d'application des opérations et de leur inverse est à écrire en phase 1, avec des tests de retour arrière.
- **Réversibilité** : moyenne. Passer à l'option 1 plus tard demanderait de migrer les tables, mais le journal `entity_change` contient l'information nécessaire pour reconstruire les plages de validité.
