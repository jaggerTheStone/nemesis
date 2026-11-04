# Protocole : tests des maquettes et reconnaissance des icônes

Statut : version 1 du 2026-11-04. Il s'applique au prototype cliquable de l'incrément I0.11.

## Pourquoi

La partie 10.1 du cahier des charges demande trois choses :
- tester les parcours avec de vrais usagers, dans les gares, avant de coder les écrans ;
- faire tester chaque itération par 5 à 8 personnes, dont au moins 2 qui lisent difficilement et 1 personne âgée ;
- s'assurer que chaque icône de mode et d'action est reconnue sans légende par au moins 85 % de 20 personnes.

Une question guide chaque séance : « Est-ce qu'Awa peut s'en servir ? Est-ce que Mamadou est exclu ? »

Un tour 0 sur maquettes papier dessinées à la main est possible dès maintenant, avec ce même protocole. Il permet d'apprendre avant le prototype.

## Participants

Par tour de test des maquettes, 5 à 8 personnes de 18 ans et plus, recrutées dans les gares et marchés du corridor pilote :

| Profil | Minimum par tour |
|--------|------------------|
| Lit difficilement ou ne lit pas | 2 (exigence de la partie 10.1) |
| 60 ans et plus | 1 (exigence de la partie 10.1) |
| Préfère le dioula | 1 |
| Femmes | 2 |
| Téléphone basique ou sans téléphone, pour la tâche T5 | 1 |

Le test des icônes porte sur 20 personnes par version du jeu d'icônes, dont au moins un tiers qui lisent difficilement (proposition, H-025).

La contrepartie offerte aux participants reste à fixer par le porteur du projet.

## Matériel

- **Téléphone de référence** : Android d'entrée de gamme, environ 2 Go de mémoire, chargé, luminosité au maximum. Le prototype est installé en build de développement, avec le bandeau « DONNÉES FICTIVES ».
- **Menu USSD simulé** pour T5 : une carte imprimée par écran du menu. L'animateur montre la carte qui correspond au choix de la personne.
- **Deux paquets de cartes d'icônes** (A et B), mélangés dans deux ordres différents. Une icône par carte, sans texte, le code au dos. On alterne A et B d'un participant à l'autre.
- **Fiches** : [test des maquettes](../TERRAIN/fiches/fiche-test-maquettes.html) et [test des icônes](../TERRAIN/fiches/fiche-test-icones.html), avec des crayons.
- **Aucun appareil d'enregistrement**, ni son, ni image (H-020).

## Rôles

- **L'animateur** (code E01…) lit les consignes et pose les questions. Il ne guide pas.
- **L'observateur** (code E02…) remplit la fiche : résultat, durée, nombre de pressions, aide donnée, observations.

## Déroulé d'une séance de test des maquettes (environ 25 minutes)

1. **Accueil.** Vérifier que la personne a 18 ans ou plus, puis lire le consentement écrit sur la fiche. Sans accord, remercier et s'arrêter.
2. **Profil** : tranche d'âge, lecture déclarée, téléphone, langue préférée. On coche, on ne demande aucun justificatif.
3. **Mise en confiance** :
   > « C'est l'application qu'on teste, pas vous. Il n'y a pas de mauvaise réponse. Dites tout haut ce que vous pensez, si vous voulez. »
4. **Tâches T1 à T5**, lues à voix haute. On ne demande jamais à la personne de lire une consigne.
5. **Questions de compréhension**, imprimées sur la fiche. Elles vérifient que les fourchettes (« 10 à 20 min »), la fraîcheur (« il y a 4 min ») et les badges de confiance sont compris, comme l'exige la règle d'honnêteté 1.3.2.
6. **Remerciements.**

## Les tâches

Les lieux entre crochets sont à choisir parmi ceux du prototype. Ce sont des lieux réels issus d'OSM ; les lignes et les prix sont fictifs (H-007).

| Tâche | Consigne lue à la personne | Réussie si… | À observer |
|-------|----------------------------|-------------|------------|
| T1 · Trajet du matin (parcours 1) | « Demain matin, vous allez à [destination]. Trouvez le trajet le moins cher. Combien allez-vous payer ? Où montez-vous ? » | La personne désigne l'option « Le moins cher », donne la fourchette de prix et le lieu de montée | Comprend-elle la fourchette ? Utilise-t-elle la voix ou le bouton audio ? |
| T2 · Gare saturée (parcours 2) | « Vous arrivez à [gare] et la file est très longue. Que vous propose l'application ? » | Elle trouve l'option de remplacement et dit combien de temps elle gagne | Voit-elle d'où vient l'information, et quand elle a été signalée ? |
| T3 · Bord de route (parcours 3) | « Vous attendez au bord de la route, les gbakas passent pleins. Que faites-vous ? » | Elle comprend le conseil « remonter à la gare » et les deux attentes estimées | Fait-elle confiance à l'estimation ? |
| T4 · Contribuer (parcours 5) | « Vous êtes dans la file. Dites à l'application qu'il y a beaucoup de monde. » | Elle réussit sans aide, en deux pressions au plus (F-07) | Nombre de pressions, et le fait de le faire d'une seule main |
| T5 · Sans smartphone (parcours 7) | « Avec ce téléphone simple, demandez comment aller de [A] à [B]. » | Elle atteint l'écran de résultat en cinq écrans au plus | Compréhension des menus numérotés |

## Règles d'animation

- **Pas d'aide pendant les 30 premières secondes** de difficulté.
- **Ensuite, une relance neutre** : « Que cherchez-vous ? »
- **En dernier recours, une aide ciblée.** Le résultat devient alors « Réussie avec aide », et l'observateur note l'aide donnée.
- **La personne peut abandonner** une tâche ou toute la séance, sans justification.
- **Réactions neutres** : ni « bravo », ni « non, pas là ».

## Test de reconnaissance des icônes (environ 10 minutes)

1. Faire vérifier l'âge, lire le consentement, cocher le profil, comme pour les maquettes.
2. Montrer chaque carte seule et demander : « Qu'est-ce que ça représente ? À quoi ça sert ? »
3. Noter la réponse mot pour mot, dans la langue de la personne, sans l'aider ni la corriger.
4. Coder au bureau, avec le guide ci-dessous :
   - `oui` : la personne nomme le bon mode ou la bonne action, avec ses propres mots ;
   - `partiel` : la bonne famille mais pas le bon objet (« un car » pour le gbaka, « partager » pour « signaler ») ;
   - `non` : une autre chose, ou « je ne sais pas ».
5. Faire coder 20 % des fiches par un second codeur. Les désaccords se règlent à deux. En cas de doute, choisir `partiel`.
6. Calculer les taux : `uv run nemesis-terrain icones data/terrain/collecte/ux`. Seules les réponses `oui` comptent pour le seuil de 85 %. Le rapport indique aussi le taux chez les personnes qui lisent difficilement.

Le guide de codage par icône est à compléter avec les icônes elles-mêmes (I0.11). Il prendra cette forme :

| Icône | Réponses codées `oui` | Réponses codées `partiel` |
|-------|------------------------|----------------------------|
| `mode_gbaka` | à compléter | à compléter |

## Après la séance

- **Saisie** dans `data/terrain/collecte/ux/<session>/` : `participants.csv`, plus `observations.csv` ou `icones.csv`. Puis validation.
- **Compte rendu** à partir du [modèle](MODELE-tests-AAAA-MM-JJ.md), enregistré sous `docs/UX/tests-AAAA-MM-JJ.md`.
- **Suites** : chaque problème bloquant ou majeur devient une tâche avant le tour suivant.
