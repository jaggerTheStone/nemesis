# Kits de terrain

Incrément I0.2 de la phase 0. Ces kits servent à lancer tôt les collectes qui demandent des semaines sur place. Le MVP pourra ainsi être mesuré dès son arrivée.

| Activité | À quoi elle sert | Protocole | Fiche papier | Modèle de saisie |
|----------|------------------|-----------|--------------|------------------|
| 300 requêtes réelles | Évaluer la recherche de lieux (F-01 : 90 % de réussite au premier essai) | [PROTOCOLE-REQUETES.md](PROTOCOLE-REQUETES.md) | [HTML](fiches/fiche-requetes.html) · [PDF](pdf/fiche-requetes.pdf) | [requetes.csv](../../data/terrain/modeles/requetes.csv) |
| 200 trajets de référence | Mesurer le réalisme des itinéraires (85 %) et bloquer les régressions | [PROTOCOLE-TRAJETS-REFERENCE.md](PROTOCOLE-TRAJETS-REFERENCE.md) | [HTML](fiches/fiche-trajet-reference.html) · [PDF](pdf/fiche-trajet-reference.pdf) | [trajets.csv](../../data/terrain/modeles/trajets.csv), [reponses.csv](../../data/terrain/modeles/reponses.csv) |
| Tests des maquettes | Vérifier que les parcours clés marchent pour Awa, Mamadou, Mariam… | [PROTOCOLE-TESTS-MAQUETTES.md](../UX/PROTOCOLE-TESTS-MAQUETTES.md) | [HTML](fiches/fiche-test-maquettes.html) · [PDF](pdf/fiche-test-maquettes.pdf) | [participants.csv](../../data/terrain/modeles/participants.csv), [observations.csv](../../data/terrain/modeles/observations.csv) |
| Test des icônes | Chaque icône reconnue sans légende par 85 % de 20 personnes | même protocole | [HTML](fiches/fiche-test-icones.html) · [PDF](pdf/fiche-test-icones.pdf) | [icones.csv](../../data/terrain/modeles/icones.csv) |

Le [dictionnaire des données](DICTIONNAIRE.md) décrit chaque colonne et chaque code. Il est généré à partir des schémas, comme les modèles de saisie.

## Le circuit d'une donnée

1. **Imprimer** les fiches PDF.
2. **Collecter** sur place en suivant le protocole.
3. **Saisir** dans une copie du modèle CSV, ouverte dans un tableur, puis enregistrer au format « CSV UTF-8 ».
4. **Déposer** le fichier dans `data/terrain/collecte/` :
   - requêtes : `requetes/requetes-AAAA-MM-JJ-E01.csv` ;
   - trajets : `trajets/trajets.csv` et `trajets/reponses.csv` ;
   - tests : un dossier par session, `ux/S20261120-01/`, contenant `participants.csv` et `observations.csv` ou `icones.csv`.
5. **Valider** : `uv run nemesis-terrain valider data/terrain/collecte`. Chaque erreur indique le fichier, la ligne, la colonne et, souvent, la correction (« vouliez-vous « port_bouet » ? »). L'intégration continue refait cette validation à chaque envoi.

## Règles communes à toutes les activités

Ces règles appliquent l'hypothèse H-020 : aucune donnée personnelle réelle avant la déclaration à l'ARTCI ou un avis juridique écrit.

- **Anonymat.** Ne jamais noter de nom, de numéro de téléphone, d'adresse privée ni d'âge exact. Si quelqu'un indique son domicile, noter le repère public le plus proche ou le quartier.
- **Aucun enregistrement.** Pas de photo de personne, pas d'enregistrement audio ni vidéo. Les notes sont écrites à la main.
- **Codes pseudonymes.** Enquêteurs et animateurs : E01, E02… ; validateurs : V01, V02… ; participants : P01, P02… dans chaque session.
  - Pour les enquêteurs et les validateurs, le coordinateur garde hors du dépôt la correspondance entre code et personne (contrat, paiement).
  - Pour les participants, cette correspondance n'existe nulle part.
- **Adultes uniquement.** Demander « Vous avez plus de 18 ans ? » avant de commencer (partie 12.5).
- **Consentement oral.** Lire le texte prévu, mot pour mot, avant toute question. Sans accord, ne rien noter et remercier.
  - Les textes vouvoient : on s'adresse à des inconnus dans un lieu public (H-024). Le tutoiement de l'appli (H-005) ne s'applique pas ici.
  - Pour une personne qui préfère le dioula, un enquêteur dioulaphone traduit oralement. Une version écrite validée reste à produire.
- **Respect des gares.** Avant d'enquêter dans une gare, se présenter au chef de gare, ou au représentant du syndicat présent, et expliquer la démarche. Ne jamais gêner le chargement des véhicules.
- **Sécurité des enquêteurs.** Travailler en binôme après la tombée de la nuit ; arrêter en cas de tension.
- **Fiches papier.** Les ranger sous clé. Les conserver jusqu'à la fin de la phase 1 pour vérifier la saisie, puis les détruire.

## Ce qui reste à décider par le porteur du projet

- Qui collecte sur place (question Q-03) : sans équipe à Abidjan, ces kits restent prêts mais inutilisés.
- La contrepartie offerte aux participants des tests, et la rémunération des Éclaireurs et des validateurs : budget de la partie 15.6.
- La relecture juridique des textes de consentement, avec la question Q-04.

## Pour les développeurs

- Les schémas (`data/pipelines/src/nemesis_pipelines/terrain/schemas/`) sont la source unique. Après une modification, lancer `uv run nemesis-terrain generer` : il régénère les modèles et le dictionnaire. Les tests échouent si on oublie.
- Les fiches HTML portent un attribut `data-champ` par colonne saisie sur le terrain. Un test vérifie qu'aucun champ ne manque sur le papier.
- Après une modification d'une fiche, régénérer les PDF avec `make fiches-pdf` (il faut Playwright avec Chromium). Un test compare les empreintes enregistrées dans `pdf/SOURCES.sha256`.
- Les exemples fictifs se trouvent dans `data/fixtures_fictives/terrain/`. On les valide avec `uv run nemesis-terrain valider --fictif data/fixtures_fictives/terrain`.
