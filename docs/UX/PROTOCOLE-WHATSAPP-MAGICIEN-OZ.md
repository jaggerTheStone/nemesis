# Protocole : prototype WhatsApp « magicien d'Oz »

Un humain répond sur WhatsApp comme le fera plus tard le canal automatisé (partie 11.2). On apprend ainsi, avant d'écrire le service, comment les gens demandent un trajet, ce qu'ils comprennent d'une réponse courte, et ce qu'ils en font (partie 10.1).

> **Exécution bloquée.** Ce prototype voit des numéros de téléphone et des positions : il ne démarre pas avant la déclaration ARTCI ou un avis juridique écrit (Q-07, H-020). Le protocole est prêt ; seule la date de lancement attend.

## Ce qu'on veut apprendre

| Question | Mesure |
|----------|--------|
| Comment les gens formulent-ils un trajet ? | Part de texte, de notes vocales, de positions partagées ; repères cités ; fautes et abréviations (F-01) |
| La réponse courte suffit-elle ? | Part des conversations où la personne choisit « 1 » ou « 2 » sans autre question ; échanges nécessaires avant une réponse utile |
| Les fourchettes et les sources sont-elles comprises ? | Questions de relance du type « donc c'est combien ? » ; réponses au micro-sondage |
| Quel délai est acceptable ? | Délai réel de réponse, et abandons selon ce délai |
| Les abonnements intéressent-ils ? | Part des personnes qui demandent « préviens-moi chaque jour » |

## Dispositif

- **Un numéro dédié**, sur un téléphone du projet, avec l'application WhatsApp Business. On n'utilise pas l'API pour ce prototype. Ce numéro ne sert à rien d'autre.
- **Deux opérateurs ou opératrices**, les « magiciens », en binôme sur les créneaux de pointe : de 6 h à 9 h et de 16 h 30 à 20 h, en semaine. L'un répond, l'autre chronomètre et tient le journal.
- **Sources des réponses**, sans rien inventer (règle 1) :
  - relevés de terrain datés (Éclaireurs, trajets de référence) ;
  - connaissance locale des opérateurs, toujours présentée comme telle ;
  - lieux et rues d'OpenStreetMap ;
  - **jamais** le GTFS 2023 : sa licence le réserve à l'évaluation interne (H-030).
- **Recrutement** : une affichette dans les gares du corridor pilote, avec le numéro, la phrase « Demande ton trajet, une personne te répond » et les créneaux. Participants de 18 ans et plus.

## Consentement, avant toute réponse

Premier message, envoyé à toute nouvelle conversation :

```
Bonjour ! Ici [nom du projet], un test pour aider à se déplacer à Abidjan.
Une personne de l'équipe te répond, ce n'est pas un robot.
On garde ta demande sans ton numéro, pour améliorer le service.
Ta position n'est jamais gardée. Tu peux écrire STOP à tout moment.
Tu as 18 ans ou plus et tu es d'accord ? Réponds OUI.
```

Sans « OUI », on ne répond pas sur le fond. Après « STOP », on confirme, on supprime la conversation du téléphone et on ne recontacte jamais la personne.

## Modèles de réponse

Les modèles suivent la microcopie de la partie 10.4 : tutoiement, phrases de 12 mots au plus, « 300 F », « 6 h 30 », « 10 à 20 min ». Les valeurs entre crochets viennent des sources ci-dessus ; une valeur inconnue s'écrit « inconnu », jamais une estimation inventée.

**M1, deux options** (partie 11.2) :

```
De [départ] à [arrivée], maintenant :
1) 🚐 Gbaka [ligne] : [20 à 35] min, [300 à 400] F. Attente [5 à 15] min.
2) 🚕 Wôrô-wôrô puis 🚌 bus : [25 à 40] min, [400 à 500] F.
D'après nos relevés du [date]. Réponds 1 ou 2 pour le détail.
```

**M2, détail d'une option** :

```
1) Marche 4 min jusqu'à [gare], à côté de [repère].
2) Prends le gbaka [couleur, inscription]. L'apprenti crie « [destination] ».
3) Prévois [300 à 400] F, souvent [300] F. Prépare la monnaie.
4) Descends à [repère]. Demande à l'apprenti de te prévenir.
```

**M3, il manque le départ ou l'arrivée** : « Tu pars d'où ? Un carrefour, une gare ou un quartier suffit. »

**M4, lieu inconnu** : « Je ne trouve pas [lieu]. C'est près de quel carrefour ou marché ? »

**M5, on ne sait pas** : « Je n'ai pas d'info fiable pour ce trajet. Je préfère ne pas deviner. » On note la demande : c'est un trou de données.

**M6, note vocale reçue** : on répond par écrit, avec M1 ou M3. Si l'audio est incompréhensible : « Je n'ai pas bien compris. Tu peux répéter ou écrire ? »

**M7, position partagée** : on s'en sert pour M1, puis on la supprime de la conversation. On ne note que la commune ou le quartier.

**M8, micro-sondage**, une heure après un M2, une seule fois : « Tu as attendu combien de temps ? Réponds juste un nombre de minutes. »

**M9, abonnement demandé** : « Le rappel quotidien n'existe pas encore. Merci, on note que ça t'intéresse ! » On ne simule pas l'abonnement : il demanderait de garder le numéro.

**M10, hors créneau** (réponse d'absence automatique) : « On répond de 6 h à 9 h et de 16 h 30 à 20 h, en semaine. »

## Délai de réponse

- Objectif : **moins de 3 minutes** entre la réception et l'envoi de M1, sur les créneaux annoncés.
- Le service automatisé visera moins de 5 s (partie 11.7). Le prototype mesure donc surtout ce qui se passe quand la réponse tarde : relances, abandons.
- Le chronométreur note les heures de réception et d'envoi, à la minute.

## Journal, sans identité

Un fichier CSV par jour, tenu par le chronométreur. **Aucun numéro, aucun nom, aucune position précise** :

| Colonne | Contenu |
|---------|---------|
| `conversation` | Code tiré au hasard au premier message (`W` + 4 chiffres). La correspondance avec le numéro n'est écrite nulle part |
| `jour`, `recu_a`, `repondu_a` | Date, heures à la minute |
| `entree` | `texte`, `vocal`, `position` |
| `demande` | Départ et arrivée tels qu'écrits, sans adresse de domicile ; position ramenée à la commune ou au quartier |
| `modele` | M1 à M10 |
| `suite` | `1`, `2`, `question`, `rien`, `stop` |
| `attente_declaree_min` | Réponse au micro-sondage, sinon vide |
| `note` | Observation de l'opérateur, sans donnée personnelle |

Règles de conservation :
- les conversations sont supprimées du téléphone **7 jours** après le dernier message, ou tout de suite après « STOP » ;
- rien n'est exporté de WhatsApp : ni sauvegarde, ni capture d'écran ;
- le journal suit les durées de H-020.

Le format du journal sera ajouté aux schémas validés par `nemesis-terrain` quand Q-07 sera levée.

## Après chaque semaine

- **Compte rendu** au format du [modèle](MODELE-tests-AAAA-MM-JJ.md). On y met les mesures du tableau du début, les formulations de lieux à ajouter aux alias, et les trous de données (M5).
- **Modèles de réponse** : chaque modèle mal compris est réécrit avant la semaine suivante.
- **Requêtes réelles** : les demandes alimentent le jeu des 300 requêtes réelles (F-01), une fois anonymisées comme ci-dessus.
