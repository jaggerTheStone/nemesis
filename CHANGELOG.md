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
- I0.6 : contrat de l'API et squelette.
  - OpenAPI 3.1 (`packages/openapi`) :
    - 26 opérations ;
    - estimations accompagnées de leur fraîcheur, confiance et source ;
    - idempotence des écritures, ETag, pagination par curseur, limites de débit, erreurs RFC 9457 ;
    - types générés et règles vérifiées par des tests.
  - Protobuf `nemesis.live.v1` (deltas par tuile), avec contrôle de compatibilité.
  - API NestJS branchée sur PostgreSQL : villes, recherche de lieux tolérante
    aux fautes, fiche d'arrêt avec repli historique ; Brotli, ETag ; tests de
    contrat générés depuis le contrat, contre une base migrée ; `make api-test`.
- I0.7 : pipelines d'import et rapports.
  - Manifeste des sources (`data/pipelines/sources.toml`) : téléchargement refusé
    sans empreinte (SHA-256 épinglée ou MD5 publiée), provenance conservée,
    outils épinglés par empreinte.
  - GTFS « Abidjan 2023 » pris à son dépôt d'origine, au commit `da5d9faf`.
    Sa licence est **CC BY-NC 4.0** : évaluation interne seulement (H-030),
    et la base refuse toute ligne du réseau qui le cite (erreur `NM004`).
  - Migration `20261104000800_imports` : `ops.import_run`, `staging_gtfs`
    (lignes intactes et vues typées), `staging_osm`, référence externe des lieux,
    garde de licence ; l'API ne lit pas les zones intermédiaires.
  - Validateur MobilityData : tous les avis listés, erreurs d'abord, rien corrigé.
  - Import OSM par osm2pgsql 1.11 (style flex) ; promotion des points d'intérêt
    en lieux avec leurs alias, sans doublon ni suppression silencieuse.
  - Rapport d'écarts GTFS ↔ OSM : appariement par identifiant OSM, puis par
    distance, référence et géométrie ; Markdown et GeoJSON.
  - Fond de carte léger : schéma Planetiler maison (ADR-009), archive du pays et
    extrait d'Abidjan, taille lue dans l'en-tête PMTiles et comparée à F-12.
  - Extrait OSM fictif de Lagune-Fictive, avec des écarts volontaires que le
    rapport doit retrouver exactement.
  - `make data-import`, `make data-import-fictif`, `make pipelines-test` ;
    workflows « Pipelines de données (chaîne fictive) » et « Imports de données
    réelles (hebdomadaire) ».
  - Première chaîne réelle verte (2026-11-04) : GTFS 2023 sans erreur
    (245 avertissements, 974 informations) ; 4 815 arrêts sur 4 834 et les
    974 tracés retrouvés dans OSM ; 33 284 lieux promus ; extrait de tuiles
    d'Abidjan de 4,5 Mo pour un budget de 45 Mo.
- I0.8 : spike du moteur d'itinéraires et ADR-003 accepté (option B).
  - `routing-core` : GTFS avec calendriers, réseau à fréquences, points de
    montée virtuels, attente du régime B comme coût de montée, attentes en
    direct simulées, RAPTOR ; `routing spike` ; compilation Android arm64.
  - `tools/routing-spike` : 25 couples tirés des arrêts réels,
    OpenTripPlanner 2.10 épinglé, comparaison avec une fonction de coût
    commune ; workflow dédié et `make routing-spike`.
  - Mesures : B répond en 0,6 ms (12 Mio), OTP en 689 ms (1 Gio) ; avec des
    attentes en direct simulées, B gagne plus de 5 min dans 44 requêtes
    sur 74.
- I0.9 : moteur d'itinéraires en ligne de commande.
  - Pack ville (format 1) : GTFS et graphe piéton tiré d'OSM ;
    `nemesis-data pack reel`, pack fictif dans `data/fixtures_fictives/pack`.
  - `routing-core` : interface `RoutingEngine`, McRAPTOR à quatre critères,
    marche sur le graphe OSM, attentes en régime A (profils) ou B
    (intervalles du GTFS), prix estimés, Monte-Carlo à 500 tirages, options
    étiquetées « le moins cher », « le plus rapide », « le plus simple »,
    source de chaque étape.
  - `routing plan` et `routing bench` ; tests par propriétés.
  - Workflow « Itinéraire réel de bout en bout (I0.9) » : critère de fin de
    la phase 0 atteint ; 75 requêtes sur le GTFS 2023 et le graphe piéton
    d'Abidjan en 43 ms en médiane, 123 ms au 95e centile.
  - H-032 : paramètres du moteur v0, à calibrer.
- I0.10 : simulateur par agents v0 (`tools/simulator`).
  - Corridor fictif G1 : gare de tête au remplissage (régime A), arrêts de bord
    de route (régime B), bus de passage, pluie, patience au bord de la route.
  - Signalements au format `ContributionRequest` (bruit, retards, renvois,
    chef de gare, fraude) et vérité terrain ; exemple validé contre le contrat.
  - `nemesis-simulator simuler | evaluer | exemple`, `make simulation` ;
    évaluation dans le résumé du workflow Python.
  - Formules d'attente confrontées à la simulation : calibrées quand leurs
    hypothèses tiennent. Sur le corridor, le régime A est trop prudent sous la
    pluie et le régime B trop optimiste quand d'autres attendent ; corrections
    proposées dans ALGORITHMES.md.
  - H-033 : conventions des signalements et paramètres du simulateur.
- I0.11 : prototype cliquable Flutter et mesures de l'ADR-001.
  - `routing-ffi` : interface C du moteur d'itinéraires pour le téléphone
    (dart:ffi) ; profil release avec LTO et symboles retirés.
  - Données fictives embarquées générées par `nemesis-fixtures` : pack du
    moteur, `city.json`, `map.json`.
  - Appli hors ligne : onglets Trajet, Carte, Moi, bouton Signaler, résultats
    étiquetés, pas à pas, fiche gare, signalement en deux pressions (file
    SQLite au format `ContributionRequest`), « Pourquoi cette estimation ? »,
    carte MapLibre sans tuiles, bandeau « DONNÉES FICTIVES », jetons de design.
  - Tests : widgets, références visuelles à 100 % et 200 % de taille de
    texte, accessibilité, moteur natif ; CI : APK arm64 de production mesuré,
    test de fumée sur émulateur Android 8 (API 26).
  - ADR-001 mesuré : APK de 52,5 Mo, environ 21,3 Mo à télécharger pour un
    budget de 20 Mo, dont 10,8 Mo pour la carte ; décision du porteur.
  - Protocole WhatsApp « magicien d'Oz » (bloqué par Q-07), guide de codage
    des icônes, H-034.
  - Constat sur le GTFS 2023 : 28 % des courses ont une durée forfaitaire de
    120 min.

### Corrigé

- `make dev` et la CI ne dépendent plus de la durée de la migration :
  `docker compose up --wait` échouait parfois quand le conteneur de migration se
  terminait pendant l'attente.
