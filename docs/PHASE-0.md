# Phase 0 — Fondations : plan détaillé

Statut : validé le 2026-11-04, **terminé le 2026-11-09** : voir le [rapport de phase](RAPPORT-PHASE-0.md). Avancement : voir `docs/ETAT.md`.
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
- **Réalisé** (2026-11-04) : générateur `nemesis-fixtures`, avec une seule description de la ville et une graine fixe.
  - GTFS : 35 arrêts, 12 lignes, 72 courses à fréquences, Fares v2 et huit fichiers `ext_`.
  - Jeu SQL chargé par `docker compose up` (0,3 s, rejouable).
  - Validateur MobilityData 8.0.1 en CI, avec rapport conservé en artefact : 0 erreur, 0 avertissement. Les 3 informations restantes sont attendues : fichiers `ext_`, colonne `is_fictional`, calendrier jusqu'en 2030.
  - 11 tests du générateur.
  - Écart au plan : 27 arrêts informels en plus des 8 gares, pour exercer la montée continue.

### I0.6 — OpenAPI v0, Protocol Buffers et squelette de l'API

- Contrat OpenAPI 3.1 pour `/v1` : recherche de lieux, calcul d'itinéraire, détail de gare, état en direct par zone, contributions, incidents, packs hors ligne, compte, récompenses (bouchon), back-office, flux partenaires.
- **Règle 2 dans le contrat** : tout objet d'estimation (attente, prix, durée, état de file) porte obligatoirement `observed_at`, `confidence` et `source` ; une estimation sans fraîcheur est invalide au regard du schéma.
- Clés d'idempotence sur toutes les écritures, ETags, pagination, limites de débit déclarées.
- Protocol Buffers des deltas temps réel dans `packages/proto`, contrôlés par `buf lint` et `buf breaking`.
- Squelette NestJS qui sert la recherche de lieux et le détail de gare sur les fixtures ; tests de contrat générés à partir du schéma.
- **Terminé quand** : le linter OpenAPI passe ; les tests de contrat passent contre le squelette.
- **Réalisé** (2026-11-04) :
  - contrat OpenAPI 3.1 : 26 opérations, Redocly sans erreur, 15 tests des règles du projet, types TypeScript générés ;
  - contrat `nemesis.live.v1` (deltas par tuile), avec `buf lint` et `buf breaking` ;
  - squelette d'API branché sur PostgreSQL : villes, recherche de lieux, fiche d'arrêt ; problème RFC 9457, ETag, Brotli, rôle `nemesis_api` ;
  - 20 tests de contrat générés et de comportement, contre une base migrée (`make api-test`, job de CI).

  Ajouts au plan :
  - repli JSON du flux SSE des trajets suivis (ADR-006) ;
  - compression Brotli (partie 9.6) ;
  - un seul résultat par gare dans la recherche.

### I0.7 — Pipelines d'import et rapports

- **OSM** : extrait Côte d'Ivoire de Geofabrik, empreinte vérifiée, import par osm2pgsql (configuration « flex ») : voirie, réseau piéton, points d'intérêt transformés en `place` avec alias, relations de lignes (réseaux de gbakas et de wôrô-wôrôs cartographiés par Jungle Bus).
- **GTFS « Abidjan 2023 »** : téléchargement, empreinte, validation par MobilityData (rapport HTML et JSON), import dans un schéma intermédiaire avec provenance (source, licence, date de récupération).
- **Rapport d'écarts GTFS ↔ OSM** : arrêts appariés à distance seuil, lignes appariées par nom et par géométrie, liste des écarts ; sortie en Markdown et en GeoJSON pour revue.
- **Tuiles** : Planetiler vers PMTiles pour la Côte d'Ivoire, puis extrait pour Abidjan ; mesure de la taille face au budget F-12 (moins de 60 Mo avec fond léger).
- Exécution par `make data-import` et par une tâche de CI planifiée chaque semaine (volume trop lourd pour chaque pull request).
- **Dépend de Q-08** : hôtes aujourd'hui bloqués dans mon environnement.
- **Terminé quand** : les rapports de validation et d'écarts sont produits ; les volumes importés sont consignés dans `docs/DATA.md` ; les erreurs du validateur sont listées, jamais corrigées en silence.
- **Réalisé** (2026-11-04) : chaîne `nemesis-data`, `make data-import` et `make data-import-fictif` ([data/pipelines/README.md](../data/pipelines/README.md)).
  - Sources déclarées dans un manifeste. Un téléchargement est refusé sans empreinte, et la provenance de chaque import est inscrite dans `ops.import_run`.
  - **GTFS « Abidjan 2023 »** : pris à son dépôt GitLab d'origine, joignable depuis l'environnement cloud. Il est importé localement en staging (4 834 arrêts, 490 lignes, 974 tracés) et ses volumes sont consignés dans DATA.md.
    - **Sa licence est CC BY-NC 4.0** : pas d'usage commercial. Il sert donc à l'évaluation seulement, et la base refuse de le faire entrer dans le réseau (H-030, à trancher par le porteur).
  - Validateur MobilityData sur le GTFS : tous les avis listés, erreurs d'abord, rien corrigé.
  - OSM : import par osm2pgsql 1.11 (style flex) ; points d'intérêt promus en lieux avec leurs alias.
  - Rapport d'écarts GTFS ↔ OSM en Markdown et GeoJSON. Sur les données fictives, il retrouve exactement les écarts volontaires de l'OSM fictif.
  - Tuiles : schéma Planetiler maison (ADR-009), archive du pays et extrait d'Abidjan, mesurés face aux 45 Mo de F-12 (H-031).
  - Tests : 33 sans base, plus 6 contre une base PostGIS avec osm2pgsql (`make pipelines-test`) et 2 du schéma.
  - CI : la chaîne fictive tourne à chaque modification des pipelines, la chaîne réelle chaque semaine.
    - Geofabrik et GHCR (validateur, Planetiler) sont bloqués dans l'environnement cloud : l'import OSM réel, le validateur, les écarts réels et les tuiles ne tournent qu'en CI.
    - Première exécution réelle verte le 2026-11-04 :
      - GTFS : 0 erreur, 245 avertissements et 974 informations, tous listés ;
      - 4 815 arrêts sur 4 834 et les 974 tracés retrouvés dans OSM, dont 71 tracés différents ;
      - 33 284 lieux promus ;
      - tuiles : 4,5 Mo pour Abidjan, face à un budget de 45 Mo.

      Volumes consignés dans DATA.md.

  Écarts au plan :
  - extrait OSM fictif et GTFS d'identifiants OSM pour tester les rapports sans données réelles ;
  - garde de licence dans la base ;
  - simplification signalée : le fond léger v0 ne dessine pas l'océan (ADR-009).

### I0.8 — Spike du moteur d'itinéraires (deux jours) et ADR-003

- **Option A** : OpenTripPlanner 2 sur le GTFS d'Abidjan et OSM. À vérifier : prise en charge de `frequencies.txt`, de `continuous_pickup` et `continuous_drop_off`, temps de réponse, mémoire, possibilité de réévaluer les étapes avec l'attente estimée en direct.
- **Option B** : RAPTOR multicritère minimal en Rust sur un réseau à fréquences, où le coût de montée est l'attente estimée ; points de montée virtuels tous les 150 à 300 m pour la montée continue.
- Mêmes 20 couples origine-destination pour les deux options ; mesures comparées ; ADR-003 figé.
- **Terminé quand** : l'ADR-003 est rédigé avec les mesures.
- **Réalisé** (2026-11-05) : [ADR-003](DECISIONS/ADR-003-moteur-itineraires.md) accepté. **Option B retenue**, mesures du workflow « Spike du moteur d'itinéraires » à l'appui.
  - **Option B** (`services/routing`) :
    - GTFS avec calendriers, réseau à fréquences, attente du régime B comme coût de montée, points de montée virtuels, RAPTOR ;
    - 0,6 ms par requête en médiane, 12 Mio de mémoire ; 1,9 ms et 43 Mio avec les points virtuels ;
    - le cœur compile pour Android arm64 ;
    - 14 tests, dont un de non-régression sur la cohérence des trajets.
  - **Option A** : OpenTripPlanner 2.10 :
    - 689 ms en médiane, 5,1 s pour la pire requête, environ 1 Gio de mémoire ;
    - fréquences traitées comme un intervalle complet d'attente ;
    - pas de montée entre deux arrêts.
  - **Comparaison avec la même fonction de coût** :
    - équivalence en attentes médianes ;
    - avec des attentes en direct simulées, B gagne plus de 5 min dans 44 requêtes sur 74 (médiane 9,2 min).

  Écarts au protocole :
  - 25 couples tirés des arrêts réels, faute de corridor pilote (5 « bord de route » en plus des 20 prévus) ;
  - réalisme non noté, faute de suite de référence (Q-03) ;
  - mesure sur téléphone reportée en I0.11, seule la compilation Android est vérifiée ;
  - marche de B estimée en ligne droite × 1,3, avec la même règle pour les deux moteurs dans la comparaison.

### I0.9 — Moteur d'itinéraires en ligne de commande

- Interface unique `RoutingEngine` (partie 8.1).
- `routing plan --from <lat,lon|lieu> --to <lat,lon|lieu> --at <date-heure> --data <pack>` renvoie un JSON : options étiquetées « Le moins cher », « Le plus rapide », « Le plus simple » issues d'un front de Pareto, sans options dominées ni quasi-doublons ; durées aux 50e et 80e centiles par Monte-Carlo (500 tirages) ; source de chaque étape.
- Attente v0 : régime B à partir des intervalles du GTFS ; régime A paramétré sur les fixtures uniquement, faute de données réelles.
- Marche sur le graphe piéton OSM (Dijkstra borné à environ 1,5 km).
- Tests par propriétés : aucune option dominée ; ajouter une ligne ne dégrade jamais la meilleure option ; symétrie raisonnable entre aller et retour.
- **Terminé quand** : un itinéraire réel est calculé de bout en bout sur les données importées, ce qui est le critère de fin de la phase ; latence mesurée ; tests au vert en CI sur les fixtures.
- **Réalisé** (2026-11-06) : `routing plan` et `routing bench` ([services/routing/README.md](../services/routing/README.md)), pack ville produit par `nemesis-data pack reel`. **Critère de fin de phase atteint** : le workflow « Itinéraire réel de bout en bout (I0.9) » calcule des itinéraires sur le GTFS 2023 et le graphe piéton de l'extrait OSM d'Abidjan.
  - **Pack réel** : 18 608 arrêts, dont 13 774 points de montée virtuels ; 980 parcours ; graphe piéton de 111 494 nœuds et 141 940 arêtes ; 485 arrêts hors graphe, rejoints en ligne droite ; chargement en 666 ms.
  - **Latence** sur les 25 couples du spike à 3 heures, soit 75 requêtes : 42,8 ms en médiane, 122,5 ms au 95e centile, 131,5 ms au pire, pour un budget de 2 s au 95e centile côté serveur (F-02). Aucune requête sans option.
  - **Exemple** : Adjamé Liberté → Gare de Bassam, un mardi à 7 h 30, une option directe en woro-woro étiquetée « Le plus rapide » et « Le plus simple » : 31 min en médiane, 44 min au 80e centile, 404 m de marche sur le graphe OSM, attente du régime B. Prix inconnu : le GTFS 2023 n'en donne pas.
  - **Fixtures** : 6 tests sur le pack fictif. Flamboyants → Embarcadère Sud y donne quatre options, dont trois étiquetées, avec leurs prix et les régimes A et B dans un même trajet. Le pack fictif sert aussi au déterminisme, à la recherche de lieux, au dimanche, à la nuit et aux dates invalides.
  - **Propriétés** : 3 tests sur des villes en grille tirées de graines fixes : aucune option dominée ; une ligne de plus n'aggrave aucun critère ; aller et retour comparables.
    - Le test de symétrie a révélé un défaut. Une arrivée à pied pouvait éliminer une arrivée en véhicule au même arrêt, et faire perdre des trajets. Chaque arrêt a désormais deux ensembles de Pareto.

  Ajouts au plan, signalés :
  - la marche est comparée par tranches de 250 m. Sans elles, sur le GTFS 2023, le front gardait des trajets à quatre correspondances pour 50 m de marche en moins, et la médiane était à 404 ms ;
  - les options sans étiquette passent un filtre de pertinence, et 5 options au plus sont affichées ;
  - paramètres consignés dans H-032.

  Limites :
  - les prix ne sont connus que sur les fixtures ;
  - la loi log-normale remplace la loi Gamma pour le régime A ;
  - les temps à bord sont ceux du GTFS ;
  - une option à une correspondance pour gagner 240 m de marche reste affichée sans étiquette (Adjamé → Bassam, 48 min contre 31), à calibrer avec la suite de référence.

### I0.10 — Simulateur par agents v0

- Simulation à événements discrets d'un corridor : arrivées de passagers (processus de Poisson par tranche de 15 minutes), départs au remplissage (régime A), passages en ligne avec probabilité de place libre (régime B), signalements bruités, retardés ou frauduleux, effet de la pluie.
- Sorties : flux d'observations au format de l'API, plus la vérité terrain, pour évaluer l'agrégation et la calibration.
- Test clé : les formules fermées des régimes A et B (partie 8.2) sont confrontées au simulateur ; la couverture du 80e centile doit tomber dans la plage attendue.
- **Terminé quand** : une journée de pointe se simule en moins d'une minute, de façon reproductible avec une graine fixe.
- **Réalisé** (2026-11-06) : `nemesis-simulator` ([tools/simulator/README.md](../tools/simulator/README.md)), `make simulation`. **Critère atteint** : une journée de 5 h à 22 h se simule en 0,1 s environ, signalements compris, et la même graine redonne les mêmes fichiers.
  - **Corridor** : la ligne G1 du jeu fictif. Gare de tête en régime A, avec départs au remplissage, *T*max et 3 véhicules en attente au plus. Cinq arrêts de bord de route en régime B, servis par G1 et par le bus B1. Une averse en fin d'après-midi. Sur une journée : 4 326 passagers et une file de 92 personnes au plus.
  - **Sorties** :
    - signalements au format `ContributionRequest`, avec leur réception, leur source et un pseudonyme ;
    - vérité terrain : passagers, passages, départs, file minute par minute, vérité de chaque signalement ;
    - un exemple versionné, validé par ajv contre le contrat OpenAPI.
  - **Signalements** : erreurs de catégorie, attentes déclarées bruitées, retards et envois différés, renvois sous le même identifiant, chef de gare exact, deux types de fraude.
    - La règle des 150 m attrape toutes les files signalées à distance, sans rejeter un seul signalement honnête.
    - Les prix gonflés passent tous : il faudra le contrôle des valeurs atypiques (section 3 d'ALGORITHMES.md).
  - **Test clé**, sur la couverture du p80 et sur 5 journées, détail dans ALGORITHMES.md, sections 1.2 et 1.3 :
    - les formules des régimes A et B sont calibrées quand leurs hypothèses tiennent : débits constants, arrivées de Poisson, personne d'autre en attente ;
    - sur le corridor, le régime A documenté est juste en moyenne (81,8 %), mais par compensation : 91 % sous la pluie. Corrections proposées : intégrer les débits des tranches à venir, et attendre le remplissage du véhicule ;
    - le régime B documenté est trop optimiste dès que d'autres attendent : 61 % ; il faudra des données de terrain sur l'ordre de montée.
  - **Tests** : 19 tests Python et 4 tests de contrat. L'évaluation s'affiche dans le résumé du workflow Python.

  Ajouts au plan, signalés :
  - patience au bord de la route, avec attentes censurées ;
  - plafond de véhicules en attente à la gare ;
  - option d'ordre de montée ;
  - formules corrigées du régime A, et borne « file ordonnée » du régime B ;
  - paramètres consignés dans H-033.

  Limites : un seul corridor dans un seul sens ; l'offre de véhicules à la gare n'est pas un retour de tournée ; pas de congestion ; comportements de signalement inventés.

### I0.11 — Prototype cliquable Flutter et ADR-001

- Trois onglets (Trajet, Carte, Moi) et le bouton flottant Signaler ; écrans d'accueil (« Tu vas où ? »), de résultats (trois cartes d'option), pas à pas, fiche gare, contribution en deux pressions, feuille « Pourquoi cette estimation ? ».
- Clés de traduction ARB (fr-CI) dès le premier écran ; jetons de design ; bandeau « DONNÉES FICTIVES » dans les builds de développement ; fonctionne hors ligne sur les données embarquées, sans backend.
- Bases de l'accessibilité : zones tactiles de 48 dp, texte de 16 sp, tests de référence visuels à 100 % et 200 % de taille de texte.
- Mesure du poids de l'APK arm64 en release, avec carte, base SQLite et bibliothèque native du moteur ; l'ADR-001 est figé avec ces chiffres.
- Protocole du prototype WhatsApp « magicien d'Oz » : scripts, modèles de réponse, délai de réponse, journal sans identité ; exécution soumise à Q-07.
- **Terminé quand** : l'APK est construit en CI ; les tests de widgets et de référence visuels sont au vert ; un test de fumée tourne sur émulateur Android 8 (API 26) en CI.
- **Réalisé** (2026-11-06) : prototype `apps/mobile` ([README](../apps/mobile/README.md)). **Critère atteint** : APK construit en CI, 35 tests de widgets, de références visuelles et d'accessibilité au vert, test de fumée vert sur émulateur Android 8.0 (API 26).
  - **Hors ligne, sans serveur**, sur la ville fictive embarquée (environ 360 Ko de données générées par `nemesis-fixtures`). Les itinéraires viennent du **moteur du serveur**, compilé pour le téléphone (`routing-ffi`, appelé par `dart:ffi`) : mêmes résultats en ligne et hors ligne.
  - **Écrans** :
    - les trois onglets, le bouton Signaler et « Tu vas où ? » ;
    - trois cartes d'option étiquetées, le pas à pas et la fiche gare ;
    - le signalement en deux pressions, gardé dans une file SQLite au format `ContributionRequest`, et « Pourquoi cette estimation ? » ;
    - une carte MapLibre hors ligne, et le bandeau « DONNÉES FICTIVES » partout.
  - **Accessibilité** : zones de 48 dp, libellés, contraste, texte de 16 sp. Les références visuelles de 7 écrans sont prises à 100 % et à 200 % de taille de texte : les débordements à 200 % ont été corrigés, et le test d'accessibilité a révélé des étiquettes de puces invisibles, corrigées aussi.
  - **ADR-001 mesuré, pas figé.**
    - APK arm64 de production : 52,5 Mo, soit environ 21,3 Mo à télécharger, pour un budget de 20 Mo.
    - La carte MapLibre en pèse 10,8 Mo, plus que le surcoût de Flutter (environ 7,8 Mo).
    - Sur l'émulateur, à titre indicatif : démarrage en 0,9 à 1,1 s, mémoire de 70 Mo.
    - La recommandation est de mesurer une carte dessinée en Dart avant de trancher entre Flutter et Kotlin natif. **Décision du porteur.**
  - **Protocole WhatsApp « magicien d'Oz »** : [docs/UX](UX/PROTOCOLE-WHATSAPP-MAGICIEN-OZ.md). Prêt, exécution bloquée par Q-07.
  - **Guide de codage des icônes** : complété avec les icônes du prototype. Choix du prototype consignés dans H-034.

  Ajouts au plan, signalés :
  - le moteur natif dans l'appli, prévu pour la mesure de l'ADR-001, sert aussi aux écrans ;
  - le profil release de Rust a été réglé pour le poids (LTO, symboles retirés) ;
  - le démarrage et la mémoire sont mesurés sur l'émulateur, à titre indicatif.

  Limites :
  - pas de dictée, de lecture vocale, de suivi « Je pars » ni de lieux enregistrés ;
  - une position de démonstration fixe ;
  - des icônes Material provisoires ;
  - les puces de départ (« Partir à 7 h 30 ») sont tronquées à 200 % de taille de texte : rien ne se casse, mais elles sont à retravailler ;
  - la fluidité de la carte avec 200 marqueurs n'est pas mesurée, faute de téléphone de référence (Q-02).

### I0.12 — Kit complet de la campagne « Éclaireurs »

- Spécification du mode « relevé » : trace GPS, arrêts, prix payés, photos (règle : ni visage ni plaque identifiables), comptage des départs et des files par tranche de 15 minutes ; fonctionnement hors ligne ; export.
- Fiches de collecte : recensement des gares, relevé de ligne, prix, comptages.
- Protocole qualité : double relevé sur 10 % des lignes, mesure d'accord entre relevés, seuils d'acceptation.
- **Terminé quand** : les fiches sont imprimables et les formats d'échange sont validés par un script en CI.
- **Réalisé** (2026-11-09) : [protocole de la campagne](TERRAIN/PROTOCOLE-ECLAIREURS.md) et [spécification du mode relevé](TERRAIN/MODE-RELEVE.md). **Critère atteint** : quatre fiches imprimables, en HTML et en PDF ; sept formats d'échange validés par `nemesis-terrain` en CI.
  - **Fiches papier** : recensement d'une gare (1 page), relevé de ligne (2 pages, 32 arrêts), prix payés (1 page), comptage en gare (1 page, 12 tranches de 15 min).
  - **Formats d'échange**, décrits par des schémas dont sont tirés le validateur, les modèles CSV et le dictionnaire :
    - `gares`, `releves_ligne`, `arrets_releves`, `prix`, `comptages`, issus des fiches ou de l'appli ;
    - `photos` et `traces`, issus de l'appli seulement.
  - **Règles vérifiées** :
    - heures dans l'ordre, tranches à 00, 15, 30 ou 45, partis pleins au plus égaux aux départs ;
    - arrêts et traces rattachés à leur relevé ;
    - une photo non vérifiée « ni visage ni plaque » est refusée.
  - **Protocole qualité** : double relevé d'au moins 10 % des lignes, et comptages à deux. `nemesis-terrain accord` mesure l'accord :
    - arrêts communs (Jaccard), ordre, écart de prix ;
    - véhicules et files comptés, catégories de file (kappa de Cohen).

    Il compare aussi les catégories de file choisies à l'œil aux files comptées, pour calibrer les catégories de l'appli. Seuils dans H-035.
  - **Mode relevé de l'appli** :
    - trace GPS pendant un relevé seulement, arrêts en une pression, comptages par tranche avec changement automatique ;
    - photos vérifiées et sans métadonnées EXIF ;
    - hors ligne, avec un export dans les mêmes formats.

    **Spécifié, pas développé** : la trace GPS est une donnée personnelle de l'Éclaireur, et le mode attend Q-07.
  - **Jeu fictif de la campagne**, validé en CI et accepté par `accord --strict`. 11 tests ont été ajoutés.

  Ajouts au plan, signalés :
  - un jeu `photos` dont la règle bloque toute photo non vérifiée ;
  - la calibration des catégories de file par les comptages ;
  - un mode de saisie « appli » dans les schémas ;
  - la règle d'ordre étendue aux heures.

  Limites :
  - aucune collecte réelle tant que l'équipe n'existe pas (Q-03) ;
  - des seuils sans retour du terrain ;
  - l'appariement des arrêts par nom exact ou par distance : deux noms différents sans position ne s'apparient pas.

### I0.13 — Clôture de la phase

- Démo reproductible en moins de 5 minutes ; mises à jour de `docs/ETAT.md` et de `CHANGELOG.md` ; rapport de phase : fait, lancement, tests, limites, prochaine étape.
- **Réalisé** (2026-11-09) : **critère atteint**.
  - **Démo** : `make demo` (`tools/demo/demo.py`), hors ligne et sans base. Elle enchaîne le jeu fictif, un itinéraire fictif, une journée simulée avec la couverture des formules d'attente, les données de terrain, puis l'itinéraire réel si son pack est présent. `DEMO_OPTIONS=--avec-mobile` ajoute les tests de l'appli.
    - Durée : 6 s moteur compilé, 80 s avec la compilation et l'appli. Elle échoue au-delà de 5 minutes.
    - Le workflow « Démo de la phase 0 » la rejoue sur une machine neuve et publie son compte rendu.
  - **Rapport de phase** : [RAPPORT-PHASE-0.md](RAPPORT-PHASE-0.md), avec les décisions en attente du porteur, classées par impact sur la phase 1.
  - ETAT et CHANGELOG mis à jour.

  Limite : la démo ne montre pas l'itinéraire réel en local, faute d'accès à Geofabrik (H-021). Elle renvoie au workflow qui le calcule.

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
| Simulateur par agents (14.1, partie 15) | Un corridor, un sens, offre de véhicules exogène, comportements inventés (H-033) | Suffit à confronter les formules d'attente ; pas de données pour davantage | Phase 1, avec les données du pilote |
| Mesures de l'ADR-001 : démarrage, mémoire, carte à 30 images par seconde (9.3) | Poids mesuré en CI ; démarrage et mémoire sur émulateur, à titre indicatif ; fluidité de la carte non mesurée | Pas de téléphone de référence (Q-02) | Dès que le téléphone est disponible |
| Estimation des prix (8.3) | Prix estimés de l'extension nemesis en condition « normale » (fixtures seulement), sinon « prix inconnu » | Règle 1 : pas d'invention | Phase 1 |
| Loi d'attente du régime A (ALGORITHMES.md 1.2) | Log-normale ajustée sur le p50 et le p80 des profils | Loi Gamma sans paramètres réels à ajuster | Phase 1, modèles v1 |
| Temps à bord par tronçon et par tranche de 15 min (8.1) | Horaires du GTFS, sans tirage aléatoire | Pas de vitesses observées | Phase 1 |
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
