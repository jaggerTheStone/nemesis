# ADR-009 — Schéma des tuiles du fond de carte léger

- **Statut** : proposé.
- **Date** : 2026-11-04
- **Casquettes consultées** : ingénieur géomatique, ingénieur mobile, SRE, juriste (licences)

## Contexte

La partie 9.1 fixe la chaîne : tuiles vectorielles produites depuis OpenStreetMap avec Planetiler, stockées en PMTiles, rendues par MapLibre. Elle prévoit un extrait PMTiles par ville pour le hors-ligne.

F-12 fixe deux plafonds pour le pack de la ville d'Abidjan : moins de 15 Mo sans fond de carte, moins de 60 Mo avec le fond léger. Le fond lui-même dispose donc au plus de 45 Mo.

Sur ce fond, l'appli affiche ses propres données, servies à part : gares, arrêts, lignes, incidents. Le fond n'a besoin que de ce qui sert à se repérer.

## Options envisagées

| Critère | OpenMapTiles (profil par défaut de Planetiler) | Shortbread | Schéma maison « fond léger » |
|---------|-----------------------------------------------|------------|------------------------------|
| Contenu | Complet : bâtiments, commerces, adresses, etc. | Complet, plus sobre | Eau, verdure, limites, localités, voirie, rail, bacs, gares |
| Taille sur Abidjan | La plus grosse : Abidjan compte beaucoup de bâtiments cartographiés | Plus petite, avec bâtiments et adresses | La plus petite |
| Sources hors OSM | Natural Earth, polygones d'eau de mer, lacs (téléchargés par Planetiler, sans empreinte vérifiée) | Polygones d'eau de mer | Aucune : seulement l'extrait OSM vérifié |
| Licence du schéma | CC-BY 4.0 : mention « © OpenMapTiles » obligatoire en plus d'OSM | CC0 | Le nôtre |
| Styles MapLibre existants | Nombreux | Quelques-uns (VersaTiles) | À écrire, mais court |
| Tests du schéma | Ceux du projet OpenMapTiles | Ceux de Planetiler | Exemples dans le schéma, joués par `planetiler verify` en CI |

## Décision proposée

Un **schéma maison** au format YAML de Planetiler : `data/pipelines/src/nemesis_pipelines/tiles/basemap.yml`.

- **Neuf couches** : `water`, `waterways`, `green`, `boundaries`, `places`, `roads`, `railways`, `ferries`, `transit`.
- **Absents** : bâtiments, adresses, commerces, arrêts de bus. L'appli affiche ses propres arrêts, avec leur fraîcheur.
- **Zoom maximal** : 14 ; MapLibre agrandit au-delà.
- **Sources** : l'extrait OSM vérifié par sa MD5, et rien d'autre.
- **Archives** : l'archive du pays, et un extrait par ville borné par l'emprise de `sources.toml` (H-029).
- **Mesure** : la taille de l'extrait de la ville est comparée aux 45 Mo à chaque exécution de la chaîne réelle.

## Conséquences

- **Simplification signalée** (règle 1.3.8) : le fond v0 ne dessine pas l'océan.
  - Il faudrait les polygones d'eau de mer d'osmdata.openstreetmap.de, qui ne publient pas d'empreinte vérifiable (I0.7 : toute source est vérifiée).
  - La lagune Ébrié, cartographiée comme surface d'eau dans OSM, est bien dessinée.
  - À traiter avec le style de carte (I0.11 ou phase 1) : soit une empreinte épinglée par import, soit une couche « terre » calculée.
- **Attribution** : « © les contributeurs d'OpenStreetMap », inscrite dans les archives et affichée par l'appli, avec un lien vers openstreetmap.org/copyright. Aucune mention de schéma n'est due.
- **Style** : à écrire pour ces neuf couches. La lisibilité au soleil est un critère de la partie 9.1, à tester en I0.11.
- **Réversibilité** : bonne. Passer à Shortbread ne change que le schéma et le style ; la chaîne, les archives et la mesure restent les mêmes.
