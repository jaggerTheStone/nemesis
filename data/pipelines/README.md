# data/pipelines

Pipelines de données du projet :
- import d'OpenStreetMap et du GTFS « Abidjan 2023 », rapports de validation et d'écarts, tuiles du fond léger (I0.7) ;
- validateur des données de terrain (`nemesis-terrain`, I0.2) ;
- générateur du jeu fictif (`nemesis-fixtures`, I0.5 et I0.7).

Les fichiers produits (`data/work/` : sources téléchargées, rapports, `*.pmtiles`) ne sont jamais versionnés.

## Lancer la chaîne

```bash
make dev                  # base de développement migrée
make data-import-fictif   # chaîne complète sur les données fictives du dépôt (sans réseau)
make data-import          # chaîne réelle : Geofabrik, GTFS 2023 (réseau requis)
```

**Prérequis** :
- osm2pgsql 1.11 : `apt-get install osm2pgsql`, paquet d'Ubuntu 24.04 ;
- osmium-tool, pour les tuiles du jeu fictif, écrit en OSM XML ;
- Docker, pour le validateur GTFS et Planetiler (images GHCR épinglées dans `sources.toml`).

**Options** :
- sans accès à GHCR : `make data-import-fictif DATA_OPTIONS="--sans-validation --sans-tuiles"` ;
- autre base : `DATABASE_URL=postgres://… make data-import`.

**Résultats** :

| Fichier | Contenu |
|---------|---------|
| `data/work/sources/<source>/` | Fichier vérifié et `provenance.json` |
| `data/work/rapports/<profil>/validation-gtfs/` | Rapports du validateur (HTML, JSON) et `resume.md`, qui liste tous les avis |
| `data/work/rapports/<profil>/ecarts.md`, `ecarts.geojson` | Rapport d'écarts GTFS ↔ OSM, et ses entités pour revue sur une carte |
| `data/work/rapports/<profil>/tuiles.md`, `tuiles.json` | Taille des archives face au budget de F-12 |
| `data/work/rapports/<profil>/volumes.json` | Provenance, volumes importés, totaux des avis et des écarts |
| `data/work/tiles/*.pmtiles` | Fond léger, servi par le serveur de tuiles de `make dev` |

Chaque étape a sa commande : `uv run nemesis-data --help`.

## Sources

Elles sont déclarées dans [`sources.toml`](sources.toml) : URL, mode de vérification, licence, attribution, usage permis. Le manifeste est refusé dans les cas suivants :
- une source réelle sans empreinte : ni `sha256` épinglée, ni `md5_url` publiée par la source ;
- une URL qui n'est pas en https ;
- une attribution absente ;
- un fichier du dépôt qui n'est pas fictif ;
- un profil qui mêle données fictives et réelles ;
- une image d'outil non épinglée par empreinte.

| Source | Vérification | Usage |
|--------|--------------|-------|
| `osm_cote_divoire` (Geofabrik, extrait du jour) | MD5 publiée par Geofabrik | Produit (ODbL) |
| `gtfs_abidjan_2023` (dépôt GitLab d'origine, commit `da5d9faf`) | SHA-256 épinglée | **Évaluation seulement** (CC BY-NC 4.0, H-030) |
| `osm_lagune_fictive`, `gtfs_lagune_fictive` | Fichiers du dépôt | Tests |

## Étapes

1. **Téléchargement** (`download.py`). Le fichier est écrit à côté de son `provenance.json`. S'il ne correspond pas à son empreinte, il est supprimé et la chaîne s'arrête. Un fichier déjà présent et inchangé n'est pas retéléchargé.
2. **Validation du GTFS** (`gtfs/validator.py`). Le validateur MobilityData tourne avec le code pays `ci`. Tous ses avis sont listés dans `resume.md`, erreurs d'abord, avec jusqu'à 10 exemples. Rien n'est corrigé : chaque avis est à traiter avec le producteur des données.
3. **GTFS en staging** (`gtfs/staging.py`).
   - Chaque ligne de chaque fichier est copiée dans `staging_gtfs.record` avec son numéro de ligne, ses valeurs restant du texte.
   - Les vues `staging_gtfs.stop`, `route`, `trip`, `stop_time` et `shape_point` typent ce qui est lisible.
   - Les lignes vides, trop courtes ou trop longues sont comptées.
   - Seuls les deux derniers imports d'une source gardent leurs lignes.
4. **OSM en staging** (`osm/importer.py`, style [`osm/nemesis.lua`](src/nemesis_pipelines/osm/nemesis.lua)). osm2pgsql recrée les tables de `staging_osm` :
   - `road` : voirie, avec ce qui se marche et ce qui se roule ;
   - `poi` : points d'intérêt nommés, déjà classés dans les catégories de `network.place` ; « maquis » seulement si le nom le dit ;
   - `transit_stop` : quais, arrêts, gares routières, embarcadères ;
   - `route`, `route_master` et `route_member` : les lignes et leurs membres ordonnés ;
   - `boundary` : les limites administratives.
5. **Lieux** (`osm/places.py`, profil réel seulement). Les points d'intérêt de l'emprise de la ville deviennent des `network.place`, avec leurs alias : `name`, `old_name` (ancien nom), `short_name` (abréviation), les autres variantes en « autre ».
   - Un import suivant met à jour les lieux, par leur référence OSM, au lieu de les dupliquer.
   - Les lieux disparus d'OSM sont comptés, jamais supprimés.
6. **Écarts GTFS ↔ OSM** (`reports/gaps.py`).
   - **Arrêts** : appariés d'abord par identifiant, quand le GTFS vient d'OSM (`node/…`), puis un à un par distance, jusqu'à 50 m. Un arrêt apparié à plus de 20 m est signalé comme déplacé.
   - **Tracés** : appariés d'abord par identifiant (relation OSM = `shape_id`), puis par référence et par géométrie.
     - Sont comparées la part de chaque ligne qui court à moins de 30 m de l'autre, et la distance au premier arrêt, pour le sens.
     - Un tracé est identique au-delà de 95 % dans les deux sens, distinct sous 80 % sans la même référence.
   - **Objets présents seulement dans OSM** : comptés à moins de 300 m des arrêts du GTFS.
7. **Tuiles** (`tiles/`, schéma [`basemap.yml`](src/nemesis_pipelines/tiles/basemap.yml), ADR-009).
   - `planetiler verify` joue les exemples du schéma.
   - Planetiler produit l'archive du pays, puis l'extrait borné par l'emprise de la ville.
   - L'en-tête PMTiles est lu en Python. La taille de l'extrait est comparée aux 45 Mo du fond (F-12, H-031).
8. **Pack ville du moteur d'itinéraires** (`pack/`, `nemesis-data pack reel [--sortie <dossier>]`, défaut `<travail>/packs/reel`). Le pack n'est pas produit par `make data-import` : il se construit à la demande, sans base.
   - Le GTFS est copié tel quel dans `gtfs/`.
   - Graphe piéton : osmium découpe l'extrait à l'emprise de la ville et garde les voies `highway`. Sont exclues celles qui ne se marchent pas : autoroutes et bretelles, chantiers, projets, circuits, voies de bus guidés, quais, ascenseurs, surfaces (`area=yes`), et les voies marquées `foot=no` ou `access=no` ou `private`. Un tag `foot=yes` ou `designated` l'emporte sur ces règles. Les nœuds sont placés aux intersections, aux extrémités et au plus tous les 100 m ; les arêtes parallèles gardent la plus courte.
   - `pack.json` reprend la provenance des deux sources. L'usage passe à `evaluation` dès qu'une source l'est : c'est le cas du GTFS 2023 (H-030).
   - Le pack fictif est régénéré par `nemesis-fixtures generer` dans `data/fixtures_fictives/pack`, à partir de l'OSM fictif.

## Tests

```bash
uv run pytest data/pipelines   # sans base : les tests de base sont ignorés
make pipelines-test            # contre une base PostGIS jetable, avec osm2pgsql
```

Sur les données fictives, le rapport d'écarts doit trouver exactement les écarts volontaires de l'OSM fictif ([data/fixtures_fictives/README.md](../fixtures_fictives/README.md)). Un GTFS fabriqué à partir des identifiants OSM vérifie l'appariement par identité.

En CI :
- « Pipelines de données (chaîne fictive) » tourne à chaque modification ;
- « Imports de données réelles (hebdomadaire) » tourne chaque lundi, à la demande, et quand les sources, le style OSM, le rapport ou le schéma de tuiles changent.
