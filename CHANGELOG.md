# Journal des modifications

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).
Les versions suivront le versionnage sémantique à partir de la première
publication.

## [Non publié]

### Ajouté

- Cadrage : cahier des charges en Markdown, hypothèses (toutes validées le
  2026-11-04), plan de la phase 0, état du projet.
- I0.1 : socle du monorepo (arborescence de la partie 9.7 et `tools/simulator`),
  outillage par écosystème (pnpm, Cargo, uv, Flutter, buf), `Makefile` racine,
  intégration continue GitHub Actions par composant, analyse de sécurité Trivy,
  audits de dépendances, licence, politique de sécurité, modèle de pull request.
- I0.2 : kits de terrain.
  - Protocoles : requêtes réelles, trajets de référence avec la règle de notation
    du réalisme, tests de maquettes et d'icônes.
  - Quatre fiches papier imprimables, en HTML et en PDF.
  - Schémas des six jeux de terrain, dont sont générés les modèles CSV et le
    dictionnaire des données.
  - Validateur `nemesis-terrain`, exécuté en intégration continue, et rapport de
    reconnaissance des icônes.
  - Exemples fictifs et modèle de compte rendu des tests utilisateurs.
- I0.3 : documents fondateurs.
  - `ARCHITECTURE.md` : vues C4 de contexte et de conteneurs, flux principaux,
    parité en ligne et hors ligne.
  - `DATA.md` : sources et licences, provenance, fraîcheur et confiance,
    spécification de l'extension GTFS v0.
  - `PRIVACY.md` : registre des traitements, analyse d'impact de la
    géolocalisation (brouillon), brouillon du dossier ARTCI, questions au juriste.
  - `COUTS.md` : modèle de volumes par palier, formules, prix à collecter,
    coût en data pour l'usager.
  - `ALGORITHMES.md` : régimes d'attente A, B et C avec exemples chiffrés,
    calibration, itinéraires, prix, géocodage, détection.
  - ADR-001 à ADR-007, au statut « proposé ».
  - Vérification des liens de la documentation en CI.
- I0.4 : base de données et environnement local.
  - Sept migrations dbmate : schémas `network`, `mobility`, `identity` et `ops`,
    40 tables, partitions quotidiennes, rôles séparés, journal d'audit chaîné,
    versions du réseau (ADR-008).
  - Contraintes : cohérence des données fictives et entre villes, honnêteté
    des estimations, conservation.
  - `docker-compose.yml` (PostGIS, Valkey, NATS, Caddy pour les tuiles), avec
    migration et jeu fictif au démarrage ; `make dev`, `make db-test`.
  - 23 tests du schéma et un workflow de CI « Base de données ».
- I0.5 : jeu fictif « Lagune-Fictive ».
  - Générateur `nemesis-fixtures` à graine fixe, avec une seule description de
    la ville pour deux sorties.
  - GTFS : fréquences, montée continue, Fares v2 et extension `ext_` (profils
    publiés seulement à partir de 20 contributeurs).
  - Jeu SQL de la base de développement.
  - Validateur MobilityData en CI, avec rapport conservé ; `make gtfs-validate`.
