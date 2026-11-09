# Spécification : le mode « relevé » de l'appli

Statut : version 1 du 2026-11-09. **Spécification, pas encore développée.** La stack de l'appli dépend de l'ADR-001. Le développement est prévu en phase 1.

Le mode relevé est la version dans l'appli des [fiches de la campagne « Éclaireurs »](PROTOCOLE-ECLAIREURS.md). Il fait la même collecte, plus vite, avec l'heure et la position notées seules, une trace GPS et des photos. Ce qu'il exporte suit **les mêmes formats d'échange que les fiches saisies** : `nemesis-terrain valider` vérifie les deux de la même façon.

> **Blocage.** La trace GPS est une donnée personnelle de l'Éclaireur qui la porte. Le mode relevé ne sert pas avant la déclaration ARTCI ou un avis juridique écrit (Q-07, H-020), et avant l'accord écrit de chaque Éclaireur. D'ici là, les fiches papier suffisent.

## Qui l'utilise

- **Les Éclaireurs de la campagne**, puis le mode Pro (partie 6.1).
- **Activation** : par un code remis par le coordinateur, qui associe le téléphone à un code d'Éclaireur (E01…). Il n'y a ni nom ni numéro dans l'appli.
- **Pour les usagers**, le mode reste invisible.

## Fonctions

### Relevé de ligne

| Fonction | Comportement attendu |
|----------|----------------------|
| Démarrer | L'Éclaireur choisit le véhicule (code de mode) et tape ou dicte la ligne criée. Il choisit la gare de départ parmi les gares recensées, ou en crée une. L'appli donne l'identifiant RL-…, réservé à l'avance par le coordinateur. |
| Trace GPS | Seulement pendant un relevé en cours : un point toutes les 5 s, ou tous les 10 m en mouvement, avec sa précision annoncée. Un point annoncé à plus de 50 m de précision est gardé mais marqué. |
| Arrêt | Un grand bouton « Arrêt » note l'heure et la position. Ensuite, et seulement si c'est facile : le nom crié (dictée ou texte), le type d'arrêt, des compteurs « + monté » et « + descendu ». |
| Prix | Montants usuels proposés en boutons. La source et les conditions sont préremplies (`paye`, condition selon l'heure) et modifiables. |
| Terminer | À l'arrivée au terminus, avec confirmation. Au bout de 20 min sans mouvement, l'appli propose de terminer ; elle ne termine jamais seule. |

### Recensement d'une gare

Les champs de la [fiche](fiches/fiche-recensement-gare.html), avec la position prise au point de montée. La position est moyennée sur 10 s pour la précision.

### Comptage en gare

- **Tranches** : l'écran affiche la tranche en cours. Il passe à la suivante à 00, 15, 30 et 45, avec une vibration.
- **Début de chaque tranche**, dans cet ordre :
  1. véhicules en attente ;
  2. file à l'œil, choisie par quatre gros boutons ;
  3. file comptée : compteur + 1 et + 10, ou « estimée ».
- **Pendant la tranche** : deux gros compteurs, « véhicule arrivé vide » et « véhicule parti », avec « parti plein » en appui long.
- **Utilisable d'une main**, l'écran allumé, sans réseau.

### Photos

- **Cadrage** : l'appareil photo de l'appli affiche un rappel, « Ni visage ni plaque lisible ».
- **Vérification obligatoire**, avant que la photo soit gardée : « Vois-tu un visage ou une plaque lisible ? »
  - Si oui : flouter, en touchant les zones, ou supprimer.
  - La photo n'entre dans l'export qu'avec `controle = oui`. Le format d'échange refuse toute autre valeur.
- **Fichier** :
  - JPEG d'au plus 1 280 px de côté ;
  - métadonnées EXIF retirées : ni modèle de téléphone ni numéro de série. L'heure et la position vont dans `photos.csv`, pas dans l'image ;
  - stocké dans l'espace privé de l'appli, jamais dans la galerie.

## Hors ligne et export

- **Tout fonctionne sans réseau.** Les relevés sont gardés dans la base SQLite du téléphone.
- **Export** : une archive ZIP par jour et par Éclaireur, partagée par la feuille de partage d'Android ou copiée par câble. Elle contient :
  - un fichier par jeu, nommé comme les fichiers saisis à la main : `releves_ligne-AAAA-MM-JJ-E01.csv`, `arrets_releves-…`, `traces-…`, `gares-…`, `prix-…`, `comptages-…`, `photos-…` ;
  - le dossier `photos/`, avec les fichiers `PH-00001.jpg`…
- **Contrôle avant export** : l'appli applique les règles des formats d'échange. Elle reprend les schémas de `data/pipelines/src/nemesis_pipelines/terrain/schemas/`, exportés en JSON au build. Un export que `nemesis-terrain valider` refuserait n'est pas proposé.
- **Après export confirmé**, les traces et les photos sont supprimées du téléphone sous 7 jours.
- **Plus tard**, l'envoi direct à l'API (`POST /contributions`, mode Pro) remplacera l'export manuel, avec les mêmes contrôles.

## Formats d'échange

| Jeu | Contenu | Produit par |
|-----|---------|-------------|
| `gares.csv` | Une gare par ligne | Fiche ou appli |
| `releves_ligne.csv` | Un relevé de ligne par ligne | Fiche ou appli |
| `arrets_releves.csv` | Les arrêts de chaque relevé, dans l'ordre | Fiche ou appli |
| `prix.csv` | Un prix par ligne | Fiche ou appli |
| `comptages.csv` | Une tranche de 15 min par ligne | Fiche ou appli |
| `photos.csv` | Une photo vérifiée par ligne | Appli seulement |
| `traces.csv` | Un point GPS par ligne, rattaché à un relevé | Appli seulement |

Colonnes, codes et règles : [dictionnaire des données](DICTIONNAIRE.md). Exemples fictifs : `data/fixtures_fictives/terrain/eclaireurs/`.

## Énergie et data

- **GPS** : en haute précision pendant un relevé seulement. Objectif : moins de 8 % de batterie par heure de relevé sur le téléphone de référence, à mesurer (Q-02).
- **Réseau** : aucun pendant la collecte. L'export se fait en Wi-Fi ou par câble.

## Critères d'acceptation, pour le développement

1. Un export de démonstration passe `nemesis-terrain valider` sans erreur, et `nemesis-terrain accord` le lit.
2. Une photo non vérifiée ne peut pas être exportée. Une photo exportée n'a plus de métadonnées EXIF.
3. Hors d'un relevé en cours, aucune position n'est enregistrée : un test en arrière-plan le vérifie.
4. Le comptage change de tranche à l'heure exacte, et n'en perd ni n'en double aucune.
5. Tout le parcours fonctionne en mode avion.
6. Chaque écran se manie d'une main, avec des zones de 48 dp et un texte de 16 sp au moins (10.3).
