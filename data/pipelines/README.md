# data/pipelines

Import d'OpenStreetMap et du GTFS « Abidjan 2023 », génération des tuiles et des packs hors ligne (incrément I0.7). Chaque source téléchargée est vérifiée par empreinte SHA-256 (`nemesis_pipelines.checksum`).

Les fichiers lourds produits (`*.osm.pbf`, `*.pmtiles`, `data/work/`) ne sont jamais versionnés.
