# Données

Version 0 du 2026-11-04 (incrément I0.3). « La donnée est le produit » (partie 7). Ce document fixe d'où viennent les données, comment on en garde la trace, quand elles cessent d'être fraîches, et comment on les montre honnêtement.

## Règle d'or

Aucune donnée réelle n'est inventée : ni ligne, ni gare, ni prix, ni fréquence, ni horaire, ni nom, ni numéro (règle 1.3.1). Une information absente s'affiche comme absente (« prix inconnu », « pas d'information récente »). Elle n'est jamais remplacée par une valeur plausible.

## Sources autorisées

| Source | Contenu | Usage | Licence et attribution | Statut |
|--------|---------|-------|------------------------|--------|
| OpenStreetMap, extrait Côte d'Ivoire de Geofabrik | Voirie, chemins piétons, points d'intérêt, relations de lignes (réseaux de gbakas et de wôrô-wôrôs cartographiés par Jungle Bus) | Graphe piéton, repères, tracés, fond de carte | ODbL 1.0. Attribution obligatoire dans l'appli : « © les contributeurs d'OpenStreetMap », avec un lien vers openstreetmap.org/copyright. Partage à l'identique des bases dérivées utilisées publiquement : portée à valider par un juriste (H-019) | Import en I0.7 |
| GTFS « Abidjan 2023 », DigitalTransport4Africa (TUMI Data Hub, Transitland) | Réseaux SOTRA, gbakas, wôrô-wôrôs par commune | A priori et banc d'essai (H-017) | **À vérifier** sur la fiche du jeu avant tout usage public | Import en I0.7. Dernière mise à jour connue : janvier 2024, avant l'interdiction d'Adjamé aux gbakas (mars 2025) et la réorganisation par l'AMUGA (octobre 2026) |
| Flux partenaires : AMUGA, SOTRA, opérateurs lagunaires | Cartographie, arrêts-minute, pôles AIM, GTFS, positions | Réseau officiel, temps réel des bus | Selon chaque convention (7.3) | Conventions à préparer ; connecteurs GTFS et GTFS-Realtime génériques |
| Données de terrain (I0.2) | Requêtes, trajets de référence, relevés des Éclaireurs, recensement des gares | Évaluation, calibration, réseau artisanal | Données du projet, anonymes | Kits prêts ([docs/TERRAIN](TERRAIN/README.md)) ; collecte selon Q-03 |
| Contributions des usagers (F-07) | Files, prix payés, incidents, arrêts déplacés | Temps réel, prix observés, corrections du réseau | Les conditions d'utilisation doivent accorder la licence nécessaire à la publication d'agrégats sous une licence compatible avec l'ODbL ; à rédiger et valider | Phase 1 |
| Météo : SODEXAM en partenariat, ou à défaut une API ouverte | Pluie actuelle et prévue | Modèle d'attente, alertes pluie | Conditions d'usage commercial à vérifier avant intégration (9.1) | Phase 1 ou V2 |
| Tuiles vectorielles produites avec Planetiler à partir d'OSM | Fond de carte léger | Carte en ligne et hors ligne | ODbL pour les données. Le schéma de tuiles (OpenMapTiles ou Shortbread) peut ajouter sa propre attribution : à confirmer en I0.7 | I0.7 |

**Sources interdites** :
- toute donnée inventée ;
- l'extraction automatique des données d'autres applications (AMUGA mon trajet, Sotra Mobile, Traaf…) sans accord écrit ;
- toute donnée personnelle tirée des réseaux sociaux.

## Provenance et versions

- **Provenance de chaque enregistrement** : il porte sa source (`source_id`), sa date de récupération ou d'observation, sa licence et `is_fictional`.
- **Fichiers bruts téléchargés** : conservés avec leur empreinte SHA-256, vérifiée avant import (`nemesis_pipelines.checksum`).
- **Versions du réseau** : il évolue par `change_request`, puis revue et publication d'une `network_version` datée, avec une date d'effet. On peut comparer deux versions et revenir en arrière (6.3).
- **Reproductibilité** : chaque pack hors ligne et chaque réponse du moteur indiquent la version du réseau utilisée.

## Organisation de la base

Les entités de la partie 7.2 sont réparties en quatre schémas (ADR-005) :

| Schéma | Entités |
|--------|---------|
| `network` | `city`, `admin_area`, `place`, `stop`, `operator`, `route`, `route_pattern`, `service_profile`, `network_version`, `change_request`, `partner_feed`, `incident` |
| `mobility` | `observation`, `position_event`, `vehicle_session`, `queue_state`, `fare_observation`, `fare_estimate` |
| `identity` | `user`, `device`, `trust_score`, `contribution` (lien vers l'appareil), `reward_ledger` |
| `ops` | `audit_log`, état des flux partenaires |

Le schéma complet, ses migrations et ses tests arrivent en I0.4.

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

- **Pour les tests automatiques** : `data/fixtures_fictives/`. On y trouve la ville « Lagune-Fictive », avec des noms inventés impossibles à confondre avec des lieux réels, et chaque enregistrement porte `is_fictional = true`.
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
