# Protocole : suite des 200 trajets de référence

Statut : version 1 du 2026-11-04.

## Pourquoi

Le moteur d'itinéraires doit proposer des options réalistes : au moins 85 % des options proposées sur la suite de référence (critère de F-02 et de fin de la phase 1). Cette suite est rejouée à chaque modification du moteur ou des données. Toute régression bloque la publication (partie 14.1).

Seules des personnes qui font ces trajets peuvent dire ce qui est réaliste. On leur demande donc deux choses :

- les **réponses acceptables** : comment on fait vraiment ce trajet, en combien de temps, pour combien ;
- les **pièges** : des réponses plausibles sur le papier mais fausses sur le terrain (ligne disparue, accès interdit, gare déplacée), que le moteur ne doit jamais proposer.

## Composition de la suite (proposition, H-025)

| Critère | Répartition proposée |
|---------|----------------------|
| Zone | Au moins 150 trajets avec un départ ou une arrivée dans le corridor pilote ; environ 50 ailleurs dans Abidjan |
| Heure de départ | Pointe du matin 40 %, pointe du soir 30 %, journée 20 %, soir et nuit 10 % |
| Jour | Au moins 80 % de jours ouvrables ; le reste le samedi et le dimanche |
| Conditions | Environ 10 % par temps de pluie |
| Profil | Environ 5 % pour un usager à mobilité réduite |

Les trajets hors du corridor vérifient l'honnêteté du moteur. Tant qu'une zone n'est pas couverte, il doit répondre « pas encore couvert » au lieu d'inventer une option.

Les départs et les arrivées sont des repères publics, dits comme à Abidjan. On s'appuie sur les lieux visés de la collecte des requêtes et sur les trajets que les validateurs font eux-mêmes.

## Les validateurs

- **Qui.** Des habitants qui font le trajet au moins une fois par semaine. Au moins **deux validateurs par trajet** (codes V01, V02…).
- **Travail indépendant.** Chacun remplit d'abord sa fiche seul ; on rapproche ensuite les réponses.
- **Désaccord** sur une réponse : un troisième validateur tranche. Une réponse est retenue comme acceptable si au moins deux validateurs l'acceptent. La justification garde la trace du désaccord.

## Remplir une fiche

1. **Le trajet** : départ et arrivée (repère et commune), heure de départ, type de jour, conditions particulières, profil, codes des validateurs, date.
2. **Les réponses** : de 1 à 3 par trajet, sur les blocs « Réponse ».
   - **Statut** : `acceptable` pour une façon réelle de faire le trajet, `piege` pour une réponse à ne jamais proposer.
   - **Étiquettes** : `moins_cher`, `plus_rapide`, `plus_simple`, `plus_sur`, selon ce que la réponse représente.
   - **Étapes en véhicule**, dans l'ordre, une ligne par véhicule : le véhicule (code), où monter, la ligne ou la destination criée par l'apprenti, où descendre.
   - **Durée totale** porte à porte, attente comprise, en fourchette : *min* = un bon jour à cette heure, *max* = un mauvais jour.
   - **Prix total** payé, en fourchette. Il varie avec la pointe, la pluie et la nuit.
   - **Marche totale maximale**, si elle compte.
   - **Justification** : pourquoi la réponse est acceptable, ou pourquoi c'est un piège.

   Durées et prix sont obligatoires pour une réponse acceptable, facultatifs pour un piège.
3. **Au bureau** : identifiant TR-001 à TR-200, numéro de réponse (celui du bloc), coordonnées facultatives des repères, saisie dans `data/terrain/collecte/trajets/trajets.csv` et `reponses.csv`.

Chaque trajet doit avoir au moins une réponse acceptable : le validateur le vérifie.

## Règle de notation du réalisme

Pour chaque trajet couvert, chaque option proposée par le moteur est classée ainsi.

**1. Piège.** Si l'option suit les mêmes étapes qu'un piège, elle est **non réaliste**, et une alerte est levée.

**2. Correspondance automatique.** L'option est **réaliste** si elle correspond à une réponse acceptable sur tous ces points :

| Point vérifié | Condition |
|---------------|-----------|
| Étapes | Même nombre d'étapes en véhicule, même véhicule à chaque étape |
| Montée et descente | Même arrêt après géocodage, ou à moins de 300 m |
| Ligne | Même ligne ou même terminus, quand la réponse précise la ligne |
| Durée | Médiane (50e centile) comprise entre *min − 10 %* et *max + 10 %* |
| Prix | Médiane comprise entre *min − 50 F* et *max + 50 F* |
| Marche | Au plus *marche max + 3 min*, si la réponse fixe une marche maximale |

**3. Revue humaine.** Les options sans correspondance sont jugées par deux validateurs. La décision est enregistrée comme une nouvelle réponse, acceptable ou piège, pour ne pas revoir la même option à chaque passage. Cela crée une nouvelle version de la suite.

**Score** = options réalistes ÷ options proposées, sur les trajets couverts. Seuil : 85 %. Le rapport détaille aussi le score par étiquette (moins cher, plus rapide, plus simple).

**Régression** : un trajet dont une option était réaliste à la version précédente et ne l'est plus. Elle est examinée avant toute publication.

Ces tolérances sont une proposition, à recalibrer après la première évaluation complète.

## Versions et entretien

- **Version figée.** La suite v1 est figée à une date donnée. Toute modification (changement de réseau, nouvel arrêté, réorganisation de l'AMUGA) produit une nouvelle version, avec une note dans `CHANGELOG.md`.
- **Pas de suppression silencieuse.** Un trajet n'est jamais supprimé sans trace, et un identifiant n'est jamais réutilisé.
- **Revalidation** tous les six mois, et après tout grand changement du réseau.

## Effort estimé

Environ 20 minutes par trajet et par validateur, soit environ 130 heures pour 200 trajets avec deux validateurs. Ce chiffre est à vérifier sur les 10 premiers trajets.
