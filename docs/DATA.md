# Données

Version 0 du 2026-11-04 (incrément I0.3), complétée en I0.7 (imports). « La donnée est le produit » (partie 7). Ce document fixe d'où viennent les données, comment on en garde la trace, quand elles cessent d'être fraîches, et comment on les montre honnêtement.

## Règle d'or

Aucune donnée réelle n'est inventée : ni ligne, ni gare, ni prix, ni fréquence, ni horaire, ni nom, ni numéro (règle 1.3.1). Une information absente s'affiche comme absente (« prix inconnu », « pas d'information récente »). Elle n'est jamais remplacée par une valeur plausible.

## Sources autorisées

| Source | Contenu | Usage | Licence et attribution | Statut |
|--------|---------|-------|------------------------|--------|
| OpenStreetMap, extrait Côte d'Ivoire de Geofabrik | Voirie, chemins piétons, points d'intérêt, relations de lignes (réseaux de gbakas et de wôrô-wôrôs cartographiés par Jungle Bus) | Graphe piéton, repères, tracés, fond de carte | ODbL 1.0. Attribution obligatoire dans l'appli : « © les contributeurs d'OpenStreetMap », avec un lien vers openstreetmap.org/copyright. Partage à l'identique des bases dérivées utilisées publiquement : portée à valider par un juriste (H-019) | Import en place (I0.7) : extrait du jour, MD5 publiée par Geofabrik vérifiée ; chaîne hebdomadaire en CI |
| GTFS « Abidjan 2023 », Ewarren Financial Services et DigitalTransport4Africa (dépôt GitLab d'origine ; copies sur TUMI Data Hub et Transitland) | Réseau artisanal seulement : 490 lignes de gbakas et de wôrô-wôrôs, 25 agences, une par mode et par commune, aucune ligne SOTRA. Relevé du 21 novembre au 31 mai 2023 selon le dépôt d'origine, généré à partir d'OSM (identifiants d'arrêts `node/…`) | Évaluation interne seulement (H-017, H-030) : validation, rapport d'écarts, banc d'essai du moteur | **CC BY-NC 4.0 : pas d'usage commercial**. Attribution et mention des modifications exigées. Autorisation à demander à DigitalTransport4Africa (H-030) | Import en place (I0.7) dans `staging_gtfs`, jamais dans le réseau (la base le refuse). Fichier du 2023-07-26, figé au commit `da5d9faf`, SHA-256 épinglée (identique à celle publiée par GitLab). Calendrier du 2023-01-01 au 2023-12-31 : expiré, avant l'interdiction d'Adjamé aux gbakas (mars 2025) et la réorganisation par l'AMUGA (octobre 2026) |
| Flux partenaires : AMUGA, SOTRA, opérateurs lagunaires | Cartographie, arrêts-minute, pôles AIM, GTFS, positions | Réseau officiel, temps réel des bus | Selon chaque convention (7.3) | Conventions à préparer ; connecteurs GTFS et GTFS-Realtime génériques |
| Données de terrain (I0.2) | Requêtes, trajets de référence, relevés des Éclaireurs, recensement des gares | Évaluation, calibration, réseau artisanal | Données du projet, anonymes | Kits prêts ([docs/TERRAIN](TERRAIN/README.md)) ; collecte selon Q-03 |
| Contributions des usagers (F-07) | Files, prix payés, incidents, arrêts déplacés | Temps réel, prix observés, corrections du réseau | Les conditions d'utilisation doivent accorder la licence nécessaire à la publication d'agrégats sous une licence compatible avec l'ODbL ; à rédiger et valider | Phase 1 |
| Météo : SODEXAM en partenariat, ou à défaut une API ouverte | Pluie actuelle et prévue | Modèle d'attente, alertes pluie | Conditions d'usage commercial à vérifier avant intégration (9.1) | Phase 1 ou V2 |
| Tuiles vectorielles produites avec Planetiler à partir d'OSM | Fond de carte léger | Carte en ligne et hors ligne | ODbL pour les données. Schéma maison (ADR-009) : aucune attribution de schéma due, seulement celle d'OSM, inscrite dans les archives | En place (I0.7) : archive du pays et extrait d'Abidjan, mesurés face à F-12 |

**Sources interdites** :
- toute donnée inventée ;
- l'extraction automatique des données d'autres applications (AMUGA mon trajet, Sotra Mobile, Traaf…) sans accord écrit ;
- toute donnée personnelle tirée des réseaux sociaux.

## Provenance et versions

- **Provenance de chaque enregistrement** : il porte sa source (`source_id`), sa date de récupération ou d'observation, sa licence et `is_fictional`.
- **Fichiers bruts téléchargés** : conservés avec leur empreinte SHA-256, vérifiée avant import (`nemesis_pipelines.checksum`).
- **Versions du réseau** : il évolue par `change_request`, puis revue et publication d'une `network_version` datée, avec une date d'effet. On peut comparer deux versions et revenir en arrière (6.3).
- **Reproductibilité** : chaque pack hors ligne et chaque réponse du moteur indiquent la version du réseau utilisée.

## Imports (I0.7)

La chaîne est décrite dans [data/pipelines/README.md](../data/pipelines/README.md). Elle se lance avec `make data-import` (sources réelles) ou `make data-import-fictif`, et chaque semaine en CI (workflow « Imports de données réelles »).

| Étape | Ce qui est fait | Où |
|-------|-----------------|----|
| Téléchargement | Empreinte vérifiée avant tout import, `provenance.json` à côté du fichier | `data/work/sources/<source>/` |
| Validation du GTFS | Validateur MobilityData épinglé ; **tous** les avis listés, erreurs d'abord ; rien n'est corrigé | `rapports/<profil>/validation-gtfs/` |
| GTFS | Chaque ligne de chaque fichier, valeurs intactes, numéro de ligne ; vues typées où une valeur illisible reste nulle | `staging_gtfs` |
| OSM | osm2pgsql 1.11, style flex : voirie, piétons, points d'intérêt, arrêts, lignes, limites | `staging_osm` |
| Lieux | Points d'intérêt nommés de l'emprise (H-029) → `network.place` et ses alias, avec leur référence OSM ; mis à jour, jamais dupliqués ni supprimés en silence | `network.place` |
| Écarts GTFS ↔ OSM | Arrêts et tracés appariés par identifiant OSM, puis par distance, référence et géométrie | `rapports/<profil>/ecarts.md` et `.geojson` |
| Tuiles | Fond léger (ADR-009), archive du pays et extrait de la ville, taille comparée aux 45 Mo de F-12 (H-031) | `data/work/tiles/`, `rapports/<profil>/tuiles.md` |

Chaque exécution est inscrite dans `ops.import_run` : source, URL, empreinte, mode de vérification, date de récupération, date des données, volumes, état.

### Volumes importés

**GTFS « Abidjan 2023 »** (import local du 2026-11-04, fichier du 2023-07-26) :

| Fichier | Lignes |
|---------|--------|
| `agency.txt` | 25 |
| `routes.txt` | 490 |
| `trips.txt` | 980 |
| `stops.txt` | 4 834 |
| `stop_times.txt` | 15 683 |
| `frequencies.txt` | 1 076 |
| `shapes.txt` | 74 504 points, 974 tracés |
| `calendar.txt` | 1 service, tous les jours du 2023-01-01 au 2023-12-31 |
| `feed_info.txt` | version 0.1, éditeur « Data Transport » |
| `calendar_dates`, `transfers`, `pathways`, `levels`, `fare_attributes`, `fare_rules` | vides |

Particularités :
- **temps de parcours en partie forfaitaires** : 271 des 980 courses (28 %) durent exactement 120 min, soit 2 à 6 km/h, ce qui ressemble à une valeur par défaut. Les 709 autres roulent à 11–18 km/h (écart interquartile). Ces temps ne sont pas corrigés ; le moteur les utilise tels quels (ADR-003, spike I0.8) ;
- tous les identifiants d'arrêts sont des nœuds OSM (`node/…`) : le rapport d'écarts apparie d'abord par identifiant ;
- les lignes et les tracés portent des numéros de relations OSM ;
- aucune ligne n'a de nom court : seul le nom long (« gbaka : Adjamé Liberté ↔ Treichville Gare de Bassam ») les identifie.

**Validation du GTFS 2023** (validateur MobilityData de l'image 8.0.1, code pays `ci`, 2026-11-04). Aucun avis n'est corrigé ; tous sont à voir avec le producteur des données.

| Gravité | Code | Occurrences |
|---------|------|-------------|
| Erreur | — | 0 |
| Avertissement | `non_ascii_or_non_printable_char` | 187 |
| Avertissement | `mixed_case_recommended_field` | 55 |
| Avertissement | `expired_calendar` | 1 |
| Avertissement | `feed_expiration_date7_days` | 1 |
| Avertissement | `trip_coverage_not_active_for_next7_days` | 1 |
| Information | `unsorted_stop_times` | 957 |
| Information | `trip_headsign_matches_intermediate_stop` | 17 |

**Extrait OSM de la Côte d'Ivoire** (Geofabrik, publié le 2026-11-04 à 05:19 UTC, récupéré à 17:19 UTC, MD5 vérifiée) :
- fichier de 85,6 Mo : 14 746 594 nœuds, 1 786 874 chemins, 10 108 relations ;
- en staging, dans tout le pays :

| Table | Lignes |
|-------|--------|
| `road` | 217 443 |
| `poi` | 61 855 |
| `transit_stop` | 8 266 : 6 680 quais, 1 001 positions d'arrêt, 362 gares routières, 116 stations, 98 embarcadères, 9 arrêts de bus |
| `route` | 1 257 : 1 241 bus, 14 bateaux, 1 métro, 1 train |
| `route_master` | 611 |
| `route_member` | 80 340 |
| `boundary` | 197 |

Particularité d'OSM : les gbakas et les wôrô-wôrôs y sont des relations `route=bus`, comme les bus. Le mode seul ne les distingue donc pas : le réseau (`network`) et le nom le font.

**Lieux promus dans l'emprise d'Abidjan** (H-029) : 33 284 lieux et 34 455 alias, tous à confiance « faible » et « non vérifiés ».

**Écarts GTFS 2023 ↔ OSM du 2026-11-04** (rapport complet et GeoJSON dans l'artefact du workflow) :

| Mesure | Valeur |
|--------|--------|
| Arrêts du GTFS | 4 834 |
| Appariés, dont par identifiant OSM | 4 815, dont 4 812 |
| Déplacés de plus de 20 m | 14, de 22 m à 852 m |
| Nom différent | 11, dont 3 « [Arret sans nom] » sans nom dans OSM |
| Absents d'OSM | 19 |
| Arrêts d'OSM dans la zone, absents du GTFS | 2 004, sur 6 819 |
| Tracés du GTFS, tous appariés par identifiant | 974 |
| Tracé différent (moins de 95 % en commun dans un sens) | 71 |
| Nom de ligne différent | 2 |
| Lignes d'OSM dans la zone, absentes du GTFS | 282, sur 1 256, dont des lignes de bus numérotées (06, 702, 705…) et le train Abidjan–Ouagadougou |

En résumé, OSM a gardé presque tous les arrêts et tracés de 2023, et en compte d'autres. Le rapport mesure seulement l'écart à OSM : il ne dit rien du terrain actuel (interdiction d'Adjamé aux gbakas, réorganisation par l'AMUGA).

**Tuiles du fond léger** (Planetiler 0.10.2, schéma de l'ADR-009) :

| Archive | Taille | Tuiles | Budget F-12 (45 Mo pour le fond, H-031) |
|---------|--------|--------|------------------------------------------|
| Côte d'Ivoire | 57,6 Mo | 78 546 | sans objet |
| Abidjan, emprise de H-029 | 4,5 Mo | 577 | dans le budget, à 10 % |

- La plus grosse tuile d'Abidjan pèse 104 Ko compressée, au zoom 12 sur le centre, presque entièrement de voirie.
- Planetiler signale ses propres réparations, sans qu'on les masque :
  - 9 053 géométries recalées sur la grille des tuiles, pour le pays ;
  - 7 multipolygones auxquels il manque un chemin dans l'extrait ;
  - 1 multipolygone invalide, vide après réparation, donc absent des tuiles.

## Organisation de la base

Les entités de la partie 7.2 sont réparties en quatre schémas (ADR-005) :

| Schéma | Entités |
|--------|---------|
| `network` | `city`, `admin_area`, `place`, `stop`, `operator`, `route`, `route_pattern`, `service_profile`, `network_version`, `change_request`, `partner_feed`, `incident` |
| `mobility` | `observation`, `position_event`, `vehicle_session`, `queue_state`, `fare_observation`, `fare_estimate` |
| `identity` | `user`, `device`, `trust_score`, `contribution` (lien vers l'appareil), `reward_ledger` |
| `ops` | `audit_log`, état des flux partenaires |

Le schéma est en place depuis I0.4 : [data/schema](../data/schema/README.md), avec ses migrations, ses tests et les règles qu'il impose (données fictives, honnêteté des estimations, conservation, audit).

## Fraîcheur

Chaque type d'information a une **demi-vie**, qui fixe la vitesse à laquelle une observation perd du poids. Il a aussi une **durée de validité** : passé ce délai sans nouvelle observation, l'appli revient à l'estimation historique, présentée comme telle (7.5, F-06).

Valeurs proposées, à calibrer pendant le pilote :

| Information | Demi-vie | Validité avant repli | Après la validité |
|-------------|----------|----------------------|-------------------|
| File en gare, en pointe | 10 min (7.5) | 30 min (F-06) | « Habituellement à cette heure : … » |
| File en gare, en heure creuse | 20 min | 30 min (F-06) | Idem |
| Véhicules présents en gare | 5 min | 15 min | Idem |
| Position d'un véhicule, par GPS (V2) | — | Délai propre à chaque catégorie de véhicule (F-05). Proposition : 3 min pour gbakas et wôrô-wôrôs, 5 min pour les bus, 10 min pour les bateaux | Le véhicule disparaît de la carte |
| Prix payé | 30 jours (7.5) | 90 jours | Estimation historique ; « prix inconnu » s'il n'y a pas d'historique |
| Incident : accident, route barrée | 30 min | 2 h, sauf fin déclarée plus tôt | L'incident disparaît, reste dans l'historique |
| Incident : inondation | 1 h | 6 h ou fin de l'alerte de pluie | Idem ; la zone reste à éviter tant qu'elle est signalée (12.4) |
| Arrêt déplacé, ligne déviée | — | Jusqu'à la décision d'un modérateur | Modification du réseau, ou rejet |

## Confiance

La confiance est affichée par un badge à trois niveaux (10.3), plus un état « inconnu ». Définition proposée (v0) ; les détails de calcul sont dans [ALGORITHMES.md](ALGORITHMES.md).

| Niveau | Condition |
|--------|-----------|
| Élevée | Au moins 3 observations concordantes de sources distinctes depuis moins d'une demi-vie, ou une source vérifiée (chef de gare, Éclaireur, GPS) récente ; intervalle 50e à 80e centile étroit |
| Moyenne | Au moins une observation de moins de deux demi-vies, ou un historique de la tranche horaire nourri par au moins 20 contributeurs distincts |
| Faible | Observation isolée, ou historique de moins de 20 contributeurs |
| Inconnue (gris) | Aucune donnée : l'appli le dit, sans estimation |

## Règles d'affichage (règle 1.3.2)

- Toute estimation affiche sa **fraîcheur** (« il y a 4 min »), sa **source** (usagers, chef de gare, GPS, historique) et son **niveau de confiance**.
- Les durées et les prix sont des **fourchettes**, sans fausse précision :
  - durées : 50e et 80e centiles, en minutes entières (« 10 à 20 min ») ;
  - prix : 10e et 90e centiles, arrondis à 50 F (« 300 à 400 F »).
- La feuille « Pourquoi cette estimation ? » donne l'origine du chiffre, sa date et le nombre de personnes qui l'ont confirmé (10.2).

## Données fictives

La politique est fixée par la règle 1.3.1 et l'hypothèse H-007 :

- **Pour les tests automatiques** : `data/fixtures_fictives/`. On y trouve la ville « Lagune-Fictive », avec des noms inventés impossibles à confondre avec des lieux réels, et chaque enregistrement porte `is_fictional = true`. Le GTFS (avec l'extension) et le jeu SQL sont générés à partir d'une seule description, avec une graine fixe ; le GTFS passe le validateur de MobilityData en CI ([README](../data/fixtures_fictives/README.md)).
- **Pour les maquettes testées en gare** : des lieux réels issus d'OSM, mais des gares, lignes, prix et attentes fictifs, marqués « (fictif) ».
- **Dans les builds de développement** : le bandeau « DONNÉES FICTIVES » s'affiche.
- **Garde-fous** :
  - une version du réseau qui contient des enregistrements fictifs ne peut pas être publiée (I0.4) ;
  - le validateur de terrain refuse toute ligne fictive dans les données réelles (I0.2).

## Spécification de l'extension GTFS, version 0

Ce sont les fichiers décrits dans l'[ADR-007](DECISIONS/ADR-007-extension-gtfs.md). Conventions communes :
- codage UTF-8, séparateur virgule (comme GTFS) ;
- heures de tranche au format `HH:MM:SS`, sur un pas de 15 min ;
- durées en secondes, prix en XOF entiers ;
- `day_type` vaut `ouvrable`, `samedi`, `dimanche` ou `ferie` ;
- `confidence` vaut `faible`, `moyenne` ou `elevee`.

| Fichier | Champ | Type | Obligatoire | Remarque |
|---------|-------|------|-------------|----------|
| `ext_feed_info.txt` | `extension_name` | texte | oui | Toujours `ext` en v0 |
| | `extension_version` | texte, version sémantique | oui | `0.1.0` |
| | `network_version` | texte | oui | Version publiée du réseau |
| | `produced_at` | date et heure ISO 8601 | oui | |
| | `is_fictional` | 0 ou 1 | oui | |
| `ext_stop_attributes.txt` | `stop_id` | identifiant (`stops.txt`) | oui | |
| | `stop_kind` | énumération | oui | Huit valeurs, voir l'ADR-007 |
| | `boarding_radius_m` | entier positif | non | Zone de montée floue d'un arrêt informel |
| | `lighting`, `shelter`, `accessibility` | `oui`, `non` ou `inconnu` | non | |
| | `active_start`, `active_end` | heure | non | Heures d'activité |
| `ext_stop_aliases.txt` | `stop_id`, `alias` | identifiant, texte | oui | |
| | `alias_kind` | `orthographe`, `abreviation`, `nouchi` ou `ancien_nom` | oui | |
| | `language` | code de langue | non | `fr` par défaut |
| `ext_route_appearance.txt` | `route_id` | identifiant (`routes.txt`) | oui | |
| | `body_color`, `color_pattern`, `markings`, `announced_as` | texte | non | Tels que relevés sur le terrain |
| | `source`, `verified_at` | texte, date | oui | |
| `ext_service_profiles.txt` | `route_id`, `direction_id`, `stop_id`, `day_type`, `slot_start` | clé | oui | |
| | `active` | 0 ou 1 | oui | |
| | `headway_mean_s` | entier | si actif | Intervalle moyen |
| | `headway_cv` | décimal ≥ 0 | non | Coefficient de variation |
| | `departs_when_full` | 0 ou 1 | oui | Départ au remplissage, en tête de ligne |
| | `seats` | entier | non | Capacité |
| | `n_obs` | entier | oui | |
| `ext_wait_profiles.txt` | `stop_id`, `route_id`, `direction_id`, `day_type`, `slot_start` | clé | oui | |
| | `regime` | `A`, `B` ou `C` | oui | Voir ALGORITHMES.md |
| | `wait_p50_s`, `wait_p80_s` | entier | oui | p50 ≤ p80 |
| | `n_obs`, `confidence` | entier, énumération | oui | |
| `ext_fare_estimates.txt` | `route_id`, `from_area_id`, `to_area_id`, `condition` | clé | oui | Zones de `areas.txt` (GTFS-Fares v2) |
| | `fare_p10`, `fare_p50`, `fare_p90` | entier en XOF | oui | p10 ≤ p50 ≤ p90 |
| | `n_obs`, `last_observed_at`, `confidence` | entier, date, énumération | oui | |
| `ext_route_reliability.txt` | `route_id`, `direction_id`, `day_type`, `slot_start` | clé | oui | |
| | `service_probability` | décimal entre 0 et 1 | oui | Probabilité que la ligne circule dans cette tranche |
| | `wait_calibration` | décimal entre 0 et 1 | non | Part des attentes réelles sous le 80e centile annoncé |
| | `n_obs` | entier | oui | |

## Qualité des données

Tableau de bord du back-office (7.6), alimenté dès la phase 1 :
- fraîcheur par gare et par ligne ;
- couverture des 50 trajets les plus demandés ;
- écart entre l'attente prévue et l'attente déclarée ;
- calibration du 80e centile ;
- taux de contributions rejetées ;
- écarts avec OSM et GTFS ;
- lignes non parcourues depuis plus de 90 jours.

Seuils de passage à une nouvelle zone (7.3) : au moins 80 % des 50 trajets les plus demandés couverts, et au moins un signalement par gare toutes les 15 min en pointe.

## Conservation

Les durées de conservation, à valider, sont dans [PRIVACY.md](PRIVACY.md) ; elles sont appliquées par la structure de la base (ADR-005).
