# Protocole : collecte des requêtes réelles de destination

Statut : version 1 du 2026-11-04. À ajuster après la première demi-journée de collecte.

## Pourquoi

La fonctionnalité F-01 doit trouver le bon lieu au premier essai dans au moins 90 % des cas, sur 300 requêtes réelles. On ne peut pas le mesurer avec des phrases inventées au bureau. Il faut savoir comment les gens disent vraiment où ils vont : « Sipo », « Yop », « Adj Liberté », « derrière la pharmacie Y », avec ou sans accents, en français, en nouchi ou en dioula.

Chaque requête collectée devient un cas de test : la recherche de lieux reçoit la `formulation` et doit retrouver le `lieu_compris`.

## Ce qu'on note, et ce qu'on ne note jamais

| On note | On ne note jamais |
|---------|-------------------|
| La phrase exacte, mot pour mot | Le nom, le numéro, l'âge de la personne |
| Si elle a été dite ou écrite, et dans quelle langue | Une adresse privée (on note le repère public le plus proche) |
| Le lieu visé, confirmé avec la personne | La position GPS de la personne |
| Le lieu, la commune, la date et l'heure de l'enquête | Une photo, un enregistrement de voix |

## Plan de collecte (proposition, H-025)

- **300 requêtes, avec un objectif de 400** si possible (voir « Utilisation » plus bas).
- **Au moins 6 lieux d'enquête dans au moins 4 communes.** En priorité les gares et les marchés du corridor pilote, puis d'autres communes, pour couvrir la variété des lieux visés.
- **Trois tranches horaires** : pointe du matin (6 h à 9 h), journée, pointe du soir (16 h 30 à 20 h).
- **Au moins un tiers de requêtes dites et un tiers écrites.** La voix est essentielle pour les personnes qui lisent difficilement ; l'écrit montre les abréviations réelles.
- **Au plus 3 requêtes par personne**, soit au moins 100 personnes, pour la diversité.
- **Effort estimé** : 10 à 15 requêtes par heure et par enquêteur, soit 20 à 30 heures d'enquête. Ce chiffre est à vérifier dès le premier jour.

## Déroulé avec une personne (environ 2 minutes)

1. **Aborder** une personne qui attend, sans la presser si son véhicule arrive.
2. **Vérifier qu'elle est adulte** : « Vous avez plus de 18 ans ? »
3. **Lire le consentement** :
   > « Bonjour, je fais une petite enquête pour une future application qui aide à trouver son transport. Cela prend deux minutes. C'est anonyme : je ne note ni votre nom ni votre numéro. Vous acceptez ? »

   En cas de refus, remercier et s'arrêter.
4. **Poser la question** :
   > « Où allez-vous souvent ? Dites-le comme vous le demanderiez à quelqu'un. »

   Pour une requête écrite :
   > « Pouvez-vous l'écrire comme vous l'écririez dans un message ? »

   Donner un petit papier, recopier la phrase sur la fiche, puis détruire le papier.
5. **Noter mot pour mot** dans la colonne « Formulation exacte » :
   - ne pas corriger l'orthographe ;
   - ne pas ajouter d'accents ;
   - garder les abréviations (« Adj », « Koum ») et les mots de nouchi tels qu'ils sont dits.

   Pour une phrase dite, l'écrire comme elle se prononce.
6. **Confirmer le lieu** :
   > « Vous voulez dire… ? »

   Noter la réponse confirmée dans « Lieu visé ». S'il s'agit d'un domicile, demander le repère public le plus proche.
7. **Compléter la ligne** : dit ou écrit, langue, type de lieu, expression relative (« derrière », « en face de »…), commune visée. Les codes sont au verso de la fiche.
8. **Remercier.** Au plus 3 requêtes par personne.

## Saisie au bureau

- **Identifiants.** Le coordinateur attribue à chaque enquêteur une plage d'identifiants qui ne se chevauchent pas, par exemple E01 : RQ-1001 à RQ-1999.
- **Fichiers.** Un fichier par enquêteur et par jour : `data/terrain/collecte/requetes/requetes-AAAA-MM-JJ-E01.csv`.
- **Coordonnées.** Latitude et longitude du lieu visé : facultatives, ajoutées au bureau à partir d'une carte (OpenStreetMap). Jamais à partir d'une position de la personne.
- **Validation.** `uv run nemesis-terrain valider data/terrain/collecte` doit afficher « OK ».

## Contrôle qualité

- **Double saisie** : 10 % des fiches sont saisies une seconde fois par une autre personne, et les deux saisies sont comparées. Au-delà de 2 % d'écarts, toute la saisie du lot est relue.
- **Relecture** : le coordinateur relit chaque semaine les « lieux visés » ambigus et les marque en remarque.
- **Bilan du premier jour** : vérifier la répartition (dit ou écrit, communes, types de lieu) et ajuster les lieux d'enquête.

## Utilisation des données

- **Recommandation (H-026) : garder les 300 requêtes de test intactes.** On conçoit la clé phonétique et les synonymes sur un autre jeu, sinon le score de 90 % serait flatteur. D'où l'objectif de 400 requêtes : les 100 premières servent au développement, les 300 suivantes au test.
- **Collecte limitée à 300.** On les répartit en 100 pour le développement et 200 pour le test, et on le signale dans le rapport de la phase 1.
- **Jeu figé.** Une fois atteint, le jeu de test est daté et versionné, puis réutilisé tel quel à chaque évaluation.
