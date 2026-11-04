# Phase 0 — Fondations : plan détaillé

Statut : **validé le 2026-11-04, en cours**. Avancement : voir `docs/ETAT.md`.
Référence : partie 15.1 du cahier des charges (`docs/CAHIER_DES_CHARGES.md`).

## Objectif et critère de fin

Poser les fondations qui permettent de construire le MVP sans refonte : décisions structurantes documentées, dépôt outillé, modèle de données complet, données ouvertes importées et contrôlées, moteur d'itinéraires utilisable, prototype testable avec de vrais usagers, kit de terrain prêt.

**Terminé quand** (repris de la partie 15.1) : un itinéraire réel est calculé de bout en bout sur les données importées, l'intégration continue est au vert et chaque décision structurante a son ADR.

## Correspondance avec les livrables de la partie 15.1

| Livrable 15.1 | Incréments |
|---------------|------------|
| 1. Documents et premiers ADR | I0.3, I0.8 (ADR-003), I0.11 (ADR-001) |
| 2. Monorepo, CI verte, `docker compose up` | I0.1, I0.4 |
| 3. Schéma complet et OpenAPI v0 | I0.4, I0.6 |
| 4. Pipelines OSM, GTFS, tuiles et rapports | I0.7 |
| 5. Fixtures fictives et simulateur v0 | I0.5, I0.10 |
| 6. Moteur d'itinéraires en ligne de commande | I0.8, I0.9 |
| 7. Prototype cliquable et protocoles UX et WhatsApp | I0.2, I0.11 |
| 8. Kit de campagne terrain | I0.2, I0.12 |

## Ordre de construction

Le kit de terrain est avancé en deuxième position, alors que la partie 15.1 le cite en dernier. Raison : la collecte des 300 requêtes et des 200 trajets de référence demande des semaines sur place ; elle doit commencer pendant que le code avance, sinon le MVP démarre sans jeu d'évaluation.

### I0.1 — Socle du dépôt et intégration continue

- Arborescence de la partie 9.7, plus `tools/simulator` (ajout signalé, H-015), `docs/DECISIONS/` et `docs/UX/`.
- Outillage par écosystème : pnpm pour TypeScript, Cargo pour Rust, uv pour Python, Flutter ; `Makefile` racine (`make check`, `make test`, `make dev`).
- GitHub Actions : une tâche par composant, déclenchée selon les chemins modifiés ; lint et tests ; audit des dépendances (`cargo audit`, `pnpm audit`, `pip-audit`) ; Trivy sur le dépôt.
- Fichiers de base : `README.md`, `CHANGELOG.md`, `LICENSE` (selon Q-06), `SECURITY.md`, `.editorconfig`, modèle de pull request reprenant la « définition de terminé » de la partie 15.5.
- **Terminé quand** : chaque composant a au moins un test, `make check` passe en local, la CI est verte.

### I0.2 — Kits de terrain prioritaires (pour démarrer la collecte tôt)

- Gabarit des **300 requêtes réelles** (F-01) : fiche anonyme (formulation exacte, commune, type de lieu, réussite attendue), consignes d'enquête, schéma CSV.
- Gabarit des **200 trajets de référence** (partie 14.1) : origine, destination, heure, type de jour, réponses jugées acceptables, justification, validateurs ; règle de notation du « réalisme ».
- **Protocole de test des maquettes** (partie 10.1) : 5 à 8 participants dont au moins 2 qui lisent difficilement et 1 personne âgée ; tâches tirées des parcours 1, 2, 3, 5 et 7 ; test de reconnaissance des icônes (20 personnes, seuil de 85 %) ; gabarit `docs/UX/tests-AAAA-MM-JJ.md`.
- Consentement oral lu au participant, sans nom ni numéro (H-020).
- Un script de la CI valide les CSV remplis contre leur schéma.
- **Terminé quand** : les fiches sont imprimables et le validateur CSV tourne en CI.
- **Réalisé** (2026-11-04) : protocoles dans `docs/TERRAIN/` et `docs/UX/`, fiches HTML et PDF, validateur `nemesis-terrain` (schémas, modèles et dictionnaire générés), exemples fictifs. Ajouts à l'arborescence : `data/terrain`, `tools/terrain` (H-022). En plus du plan : un test de reconnaissance des icônes avec son rapport, et une règle de notation du réalisme avec des « pièges ».

### I0.3 — Documents fondateurs et ADR

- `docs/ARCHITECTURE.md` : contexte et conteneurs (format C4, niveaux 1 et 2) ; flux observation → agrégation → état publié ; parité des itinéraires en ligne et hors ligne ; canaux sans smartphone.
- ADR « proposés », chacun avec options, compromis, coût, réversibilité et justification :
  - ADR-001 : stack mobile, Flutter ou Kotlin natif (figé en I0.11 après mesure) ;
  - ADR-002 : langage de l'API, NestJS ou Go ;
  - ADR-003 : moteur d'itinéraires, option A ou B (figé en I0.8 après le spike) ;
  - ADR-004 : hébergement et transfert de données hors du pays, centre de données local ou autorisation de l'ARTCI (décision qui te revient, partie 15.6) ;
  - ADR-005 : base de données et partitionnement ;
  - ADR-006 : temps réel vers les clients (SSE ou WebSocket, deltas en Protocol Buffers) ;
  - ADR-007 : extension GTFS propre au projet (files, véhicules en gare, prix observés, fiabilité).
- `docs/DATA.md` : sources, licences, attribution, règles de fraîcheur, politique des fixtures, extension GTFS v0.
- `docs/PRIVACY.md` : registre des traitements v0, analyse d'impact de la géolocalisation (brouillon), brouillon du dossier ARTCI ; chaque point juridique est marqué « à valider par un juriste ».
- `docs/COUTS.md` v0 : modèle de coût par palier (pilote de 50 usagers, 10 000, 100 000 et 300 000 utilisateurs actifs par jour), avec formules et sources ; tout tarif non vérifié est marqué comme tel.
- `docs/ALGORITHMES.md` v0 : formules des régimes d'attente A, B et C et paramètres.
- **Terminé quand** : les documents sont relus par toi ; ADR-002, 004, 005, 006 et 007 sont au statut « proposé ».
- **Réalisé** (2026-11-04), en attente de ta relecture :
  - `docs/ARCHITECTURE.md`, avec diagrammes Mermaid validés ;
  - `docs/DATA.md`, `docs/PRIVACY.md`, `docs/COUTS.md`, `docs/ALGORITHMES.md` ;
  - ADR-001 à ADR-007, tous au statut « proposé » ;
  - un vérificateur de liens de la documentation, exécuté en CI.

  Deux écarts au cahier des charges sont signalés :
  - ADR-006 : la carte en direct passe par interrogation périodique, et non par connexion permanente ;
  - ALGORITHMES.md, section 1.7 : le conseil « remonter à la gare » tient compte du trajet entre la gare et le point de départ.

### I0.4 — Schéma de base de données et environnement local

- Migrations SQL couvrant toutes les entités de la partie 7.2 ; `city_id` partout (multi-villes) ; énumérations de modes et de types d'arrêts conformes au cahier des charges.
- `is_fictional` sur toutes les tables métier ; une contrainte empêche la publication d'une version de réseau contenant des enregistrements fictifs.
- Identité et mobilité dans deux schémas, avec deux rôles distincts (H-016) ; `audit_log` en ajout seul, chaîné par empreintes.
- `observation` et `position_event` partitionnées par jour ; fonction de maintenance qui crée et purge les partitions selon les durées de conservation.
- `docker-compose.yml` : PostgreSQL 16 + PostGIS, Redis (Valkey), NATS JetStream, serveur de tuiles statique (requêtes par plages d'octets pour PMTiles) ; migrations et fixtures appliquées au démarrage.
- **Terminé quand** : la base se crée de zéro par `docker compose up` ; les tests de schéma (contraintes, rôles, partitions, refus des fixtures à la publication) passent en CI.
- **Réalisé** (2026-11-04) :
  - sept migrations dbmate : 40 tables dans quatre schémas, trois tables partitionnées par jour, rôles, audit chaîné, maintenance ;
  - `docker-compose.yml` avec PostGIS, Valkey, NATS, Caddy et le service `migrate` ;
  - jeu de départ fictif ;
  - 23 tests du schéma (`make db-test`) et un workflow de CI dédié.

  Choix signalés :
  - Valkey à la place de Redis, pour la licence ;
  - versionnement du réseau décrit dans l'ADR-008 ;
  - planification quotidienne de la maintenance reportée à la phase 1 : en développement, elle est lancée au démarrage.

### I0.5 — Jeu `fixtures_fictives`

- Ville « Lagune-Fictive » : géographie synthétique, 3 communes, environ 8 gares, environ 12 lignes couvrant gbaka, wôrô-wôrô communal et intercommunal, bus et bateau-bus ; profils de service par tranche de 15 minutes ; prix ; repères avec alias et variantes orales.
- Fourni au format GTFS (`frequencies.txt`, `continuous_pickup`, GTFS-Fares v2) avec l'extension du projet ; généré par un script à graine fixe ; chaque enregistrement porte `is_fictional = true`.
- **Terminé quand** : le validateur GTFS de MobilityData passe sur le jeu, avec un rapport conservé en CI ; le jeu se charge en base.

### I0.6 — OpenAPI v0, Protocol Buffers et squelette de l'API

- Contrat OpenAPI 3.1 pour `/v1` : recherche de lieux, calcul d'itinéraire, détail de gare, état en direct par zone, contributions, incidents, packs hors ligne, compte, récompenses (bouchon), back-office, flux partenaires.
- **Règle 2 dans le contrat** : tout objet d'estimation (attente, prix, durée, état de file) porte obligatoirement `observed_at`, `confidence` et `source` ; une estimation sans fraîcheur est invalide au regard du schéma.
- Clés d'idempotence sur toutes les écritures, ETags, pagination, limites de débit déclarées.
- Protocol Buffers des deltas temps réel dans `packages/proto`, contrôlés par `buf lint` et `buf breaking`.
- Squelette NestJS qui sert la recherche de lieux et le détail de gare sur les fixtures ; tests de contrat générés à partir du schéma.
- **Terminé quand** : le linter OpenAPI passe ; les tests de contrat passent contre le squelette.

### I0.7 — Pipelines d'import et rapports

- **OSM** : extrait Côte d'Ivoire de Geofabrik, empreinte vérifiée, import par osm2pgsql (configuration « flex ») : voirie, réseau piéton, points d'intérêt transformés en `place` avec alias, relations de lignes (réseaux de gbakas et de wôrô-wôrôs cartographiés par Jungle Bus).
- **GTFS « Abidjan 2023 »** : téléchargement, empreinte, validation par MobilityData (rapport HTML et JSON), import dans un schéma intermédiaire avec provenance (source, licence, date de récupération).
- **Rapport d'écarts GTFS ↔ OSM** : arrêts appariés à distance seuil, lignes appariées par nom et par géométrie, liste des écarts ; sortie en Markdown et en GeoJSON pour revue.
- **Tuiles** : Planetiler vers PMTiles pour la Côte d'Ivoire, puis extrait pour Abidjan ; mesure de la taille face au budget F-12 (moins de 60 Mo avec fond léger).
- Exécution par `make data-import` et par une tâche de CI planifiée chaque semaine (volume trop lourd pour chaque pull request).
- **Dépend de Q-08** : hôtes aujourd'hui bloqués dans mon environnement.
- **Terminé quand** : les rapports de validation et d'écarts sont produits ; les volumes importés sont consignés dans `docs/DATA.md` ; les erreurs du validateur sont listées, jamais corrigées en silence.

### I0.8 — Spike du moteur d'itinéraires (deux jours) et ADR-003

- **Option A** : OpenTripPlanner 2 sur le GTFS d'Abidjan et OSM. À vérifier : prise en charge de `frequencies.txt`, de `continuous_pickup` et `continuous_drop_off`, temps de réponse, mémoire, possibilité de réévaluer les étapes avec l'attente estimée en direct.
- **Option B** : RAPTOR multicritère minimal en Rust sur un réseau à fréquences, où le coût de montée est l'attente estimée ; points de montée virtuels tous les 150 à 300 m pour la montée continue.
- Mêmes 20 couples origine-destination pour les deux options ; mesures comparées ; ADR-003 figé.
- **Terminé quand** : l'ADR-003 est rédigé avec les mesures.

### I0.9 — Moteur d'itinéraires en ligne de commande

- Interface unique `RoutingEngine` (partie 8.1).
- `routing plan --from <lat,lon|lieu> --to <lat,lon|lieu> --at <date-heure> --data <pack>` renvoie un JSON : options étiquetées « Le moins cher », « Le plus rapide », « Le plus simple » issues d'un front de Pareto, sans options dominées ni quasi-doublons ; durées aux 50e et 80e centiles par Monte-Carlo (500 tirages) ; source de chaque étape.
- Attente v0 : régime B à partir des intervalles du GTFS ; régime A paramétré sur les fixtures uniquement, faute de données réelles.
- Marche sur le graphe piéton OSM (Dijkstra borné à environ 1,5 km).
- Tests par propriétés : aucune option dominée ; ajouter une ligne ne dégrade jamais la meilleure option ; symétrie raisonnable entre aller et retour.
- **Terminé quand** : un itinéraire réel est calculé de bout en bout sur les données importées, ce qui est le critère de fin de la phase ; latence mesurée ; tests au vert en CI sur les fixtures.

### I0.10 — Simulateur par agents v0

- Simulation à événements discrets d'un corridor : arrivées de passagers (processus de Poisson par tranche de 15 minutes), départs au remplissage (régime A), passages en ligne avec probabilité de place libre (régime B), signalements bruités, retardés ou frauduleux, effet de la pluie.
- Sorties : flux d'observations au format de l'API, plus la vérité terrain, pour évaluer l'agrégation et la calibration.
- Test clé : les formules fermées des régimes A et B (partie 8.2) sont confrontées au simulateur ; la couverture du 80e centile doit tomber dans la plage attendue.
- **Terminé quand** : une journée de pointe se simule en moins d'une minute, de façon reproductible avec une graine fixe.

### I0.11 — Prototype cliquable Flutter et ADR-001

- Trois onglets (Trajet, Carte, Moi) et le bouton flottant Signaler ; écrans d'accueil (« Tu vas où ? »), de résultats (trois cartes d'option), pas à pas, fiche gare, contribution en deux pressions, feuille « Pourquoi cette estimation ? ».
- Clés de traduction ARB (fr-CI) dès le premier écran ; jetons de design ; bandeau « DONNÉES FICTIVES » dans les builds de développement ; fonctionne hors ligne sur les données embarquées, sans backend.
- Bases de l'accessibilité : zones tactiles de 48 dp, texte de 16 sp, tests de référence visuels à 100 % et 200 % de taille de texte.
- Mesure du poids de l'APK arm64 en release, avec carte, base SQLite et bibliothèque native du moteur ; l'ADR-001 est figé avec ces chiffres.
- Protocole du prototype WhatsApp « magicien d'Oz » : scripts, modèles de réponse, délai de réponse, journal sans identité ; exécution soumise à Q-07.
- **Terminé quand** : l'APK est construit en CI ; les tests de widgets et de référence visuels sont au vert ; un test de fumée tourne sur émulateur Android 8 (API 26) en CI.

### I0.12 — Kit complet de la campagne « Éclaireurs »

- Spécification du mode « relevé » : trace GPS, arrêts, prix payés, photos (règle : ni visage ni plaque identifiables), comptage des départs et des files par tranche de 15 minutes ; fonctionnement hors ligne ; export.
- Fiches de collecte : recensement des gares, relevé de ligne, prix, comptages.
- Protocole qualité : double relevé sur 10 % des lignes, mesure d'accord entre relevés, seuils d'acceptation.
- **Terminé quand** : les fiches sont imprimables et les formats d'échange sont validés par un script en CI.

### I0.13 — Clôture de la phase

- Démo reproductible en moins de 5 minutes ; mises à jour de `docs/ETAT.md` et de `CHANGELOG.md` ; rapport de phase : fait, lancement, tests, limites, prochaine étape.

## Désaccords entre casquettes, tranchés

1. **Recherche UX ou vie privée.** La recherche veut des requêtes réelles et un prototype WhatsApp dès la phase 0. La vie privée interdit toute collecte réelle avant la déclaration ARTCI. **Tranché** : fiches anonymes en phase 0 ; le prototype WhatsApp, qui manipule des numéros et des positions, attend un avis juridique (Q-07). Coût : quelques semaines de retard sur l'apprentissage par WhatsApp.
2. **Ingénieur mobile ou architecte.** Flutter, MapLibre et une bibliothèque Rust embarquée donnent une base de code unique et des itinéraires identiques en ligne et hors ligne. En face : le budget de 20 Mo et le téléphone Android 8 à 2 Go. **Tranché** : Flutter par défaut, mais l'ADR-001 n'est figé qu'après mesure sur le prototype (I0.11). Kotlin natif redevient l'option si le budget n'est pas tenable.
3. **Data scientist ou product manager.** Le GTFS 2023 permet d'avancer tout de suite, mais il précède des changements majeurs : interdiction d'Adjamé aux gbakas en mars 2025, réorganisation par l'AMUGA en octobre 2026. **Tranché** : il sert de banc d'essai et d'a priori, jamais d'état présenté comme actuel ; la campagne terrain est la vraie source.
4. **Ingénieur backend ou recrutement.** Go consomme moins pour 50 000 connexions simultanées ; TypeScript est plus facile à recruter et partage ses types avec le back-office. **Tranché** : NestJS par défaut, temps réel isolé dans un module remplaçable ; à confirmer par l'ADR-002 et les tests de charge.
5. **Réalisme des fixtures ou règle 1.** Les tests UX gagnent à montrer des lieux connus ; la règle 1 interdit d'inventer des données réelles. **Tranché** : lieux réels issus d'OSM, gares, lignes et prix fictifs et marqués (H-007).

## Simplifications signalées (règle 1.3.8)

| Exigence | Ce que fait la phase 0 | Raison | Retour prévu |
|----------|------------------------|--------|--------------|
| Pénalités de marche : traversées dangereuses, zones inondées (8.1) | Graphe piéton sans pénalités | Pas encore de données d'incidents ni de traversées | Phase 1, tranche 1 |
| Attente en direct, régimes A et C (8.2) | Régime B historique ; régime A sur fixtures seulement | Aucune observation réelle avant la phase 1 | Phase 1, modèles v1 |
| Estimation des prix (8.3) | Prix du GTFS s'ils existent, sinon « prix inconnu » | Règle 1 : pas d'invention | Phase 1 |
| Analyse statique mobile MobSF, tests d'intrusion (9.2) | Trivy et audits de dépendances seulement | Peu de code mobile à analyser en phase 0 | Phase 1, durcissement |
| Infrastructure en code Terraform et Ansible (9.2) | Docker Compose seulement | Pas d'infrastructure cible tant que l'ADR-004 n'est pas tranché | Phase 1 |
| Observabilité complète : OpenTelemetry, Prometheus, Grafana, Loki (9.2) | Instrumentation OpenTelemetry dans les squelettes, sans pile de collecte | Rien à superviser en phase 0 | Phase 1 |
| Tests de charge k6 (9.4) | Aucun | Pas encore de service à charger | Phase 1, durcissement |
| 300 requêtes et 200 trajets réels | Gabarits et protocoles ; collecte selon Q-03 | Dépend d'une présence sur le terrain | Dès qu'une personne est disponible |

## Risques principaux

- **Données vieillissantes** : le GTFS précède des changements majeurs ; le terrain doit commencer tôt (I0.2).
- **Accès réseau de l'environnement** (Q-08) : sans élargissement, imports et build Android ne sont vérifiables qu'en CI, avec des boucles de correction plus lentes.
- **Budget de poids de l'APK** : à mesurer tôt (I0.11) ; il conditionne le choix de stack.
- **Compétences locales en Rust** (Q-02) : l'option B est techniquement préférable mais plus rare à recruter à Abidjan ; l'ADR-003 doit en tenir compte.
- **Licences** : ODbL (partage à l'identique) et licence du GTFS à faire valider (H-019).
