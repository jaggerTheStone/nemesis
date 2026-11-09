# Protocole : campagne « Éclaireurs »

Statut : version 1 du 2026-11-09.

## Pourquoi

Le réseau artisanal n'est décrit nulle part de façon fiable. Les gbakas et les wôrô-wôrôs n'ont ni horaires ni arrêts officiels, et le GTFS de 2023 précède des changements majeurs (PHASE-0, désaccord 3). Les Éclaireurs relèvent sur place ce qui fera le réseau du corridor pilote (partie 7.2) :

| Collecte | Ce qu'elle donne | Fiche | Format d'échange |
|----------|------------------|-------|------------------|
| Recensement des gares | Gares, stations et points de montée : nom tel qu'on le dit, position, modes, horaires, éclairage, accès (F-06) | [fiche-recensement-gare](fiches/fiche-recensement-gare.html) | `gares.csv` |
| Relevé de ligne | Un trajet complet à bord, d'un terminus à l'autre : arrêts dans l'ordre, heures, prix | [fiche-releve-ligne](fiches/fiche-releve-ligne.html) | `releves_ligne.csv`, `arrets_releves.csv` |
| Prix payés | Les prix réels, avec leurs conditions (partie 8.3) | [fiche-prix](fiches/fiche-prix.html) | `prix.csv` |
| Comptages en gare | Départs, arrivées et file par tranche de 15 minutes : débits du régime A, calibration des catégories de file (ALGORITHMES.md 1.2) | [fiche-comptage](fiches/fiche-comptage.html) | `comptages.csv` |

Les mêmes collectes se font dans l'appli en **mode relevé** ([MODE-RELEVE.md](MODE-RELEVE.md)), qui ajoute la trace GPS (`traces.csv`) et les photos (`photos.csv`). Les fiches papier restent la solution de secours, et le seul moyen tant que le mode relevé n'existe pas.

Toutes les colonnes et tous les codes sont décrits dans le [dictionnaire des données](DICTIONNAIRE.md).

## Règles

Les [règles communes](README.md#règles-communes-à-toutes-les-activités) s'appliquent : anonymat, codes pseudonymes, respect des gares, sécurité. Pour cette campagne, s'y ajoutent les règles suivantes.

- **On observe le réseau, pas les gens.** On note des véhicules, des arrêts, des prix et des files ; jamais un nom, un numéro, une plaque ni qui a payé quoi.
- **Photos : ni visage ni plaque lisible.** Cadrer la gare, le panneau ou le véhicule de loin. Une photo où l'on reconnaît quelqu'un est floutée ou supprimée avant de quitter le téléphone ; le format d'échange refuse toute photo non vérifiée.
- **Ne rien inventer** (règle 1). Une valeur qu'on n'a pas vue reste vide. Un prix annoncé ou affiché se note avec sa source, jamais comme un prix payé.
- **Données personnelles des Éclaireurs.** Une trace GPS est une donnée personnelle de celui qui la porte. **Le mode relevé, avec sa trace, attend donc la déclaration ARTCI ou un avis juridique écrit (Q-07, H-020).** Les fiches papier, sans trace, peuvent servir dès que l'équipe existe (Q-03).

## Organisation

- **Équipe** (proposition, à dimensionner avec le budget de la partie 15.6) : un coordinateur et 4 à 6 Éclaireurs, codes E01, E02… Le coordinateur garde hors du dépôt la correspondance entre code et personne.
- **Formation** : une demi-journée sur un même trajet, fiches en main, puis comparaison des relevés.
- **Identifiants donnés avant la sortie** : le coordinateur attribue les numéros de gare (GA-0001…) et de relevé (RL-0001…), pour qu'ils ne soient jamais réutilisés.
- **Ordre conseillé** :
  1. le recensement des gares du corridor ;
  2. les relevés de ligne, au moins un par ligne et par sens ;
  3. les comptages en gare, aux pointes du matin (6 h à 9 h) et du soir (16 h 30 à 20 h), plus une tranche creuse ;
  4. les prix, tout au long de la campagne.

## Les collectes

### Recensement d'une gare

Une fiche par gare. Se présenter au chef de gare ou au syndicat, expliquer la démarche. Noter le nom tel qu'on le dit et les autres noms entendus : ils alimentent la recherche de lieux (F-01). Lire la position sur le téléphone au point de montée. Demander le premier et le dernier départ, ou les observer.

### Relevé de ligne

Un trajet complet, d'un terminus à l'autre, assis dans le véhicule.
- Le rang 1 est la gare de départ. On ajoute une ligne à chaque arrêt pour charger ou décharger, même hors de tout arrêt connu (`a_la_demande`).
- Le nom d'un arrêt est celui que crie l'apprenti ; à défaut, le repère le plus proche.
- On note l'heure de passage ; la position si on peut la lire sans gêner.
- Montés et descendus : on les compte si possible, sinon on laisse vide.

### Prix payés

Une ligne par prix. On note de préférence le prix qu'on paie soi-même (`paye`) ; sinon un prix vu payer (`observe`), annoncé (`annonce`) ou affiché (`affiche`). Les conditions s'écrivent toujours, `normale` s'il n'y a rien de particulier.

### Comptage en gare

Une fiche par ligne d'une gare et par session de 3 heures (12 tranches de 15 minutes). Au début de chaque tranche :
1. compter les véhicules en attente ;
2. choisir à l'œil la catégorie de file (`peu`, `moyen`, `beaucoup`, `tres_long`), **avant** de compter ;
3. compter la file une à une, ou l'estimer par paquets de 10 si elle est trop longue.

Pendant la tranche, un bâton par véhicule arrivé vide et un par véhicule parti. Le comptage de la file après le choix à l'œil sert à calibrer les catégories de l'appli.

## Saisie, dépôt et validation

1. **Saisir** dans une copie du modèle (`data/terrain/modeles/`), en « CSV UTF-8 ». L'identifiant du relevé se recopie sur chaque arrêt.
2. **Déposer** dans `data/terrain/collecte/eclaireurs/`, un fichier par jeu, par jour et par Éclaireur : `releves_ligne-2026-11-20-E03.csv`, `arrets_releves-2026-11-20-E03.csv`…
   - Les fichiers d'un même dossier se vérifient ensemble : les arrêts et les traces doivent y trouver leur relevé.
3. **Valider** : `uv run nemesis-terrain valider data/terrain/collecte`.
4. **Mesurer l'accord** : `uv run nemesis-terrain accord data/terrain/collecte/eclaireurs`.

## Protocole qualité

### Double relevé

- **10 % des lignes au moins** sont relevées deux fois, par deux Éclaireurs différents, dans la même semaine et à la même période de la journée.
- Le coordinateur **tire au sort** les lignes à doubler, parmi celles déjà relevées. Le second Éclaireur ne voit pas le premier relevé.
- Au bureau, la colonne `double_de` du second relevé reçoit l'identifiant du premier.
- Pour les comptages, une session sur dix est faite à deux, côte à côte, sans se parler. Les deux Éclaireurs comptent la même ligne, aux mêmes tranches.

### Mesures d'accord et seuils d'acceptation

`nemesis-terrain accord` calcule ces mesures. Les seuils sont des propositions, à revoir après la première semaine (H-035).

| Ce qu'on compare | Mesure | Seuil |
|------------------|--------|-------|
| Couverture | Part des lignes relevées deux fois | au moins 10 % |
| Arrêts de deux relevés | Arrêts trouvés par les deux sur l'ensemble des arrêts trouvés (indice de Jaccard). Deux arrêts sont les mêmes s'ils portent le même nom, ou s'ils sont à moins de 100 m | au moins 80 % |
| Ordre des arrêts | Paires d'arrêts communs vues dans le même ordre | au moins 95 % |
| Prix de deux relevés | Écart entre les prix payés | 50 F au plus |
| Véhicules comptés | Tranches où départs, puis arrivées, diffèrent d'un véhicule au plus | au moins 90 % |
| Files comptées | Tranches où les files diffèrent de 20 % au plus (3 personnes au moins) | au moins 80 % |
| Catégories de file à l'œil | Accord au-delà du hasard (kappa de Cohen), sur 8 tranches au moins | au moins 0,60 |

Le rapport ajoute la part des files comptées qui tombent dans la catégorie choisie à l'œil. Elle sert à calibrer les catégories de l'appli : 0 à 5, 6 à 20, 21 à 50, plus de 50 (ALGORITHMES.md 1.2).

### Quand une mesure est sous son seuil

1. **Regarder les deux relevés ensemble**, avec les deux Éclaireurs. Les causes les plus fréquentes : un arrêt nommé de deux façons, une variante de ligne, un véhicule qui a dévié, une condition de prix différente (pluie, pointe).
2. **Si la cause est réelle** (variante, déviation), la noter en remarque. Les deux relevés sont gardés, comme deux variantes.
3. **Sinon, refaire le relevé**, puis reprendre la formation de l'Éclaireur concerné sur ce point.
4. **Si plus d'un double relevé sur cinq est sous un seuil dans la semaine**, revoir la fiche ou la consigne avant de continuer.

La commande `nemesis-terrain accord --strict` échoue dès qu'une mesure est sous son seuil. Le coordinateur s'en sert en fin de semaine.
