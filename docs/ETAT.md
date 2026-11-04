# État du projet

Ce fichier permet à une nouvelle session de reprendre le travail sans perte (partie 1.4 du cahier des charges).

**Dernière mise à jour** : 2026-11-04.

## Où en est-on

- **Phase** : cadrage, avant la phase 0. Aucun code n'a encore été écrit.
- **Fait** :
  - cahier des charges converti en Markdown : `docs/CAHIER_DES_CHARGES.md` ;
  - premier message envoyé (reformulation, questions bloquantes, hypothèses, plan de la phase 0) ;
  - hypothèses consignées : `docs/HYPOTHESES.md` ;
  - plan détaillé de la phase 0 : `docs/PHASE-0.md`.
- **En attente** : réponses aux questions Q-01 à Q-08 (`docs/HYPOTHESES.md`) et validation du plan de la phase 0.
- **Prochaine étape** : après validation, incrément I0.1 (socle du dépôt et intégration continue).

## Points d'attention pour la reprise

- Le nom `{{NOM_APP}}` n'est pas fixé ; `nemesis` est un nom de code technique (H-003).
- Plusieurs hôtes sont bloqués par la politique réseau de l'environnement cloud (H-021) : les imports de données et le build Android dépendent soit d'un élargissement de cette politique, soit de GitHub Actions.
- Aucune donnée personnelle réelle ne doit être collectée avant la déclaration ARTCI ou un avis juridique (H-020).
