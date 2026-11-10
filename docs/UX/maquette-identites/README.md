# Maquette : trois identités pour l'appli

Statut : version 1 du 2026-11-10. **Le porteur a choisi yafohi** le jour même : voir sa [charte](../identite-yafohi/README.md). La maquette répondait à son retour sur le prototype d'I0.11, jugé « plat » (voir [ETAT.md](../../ETAT.md)).

La maquette est un canevas privé sur claude.ai : [Maquettes et identités de l'appli](https://claude.ai/artifact/1F5LKRjBzceL2WExCzV55L). Seul le porteur peut l'ouvrir, tant qu'il ne l'a pas partagée. Ce dossier en garde les sources et des aperçus.

## Ce qu'elle montre

Trois propositions complètes. Chacune a un nom tiré du nouchi, un logo, des couleurs, une typographie, un ton, et la même appli habillée à ses couleurs :

| Proposition | Sens du nom | Promesse | Inspiration |
|-------------|-------------|----------|-------------|
| **gbê** | « C'est gbê » : c'est vrai, c'est sûr | Le bon trajet, le vrai prix | La clarté de Google Maps |
| **yafohi** | « Y'a fohi » : y'a pas de souci | Bouge tranquille | La simplicité de Wave |
| **mon kôrô** | « Kôrô » : le grand frère | Le grand frère qui connaît la route | L'esprit communautaire de Waze |

Les écrans, identiques d'une identité à l'autre :

1. **Carte** : la vraie carte d'Abidjan, les gares proches avec leur attente et leur affluence, des véhicules qui bougent, des incidents signalés, la vue satellite en un geste.
2. **Recherche** : un seul champ, des suggestions de vrais lieux, la recherche vocale.
3. **Trois trajets** : le plus rapide, le moins cher, le plus régulier. Chacun montre ses durées en fourchette, son prix, sa fraîcheur et sa confiance.
4. **En route** : l'étape en cours en grand, l'alerte avant de descendre, l'heure d'arrivée, le partage du trajet.
5. **Signaler** : six gros boutons, deux pressions.
6. **Fiche gare** : l'affluence en direct et sur la journée, les départs, les prix.

Les états **hors connexion** (temps habituels, trajets enregistrés) et **vue satellite** sont montrés pour gbê. Ils existent dans les trois.

## yafohi sur les lignes réelles de 2023

Une rangée du canevas, à côté de la page d'accueil, montre yafohi sur le corridor Yopougon – Adjamé – Plateau avec les données réelles :

- **Les lignes et les arrêts** : 230 lignes et 28 arrêts principaux, tirés du GTFS 2023 de DigitalTransport4Africa.
- **Les trajets** : calculés par le vrai moteur, de Toits-Rouges vers 11 lieux du corridor, aller et retour.
- **Ce que l'appli ne sait pas, elle le dit** : « Prix inconnu », « Affluence inconnue », « Lignes de 2023 · à confirmer ».

`Reel.dc.html` charge ces données depuis un fichier du canevas, produit par `tools/maquette/donnees_2023.py`. Ce fichier n'est pas versionné : il dérive d'un jeu sous licence non commerciale (H-030). Les constats de l'essai sont dans la [feuille de route](../../FEUILLE-DE-ROUTE.md).

## Vrai et simulé

- **Vrai** : les rues, la lagune, les quartiers et les noms des gares viennent d'OpenStreetMap ; l'image satellite vient de Sentinel-2 (2025, EOX). Les trajets suivent les vraies rues.
- **Simulé** : les lignes, les véhicules, les attentes, l'affluence, les prix et les signalements. Un bandeau le rappelle sur la carte (règle 1, H-036).

## Aperçus

| | |
|-|-|
| Accueil du canevas | [accueil.jpg](apercus/accueil.jpg) |
| gbê | [planche](apercus/planche-gbe.jpg) · [écrans](apercus/ecrans-gbe.jpg) |
| yafohi | [planche](apercus/planche-yafohi.jpg) · [écrans](apercus/ecrans-yafohi.jpg) |
| mon kôrô | [planche](apercus/planche-koro.jpg) · [écrans](apercus/ecrans-koro.jpg) |

## Sources

`sources/` contient les fichiers du canevas : `canvas.json` et un `.dc.html` par planche ou écran. `Prototype.dc.html` porte toute l'appli, avec un réglage `theme` (`gbe`, `yafohi`, `koro`) et un réglage `screen`. Les autres écrans l'importent avec leurs réglages. Les fonds de carte sont des fichiers du canevas, appelés par leur adresse `/_blob/…`. Ils se refont avec les [outils de la maquette](../../../tools/maquette/README.md).

## Limites

- **Ce n'est pas l'appli** : c'est une maquette web pour choisir une direction. L'appli sera développée selon l'ADR-001.
- **Les noms ne sont pas vérifiés** : leur sens et leur usage sont à confirmer avec des Abidjanais. Leur disponibilité (magasins d'applis, marque, nom de domaine) n'est pas vérifiée non plus.
- **Licence de l'imagerie satellite** : non commerciale, voir les [outils de la maquette](../../../tools/maquette/README.md#sources-et-licences).
- **Pas de test avec des usagers** : la maquette doit passer par le protocole de tests de maquettes (5 à 8 personnes par itération, partie 10.1) avant de figer l'identité.
