# Hypothèses de travail

Ce registre applique la règle 1.3.7 du cahier des charges : quand une information manque et n'est pas bloquante, on pose une hypothèse explicite, on la note ici et on avance.

Statuts possibles : **proposée** (en attente de validation), **validée**, **remplacée** (par une décision ou un ADR), **abandonnée**.

Dernière mise à jour : 2026-11-04 : toutes les hypothèses ont été validées par le porteur du projet.

## Questions bloquantes

Ces questions ont été posées dans le premier message. Réponse du 2026-11-04 : les hypothèses par défaut sont validées. Chaque question pourra être rouverte quand l'information manquante arrivera.

| ID | Question | Hypothèse par défaut validée |
|----|----------|-----------------------------------|
| Q-01 | Nom de l'application : `{{NOM_APP}}` n'a pas été remplacé ; le dépôt s'appelle `nemesis`. | `nemesis` sert de nom de code technique ; le nom public passe par la clé de traduction `app.name` (H-003). |
| Q-02 | Moyens : qui travaille sur le projet, avec quelles compétences, combien de temps, quel budget en phase 0, quel téléphone de référence physique ? | Je développe seul, tu valides ; budget proche de zéro (offre gratuite de la CI GitHub) ; pas de téléphone physique (H-001, H-004). |
| Q-03 | Terrain : qui, à Abidjan, collecte les 300 requêtes réelles et les 200 trajets de référence, et mène les tests de maquettes en gare ? | Je livre protocoles et outillage ; la collecte attend qu'une personne soit disponible sur place. |
| Q-04 | Porteur juridique du projet, relations existantes (AMUGA, SOTRA, syndicats, universités), accès à un juriste ivoirien ? | Responsable du traitement noté « à désigner » dans le brouillon ARTCI ; aucune convention supposée. |
| Q-05 | Corridor pilote. | Choix motivé après analyse du GTFS 2023 entre Yopougon–Adjamé–Plateau et Abobo–Adjamé (H-006). |
| Q-06 | Licence du code (ouverte ou propriétaire) et politique de licences des données. | Propriétaire, « tous droits réservés » ; dépendances permissives uniquement (H-019). |
| Q-07 | Arbitrage : aucune donnée personnelle réelle avant la déclaration ARTCI ou un avis juridique écrit, y compris pour le prototype WhatsApp « magicien d'Oz ». | Arbitrage appliqué : fiches anonymes en phase 0, prototype WhatsApp différé (H-020). |
| Q-08 | Accès réseau de l'environnement de développement (hôtes bloqués, voir H-021). | Les imports et le build Android tournent uniquement dans GitHub Actions. |

## Organisation

- **H-001** (validée) — Les phases sont validées une par une, comme le demande la partie 1.4. À l'intérieur d'une phase, j'enchaîne les incréments sans attendre de validation intermédiaire ; chaque incrément est poussé avec une CI verte et consigné dans `docs/ETAT.md` et `CHANGELOG.md`.
- **H-002** (validée) — Intégration continue sur GitHub Actions. Je travaille sur la branche de travail désignée ; les pull requests vers `main` sont ouvertes à ta demande, et je ne fusionne jamais moi-même.
- **H-003** (validée) — `nemesis` est un nom de code technique, utilisé dans les identifiants internes. Le nom public n'est jamais écrit en dur ; il passe par la clé `app.name`. L'identifiant d'application Android, définitif une fois publié, sera fixé avant la première publication sur le Play Store, donc avec le nom public.
- **H-004** (validée) — La phase 0 ne comporte ni production ni données personnelles réelles : uniquement l'environnement de développement local, la CI, des données ouvertes (OSM, GTFS) et des fixtures fictives.

## Produit et expérience utilisateur

- **H-005** (validée) — Textes en français de Côte d'Ivoire, avec tutoiement et les formats « 300 F », « 6 h 30 » et « 10 à 20 min » (partie 10.4). Ces choix seront validés en tests utilisateurs.
- **H-006** (validée) — Corridor pilote : sans données de l'AMUGA, je compare les deux candidats de la partie 7.3 sur le GTFS 2023 (lignes, fréquences, gares, couverture OSM) et je présente une recommandation chiffrée ; la décision te revient (partie 15.6). Point d'attention : les deux candidats passent par Adjamé, dont l'accès est interdit aux gbakas depuis mars 2025, soit après la dernière mise à jour du GTFS (janvier 2024).
- **H-007** (validée) — Deux usages, deux jeux :
  - **tests automatiques** : ville entièrement fictive, « Lagune-Fictive », sur une géographie synthétique, avec des noms inventés impossibles à confondre avec des lieux réels ; chaque enregistrement porte `is_fictional = true` ;
  - **prototype pour les tests UX** : lieux et repères réels issus d'OSM (source autorisée par la partie 7), mais gares, lignes, prix et attentes fictifs, marqués « (fictif) », sous le bandeau « DONNÉES FICTIVES ».

## Technique (provisoire : chaque point est tranché par un ADR en phase 0)

- **H-008** (validée) — Mobile : Flutter, Android d'abord, `minSdk 26`, SQLite via drift, MapLibre. Le poids de l'APK et le démarrage à froid sont mesurés sur le prototype avant de figer l'ADR-001 ; Kotlin natif reste l'alternative si le budget de la partie 9.3 n'est pas tenable.
- **H-009** (validée) — API principale : TypeScript et NestJS, REST `/v1`, OpenAPI 3.1. L'ADR-002 compare avec Go. La diffusion temps réel est isolée dans un module remplaçable si les tests de charge l'exigent.
- **H-010** (validée) — Itinéraires : l'option B (moteur McRAPTOR en Rust, côté serveur et sur le téléphone) est la cible ; un spike de deux jours compare A et B avant l'ADR-003, comme le demande la partie 8.1.
- **H-011** (validée) — Back-office : React, TypeScript et MapLibre GL JS. Pages web légères : HTML rendu côté serveur, sans framework JavaScript, moins de 100 Ko.
- **H-012** (validée) — Python (FastAPI) pour l'apprentissage automatique ; Python aussi pour les pipelines de données et le simulateur. OSM est importé avec osm2pgsql (configuration « flex ») ; les tuiles sont générées avec Planetiler en PMTiles ; le GTFS est validé avec le validateur canonique de MobilityData.
- **H-013** (validée) — PostgreSQL 16 avec PostGIS et pg_trgm ; partitionnement natif par jour (TimescaleDB pourra être réévalué par ADR) ; Redis ; NATS JetStream. Migrations en SQL brut versionné, indépendantes du langage de l'API.
- **H-014** (validée) — Géométries stockées en WGS 84 (EPSG:4326) ; calculs métriques dans une projection locale déclarée par ville (EPSG:32630, UTM 30 N, pour Abidjan).
- **H-015** (validée) — Monorepo conforme à la partie 9.7, avec un ajout signalé : `tools/simulator` pour le simulateur par agents. Outils : pnpm (TypeScript), Cargo (Rust), uv (Python), Flutter ; un `Makefile` racine (`make dev`, `make check`).
- **H-016** (validée) — Séparation stricte entre identité et mobilité : deux schémas PostgreSQL et deux rôles distincts. Le numéro de téléphone est stocké haché (HMAC avec secret serveur) pour les recherches, et chiffré pour l'envoi des SMS. Le journal d'audit est en ajout seul, chaîné par empreintes.

## Données

- **H-017** (validée) — Le GTFS « Abidjan 2023 » (dernière mise à jour en janvier 2024) sert d'a priori et de banc d'essai ; il n'est jamais présenté comme l'état actuel du réseau. Chaque donnée porte sa source et sa date de validité.
- **H-018** (validée) — En l'absence de prix observé dans une source autorisée, l'application affiche « prix inconnu ». Aucun prix n'est inventé ni extrapolé sans observation.
- **H-019** (validée) — Les licences des jeux importés sont vérifiées et consignées dans `docs/DATA.md` avant tout usage public. Point à faire valider par un juriste : l'ODbL d'OpenStreetMap impose le partage à l'identique des bases dérivées utilisées publiquement, ce qui peut concerner notre base réseau.

## Vie privée et cadre légal

- **H-020** (validée) — Aucune donnée personnelle réelle n'est collectée avant le dépôt de la déclaration ARTCI ou un avis juridique écrit. En phase 0, les requêtes réelles et les tests de maquettes passent par des fiches anonymes (ni numéro, ni position, ni nom) ; le prototype WhatsApp « magicien d'Oz », qui voit des numéros et des positions, attend cette validation. Valeurs par défaut reprises de la partie 12.2, toutes à valider : k = 20 ; positions brutes 30 jours ; observations brutes 12 mois ; journaux techniques 90 jours.

## Environnement de développement

- **H-021** (constat du 2026-11-04) — La politique réseau de l'environnement cloud refuse : `download.geofabrik.de`, `hub.tumidata.org`, `transit.land`, `api.transitland.org`, `dl.google.com`, ainsi que `github.com` hors de ce dépôt (téléchargements du validateur GTFS et des outils PMTiles). Sont accessibles : Docker Hub, Maven Central, npm, PyPI, crates.io, pub.dev et le stockage des versions de Flutter. Sans élargissement de cette politique, les imports de données et le build Android ne sont exécutés et vérifiés que dans GitHub Actions.
  - Complément du 2026-11-04 (I0.7) : `gitlab.com` et `raw.githubusercontent.com` sont accessibles. Le GTFS « Abidjan 2023 » se télécharge donc depuis son dépôt d'origine, et sa chaîne d'import se vérifie aussi dans l'environnement cloud. Restent bloqués pour OSM : Geofabrik, `download.openstreetmap.fr`, Overpass, `osmdata.openstreetmap.de`, ainsi que Mobility Database. L'import OSM réel et les tuiles réelles ne se vérifient qu'en CI ; le GHCR (validateur, Planetiler) aussi.

## Données de terrain (I0.2)

- **H-022** (proposée) — Conventions des fichiers de terrain :
  - les schémas TOML du paquet `nemesis_pipelines.terrain` sont la source unique ; modèles CSV et dictionnaire en sont générés ;
  - les modèles sont en UTF-8 avec BOM et séparateur « ; », pour s'ouvrir tels quels dans un tableur réglé en français ; le validateur accepte aussi « , » et les décimales à virgule ;
  - les codes sont sans accents ; plusieurs valeurs dans une cellule se séparent par « + » ;
  - deux dossiers s'ajoutent à l'arborescence de la partie 9.7 : `data/terrain` (modèles et collecte) et `tools/terrain` (rendu des fiches en PDF).
- **H-023** (proposée) — Pseudonymes :
  - enquêteurs E01…, validateurs V01…, participants P01… dans chaque session ;
  - pour les enquêteurs et validateurs, la correspondance avec leur identité (contrat, paiement) est tenue par le coordinateur, hors du dépôt ; pour les participants, elle n'existe nulle part ;
  - aucun enregistrement audio, vidéo ni photo de personne en phase 0 ;
  - participants de 18 ans et plus uniquement.
- **H-024** (proposée) — Les textes de consentement vouvoient, car on s'adresse à des inconnus dans un lieu public. Le tutoiement de l'appli (H-005) n'est pas concerné. La traduction en dioula est faite oralement en attendant une version écrite validée.
- **H-025** (proposée) — Quotas proposés pour les collectes, à recalibrer après les premiers jours de terrain. Le détail figure dans chaque protocole :
  - 300 requêtes, sur au moins 6 lieux d'enquête dans au moins 4 communes, avec au moins un tiers de requêtes dites ;
  - 200 trajets, dont au moins 150 touchant le corridor pilote, avec des heures et des types de jour répartis ;
  - pour les tests de maquettes, en plus des minimums de la partie 10.1 : au moins 1 personne qui préfère le dioula, 2 femmes et 1 téléphone basique par tour ;
  - pour le test des icônes, au moins un tiers de personnes qui lisent difficilement.
- **H-026** (proposée) — Le jeu de 300 requêtes sert uniquement au test. On vise 400 requêtes pour développer la clé phonétique et les synonymes sur 100 requêtes distinctes ; sinon, on répartit en 100 pour le développement et 200 pour le test, et on le signale.

## Base de données (I0.4)

- **H-027** (proposée) — La ville fictive « Lagune-Fictive » est placée en pleine mer, dans le golfe de Guinée (autour de 2° N et 4° O). Ses coordonnées ne peuvent donc jamais coïncider avec un lieu réel, tout en restant dans la projection UTM 30 N d'Abidjan. Cela précise la « géographie synthétique » de H-007.
- **H-028** (proposée) — Les comptes de connexion de développement (`nemesis_*_dev`) ont un mot de passe local par défaut, modifiable dans `.env`. Ils n'existent que dans l'environnement Docker Compose et n'exposent leurs ports que sur 127.0.0.1. En production, les comptes sont créés par l'exploitation, hors du dépôt.


## Imports de données (I0.7)

- **H-029** (proposée) — Emprise de travail d'Abidjan : celle des arrêts du GTFS 2023, élargie d'environ 2 km, soit de −4,25 à −3,70 en longitude et de 5,18 à 5,53 en latitude. Elle couvre le terrain de la collecte de 2023 : les 13 communes du district et Grand-Bassam, selon le dépôt d'origine. Elle borne la promotion des lieux, le rapport d'écarts et l'extrait de tuiles (`data/pipelines/sources.toml`). À remplacer par la limite administrative du district tirée d'OSM, ou par l'emprise du corridor pilote quand il sera choisi.
- **H-030** (proposée, **décision du porteur**) — Le GTFS « Abidjan 2023 » est publié sous licence **CC BY-NC 4.0** (pas d'usage commercial), selon le README de son dépôt d'origine. Tant qu'une autorisation écrite de DigitalTransport4Africa n'est pas obtenue :
  - il ne sert qu'à l'évaluation interne : validation, rapport d'écarts, banc d'essai du moteur d'itinéraires ;
  - il reste dans le schéma intermédiaire `staging_gtfs`, que l'API ne peut pas lire ;
  - la base refuse toute ligne du réseau qui le cite comme source (`usage = 'evaluation'`, code d'erreur NM004).

  Le dépôt invite à écrire à DigitalTransport4Africa pour d'autres permissions : c'est une démarche de partenariat (15.6), à faire valider par un juriste avec H-019. Le même GTFS a été produit à partir d'OSM : ce qui en reste à jour dans OSM est utilisable sous ODbL.
- **H-031** (proposée) — Budget du fond de carte : F-12 donne au pack d'Abidjan 15 Mo sans fond et 60 Mo avec. Le fond léger a donc au plus 45 Mo, en mégaoctets de 10⁶ octets (lecture la plus stricte). La mesure est faite à chaque exécution de la chaîne réelle (ADR-009).

## Moteur d'itinéraires (I0.9)

- **H-032** (proposée) — Paramètres du moteur v0, choisis sans données de terrain et à recalibrer sur la suite de trajets de référence (Q-03) :
  - la marche est comparée par tranches de 250 m (environ 3 min) dans la recherche et dans le Pareto des options : une différence plus petite ne justifie pas une option de plus ;
  - « Le plus simple » compte la marche par tranches de 375 m (5 min) après le nombre de véhicules ;
  - une option sans étiquette n'est montrée que si son p80 reste sous 1,5 × le meilleur p80 + 15 min, et au plus 5 options sont affichées ;
  - marche bornée à 1,5 km pour l'accès et la sortie, 500 m pour une correspondance, 2 km pour un trajet tout à pied ; points rattachés au graphe piéton à moins de 200 m ;
  - régime A modélisé par une loi log-normale ajustée sur le p50 et le p80 des profils, en attendant la loi Gamma d'ALGORITHMES.md (section 1.2) ;
  - prix estimés en condition « normale » seulement.

## Simulateur par agents (I0.10)

- **H-033** (proposée) — Le simulateur et ses conventions, en attendant les données du pilote :
  - **paramètres fictifs** : le scénario `tools/simulator/scenarios/corridor-g1.toml` reprend les arrêts, les intervalles et les tarifs du jeu fictif. Les débits de passagers (jusqu'à 4,2 par minute à la gare en pointe), l'effet de la pluie (30 % de véhicules en moins, 15 % de passagers en plus), la patience au bord de la route (20 à 60 min), l'occupation du bus et les comportements de signalement (12 % d'usagers de l'appli, erreurs, retards, 3 fraudeurs) sont choisis pour produire une file en pointe. Ce ne sont pas des mesures ;
  - **champs des signalements** (`payload` de `ContributionRequest`) : `file` → `level` ; `vehicules_presents` → `vehicles` (`aucun`, `1_2`, `3_plus`) ; `attente_reelle` → `wait_s` ; `prix_paye` → `amount_xof` ; `vehicule_plein` → rien. À reprendre dans le contrat de l'API quand le traitement des contributions sera écrit ;
  - **gare de tête** : 3 véhicules en attente au plus ; au-delà, un véhicule qui arrive repart. *T*max compte depuis le premier passager monté ;
  - **montée au bord de la route** : en bousculade par défaut, l'option « file ordonnée » existe. L'ordre réel est à observer sur le terrain (protocole des Éclaireurs), car il change la formule du régime B (ALGORITHMES.md 1.3).
