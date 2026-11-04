# Sécurité

## Signaler une vulnérabilité

Ne publie pas de vulnérabilité dans une issue publique. Utilise la fonction
« Report a vulnerability » (avis de sécurité privé) de l'onglet Security du
dépôt GitHub. Un contact dédié sera désigné avec le porteur du projet.

## Règles appliquées dès maintenant

- Aucun secret dans le code ni dans l'historique Git : les secrets passent par
  des variables d'environnement, et `.env` est ignoré par Git.
- Analyse automatique en intégration continue : Trivy (vulnérabilités, secrets,
  mauvaises configurations) sur tout le dépôt, `pnpm audit`, `pip-audit` et
  `cargo deny`.
- Chaîne d'approvisionnement : versions exactes dans des fichiers de
  verrouillage ; pnpm refuse les paquets publiés depuis moins de 14 jours
  (`minimumReleaseAge`) et uv ignore les versions plus récentes que la date
  `exclude-newer` du `pyproject.toml` racine.
- Actions GitHub : droits minimaux (`contents: read`) et le moins possible
  d'actions tierces ; les outils sont installés à des versions figées.

Référentiels visés (partie 12.3 du cahier des charges) : OWASP MASVS pour le
mobile et ASVS pour l'API.
