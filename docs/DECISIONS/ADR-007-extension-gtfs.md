# ADR-007 — Extension GTFS propre au projet

- **Statut** : proposé. Il s'agit de la version 0 de l'extension ; ses fichiers seront produits à partir de I0.5 (fixtures) et I0.7 (imports).
- **Date** : 2026-11-04
- **Casquettes consultées** : ingénieur transport, data scientist, ingénieur géomatique, architecte

## Contexte

GTFS Schedule est le format pivot du réseau (7.1). Avec `frequencies.txt`, `continuous_pickup`, GTFS-Fares v2 et GTFS-Flex, il décrit une bonne part du transport artisanal. Il ne couvre pas ce qui fait la valeur du projet (7.1, 2.5) :
- les files en gare et les véhicules présents ;
- les attentes estimées et la fiabilité ;
- les prix **observés**, sous forme de distribution et non de tarif officiel ;
- l'apparence des véhicules (couleurs par commune, inscriptions) et les noms tels qu'on les dit ;
- les zones de montée floues des arrêts informels.

L'extension doit rester lisible par les outils GTFS standards, être versionnée et pouvoir être publiée ouvertement (6.4).

## Options envisagées

| Option | Avantages | Inconvénients |
|--------|-----------|---------------|
| 1. Fichiers supplémentaires préfixés dans l'archive GTFS | Ignorés par les outils standards ; une seule archive ; facile à publier | Notre spécification à maintenir |
| 2. Colonnes supplémentaires dans les fichiers standards uniquement | Tolérées par GTFS | Ne peut pas représenter des profils par tranche horaire ni des distributions |
| 3. Format séparé (JSON, SQLite) à côté du GTFS | Libre | Deux sources à synchroniser ; moins réutilisable |
| 4. Proposer des ajouts au standard GTFS | Bien commun | Long ; à envisager une fois l'extension éprouvée |

## Décision proposée

**Option 1** pour les données statiques, avec quelques **colonnes supplémentaires** dans les fichiers standards quand c'est naturel. À terme, on partagera l'expérience avec la communauté GTFS, à commencer par les acteurs du transport artisanal en Afrique (option 4).

Le préfixe est **`ext_`**, et non le nom de l'appli, qui n'est pas fixé (H-003). L'extension est identifiée par `ext_feed_info.txt`.

### Fichiers statiques, version 0

| Fichier | Une ligne par | Champs principaux |
|---------|---------------|-------------------|
| `ext_feed_info.txt` | archive | `extension_name`, `extension_version` (versionnage sémantique), `network_version`, `produced_at`, `is_fictional` |
| `ext_stop_attributes.txt` | arrêt | `stop_id`, `stop_kind` (`sotra_stop`, `gare_artisanale`, `arret_informel`, `arret_minute`, `embarcadere`, `station_metro`, `station_brt`, `gare_interurbaine`), `boarding_radius_m`, `lighting`, `shelter`, `accessibility`, `active_start`, `active_end` |
| `ext_stop_aliases.txt` | nom alternatif | `stop_id`, `alias`, `alias_kind` (`orthographe`, `abreviation`, `nouchi`, `ancien_nom`), `language` |
| `ext_route_appearance.txt` | ligne | `route_id`, `body_color`, `color_pattern`, `markings`, `announced_as` (ce que crie l'apprenti), `source`, `verified_at` |
| `ext_service_profiles.txt` | ligne, sens, point, type de jour, tranche de 15 min | `route_id`, `direction_id`, `stop_id`, `day_type`, `slot_start`, `active`, `headway_mean_s`, `headway_cv`, `departs_when_full`, `seats`, `n_obs` |
| `ext_wait_profiles.txt` | arrêt, ligne, sens, type de jour, tranche | `stop_id`, `route_id`, `direction_id`, `day_type`, `slot_start`, `regime` (`A`, `B`, `C`), `wait_p50_s`, `wait_p80_s`, `n_obs`, `confidence` |
| `ext_fare_estimates.txt` | ligne, zone d'origine, zone de destination, condition | `route_id`, `from_area_id`, `to_area_id` (zones de GTFS-Fares v2, `areas.txt`), `condition` (`normale`, `pointe`, `pluie`, `nuit`, `fete`), `fare_p10`, `fare_p50`, `fare_p90` (XOF), `n_obs`, `last_observed_at`, `confidence` |
| `ext_route_reliability.txt` | ligne, sens, type de jour, tranche | `route_id`, `direction_id`, `day_type`, `slot_start`, `service_probability`, `wait_calibration`, `n_obs` |

Les zones de montée en polygone utilisent les `locations.geojson` de GTFS-Flex plutôt qu'un format maison.

**Données fictives** (règle 1.3.1) : `ext_feed_info.is_fictional` vaut 1, et chaque fichier des fixtures porte en plus une colonne `is_fictional`. GTFS tolère les colonnes supplémentaires.

### Temps réel

- **GTFS-Realtime** pour ce qui entre dans le standard : `VehiclePositions` et `ServiceAlerts` (flux partenaires, SOTRA, et à terme publication ouverte).
- **Protocol Buffers propres** (`nemesis.live.v1`, dans `packages/proto`) pour l'état des gares et les deltas par tuile (ADR-006). Chaque estimation porte `EstimateMeta` : fraîcheur, confiance, source.

Nous n'ajoutons pas d'extension numérotée à GTFS-Realtime tant que le format n'est pas stabilisé.

### Règles de publication

- Les profils et estimations publiés ouvertement n'incluent que les cellules issues d'au moins 20 contributeurs distincts : `n_obs` compte les contributeurs, pas les observations (k ≥ 20, partie 12.2). Les autres cellules sont omises, jamais arrondies à une valeur inventée.
- Licence compatible avec l'ODbL d'OpenStreetMap (6.4), à valider : voir [DATA.md](../DATA.md).

## Conséquences

- La spécification détaillée (types, unités, valeurs permises) est tenue dans [DATA.md](../DATA.md). Toute modification incompatible passe à une version majeure supérieure.
- Les fixtures (I0.5) et le moteur (I0.9) lisent ces fichiers. Le pack hors ligne les reprend sous forme compilée.
- **Réversibilité** : bonne. Les fichiers sont isolés, et le cœur GTFS reste standard et validé par l'outil de MobilityData.
