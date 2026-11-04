# data/schema

Schéma de la base PostgreSQL 16, avec PostGIS et pg_trgm (partie 7.2, ADR-005, ADR-008). Les migrations sont gérées par [dbmate](https://github.com/amacneil/dbmate).

## Commandes

| Commande | Effet |
|----------|-------|
| `make dev` | Démarre la base, Valkey, NATS et le serveur de tuiles. Applique les migrations, crée les comptes de développement, charge le jeu fictif et crée les partitions |
| `make db-migrate` | Rejoue le service `migrate` sur l'environnement démarré |
| `make db-test` | Lance les tests du schéma contre une base PostGIS jetable |
| `make dev-reset` | Arrête tout et supprime les volumes : la base repart de zéro |

## Organisation

| Schéma | Contenu | Rôle qui y accède |
|--------|---------|-------------------|
| `network` | Villes, zones, lieux et alias, arrêts, opérateurs, lignes, variantes, profils de service, zones tarifaires, incidents, flux partenaires, versions du réseau | `nemesis_api` (lecture et écriture), `nemesis_analyst` (lecture) |
| `mobility` | Observations, segments de trajets, sessions et positions de véhicules (tables partitionnées par jour), états des files, profils d'attente, prix observés et estimés, vitesses | `nemesis_api` ; `nemesis_analyst` sur les seuls agrégats |
| `identity` | Comptes, appareils, consentements, contributions récompensées, points | `nemesis_identity` uniquement |
| `ops` | Comptes du back-office, journal d'audit, règles de partitionnement | `nemesis_api` (audit en ajout), `nemesis_maintenance` (fonctions de maintenance) |

## Règles inscrites dans le schéma

- **Données fictives** (règle 1.3.1) : chaque table métier a `is_fictional` et une clé `(city_id, is_fictional)` vers `network.city`. Une ville réelle ne peut contenir aucune ligne fictive. En production (`ALTER DATABASE … SET nemesis.environment = 'production'`), la publication d'une ville fictive est refusée.
- **Une seule ville par relation** : les références entre entités passent par `(id, city_id)`.
- **Honnêteté** (règle 1.3.2) : les états publiés et les estimations exigent leur confiance, leur source et la date de leur dernière observation. Les centiles doivent être ordonnés.
- **Versions du réseau** (ADR-008) :
  - une demande de modification est revue par une autre personne, et son rejet exige une raison ;
  - une version publiée est immuable ;
  - la publication passe par `network.publish_version()`.
- **Idempotence des observations** : l'identifiant est généré par le téléphone. Une heure d'observation à plus de 5 min dans le futur est refusée.
- **Conservation** (docs/PRIVACY.md) :
  - `ops.maintain_partitions()` crée les partitions quotidiennes et supprime celles qui ont dépassé leur durée de conservation : observations 12 mois, segments et positions 30 jours ;
  - `ops.purge_expired()` purge les sessions de véhicules, les prix observés et les comptes supprimés depuis plus de 30 jours.
- **Audit** : `ops.audit_log` est en ajout seul (ni modification, ni suppression, ni vidage), chaîné par SHA-256. `ops.verify_audit_chain()` renvoie le premier maillon invalide.

## Ajouter une migration

1. Créer `migrations/AAAAMMJJHHMMSS_nom.sql` avec une section `-- migrate:up` et une section `-- migrate:down`.
2. Donner les droits nécessaires aux rôles : les nouvelles tables de `network`, `mobility` et `identity` reçoivent ceux de leur schéma par défaut.
3. Pour une table métier : ajouter `city_id`, `is_fictional` et la clé composite. Un test le vérifie pour toutes les tables.
4. Lancer `make db-test`.

## Données de développement

- `dev/roles.sql` crée les comptes de connexion locaux (`nemesis_api_dev`, etc.). Mot de passe : variable `NEMESIS_DEV_PASSWORD`, voir `.env.example`.
- `../fixtures_fictives/db/seed.sql` charge la ville fictive « Lagune-Fictive », placée en pleine mer pour ne jamais être confondue avec un lieu réel (H-027). Le jeu complet, généré, arrive en I0.5.
