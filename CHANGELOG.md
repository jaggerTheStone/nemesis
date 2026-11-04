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
