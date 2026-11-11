# Outils de la maquette d'identité

Ces scripts fabriquent les fonds de carte et les tracés de la [maquette des trois identités](../../docs/UX/maquette-identites/README.md). Ce sont des outils de conception : ils ne font pas partie du produit et ne tournent pas en CI.

## Ce qu'ils produisent

| Script | Rôle | Sortie |
|--------|------|--------|
| `frame.py` | Cadre commun : Abidjan en Web Mercator, de Yopougon à Koumassi, en pixels au zoom 14 (environ 9,5 m par pixel) | — |
| `extraire.py` | Tire de l'extrait OSM les voies par classe, la côte, la lagune, la végétation, les quartiers, les gares et les embarcadères | `couches.json` |
| `dessiner.py` et `rasteriser.cjs` | Dessine un fond de carte par identité (gbê clair, yafohi crème, mon kôrô de nuit) et les grands axes à poser sur l'image satellite, rendus par Chromium | `carte-*.webp` |
| `donnees_2023.py` | Lignes, arrêts principaux et trajets du corridor Yopougon – Adjamé – Plateau d'après le GTFS 2023 et le vrai moteur (pack réel construit en local avec l'extrait de la maquette) | `yafohi-lignes-2023.json` |
| `appli_2023.py` | Données de l'APK de test : arrêts et lignes de 2023, lieux, tracés, fond yafohi en quatre images avec les noms de quartiers, pack du moteur | `apps/mobile/assets/reel/` |
| `itineraires.py` | Calcule sur le vrai réseau de rues les trois trajets du scénario, de Toits-Rouges (Yopougon) au Plateau, et les parcours des véhicules animés | `scenario.json` |

## Refaire les cartes

L'environnement cloud n'atteint ni Geofabrik ni Overpass. L'extrait d'Abidjan vient donc du workflow « Données de carte pour la maquette » (`.github/workflows/maquette-carte.yml`). Il le dépose sur la branche, dans `tools/maquette/donnees/abidjan-maquette.osm.pbf`. Une fois les cartes faites, on retire le fichier du dépôt.

Les dépendances (osmium, shapely, Pillow) restent hors du projet, dans un environnement jetable :

```bash
uv venv /tmp/maquette && VIRTUAL_ENV=/tmp/maquette uv pip install osmium shapely pillow
```

```bash
/tmp/maquette/bin/python tools/maquette/extraire.py tools/maquette/donnees/abidjan-maquette.osm.pbf /tmp/couches.json
```

```bash
python3 tools/maquette/dessiner.py /tmp/couches.json /tmp/cartes
```

```bash
/tmp/maquette/bin/python tools/maquette/itineraires.py tools/maquette/donnees/abidjan-maquette.osm.pbf /tmp/couches.json /tmp/scenario.json
```

`dessiner.py` appelle Node et le Playwright préinstallé. L'image satellite se télécharge à part, tuile par tuile, au zoom 14. Elle vient de la couche `s2cloudless-2025_3857` de `tiles.maps.eox.at` et se découpe sur le même cadre (`frame.ORIGIN`, `frame.WIDTH`, `frame.HEIGHT`).

## Sources et licences

- **Rues, côte, lagune, quartiers, gares** : © contributeurs OpenStreetMap, licence ODbL. L'attribution est affichée sur chaque carte de la maquette.
- **Image satellite** : Sentinel-2 cloudless 2025 par EOX IT Services GmbH, qui contient des données Copernicus Sentinel modifiées. Licence CC BY-NC-SA 4.0 : **pas d'usage commercial**. Elle suffit pour une maquette interne ; le produit aura besoin d'un fournisseur sous licence commerciale (budget du fond de carte, H-031).
- **Tout le reste est simulé** : lignes, véhicules, attentes, affluence, prix, signalements (H-036).
