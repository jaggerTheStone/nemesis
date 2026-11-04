# ADR-005 — Base de données, partitionnement et conservation

- **Statut** : proposé
- **Date** : 2026-11-04
- **Casquettes consultées** : architecte, ingénieur backend, ingénieur géomatique, expert vie privée, SRE

## Contexte

La base sert deux usages très différents :
- **le réseau** et les données de référence : volume modéré, requêtes spatiales et textuelles, versionnement ;
- **les événements** : contributions, positions et observations, en flux continu et à durée de conservation limitée (12.2). Il faut les écrire vite, les agréger, puis les supprimer à échéance.

**Ordre de grandeur, deuxième année.** Hypothèse de calcul, pas une mesure :
- 2 000 événements par seconde pendant 6,5 h de pointe, et 300 par seconde le reste de la journée, soit environ 66 millions d'événements par jour ;
- avec environ 150 octets par ligne, index compris, cela fait environ 10 Go par jour ;
- avec la conservation des positions brutes limitée à 30 jours, on stocke environ 300 Go.

Ces volumes concernent surtout le capteur passif et le mode Pro, qui arrivent en V2. Au MVP, les volumes sont bien plus faibles.

## Options envisagées

| Critère | PostgreSQL et PostGIS, partitionnement natif | PostgreSQL avec TimescaleDB | PostgreSQL pour le réseau et ClickHouse pour les événements |
|---------|----------------------------------------------|-----------------------------|-------------------------------------------------------------|
| Requêtes spatiales, recherche par trigrammes | Oui (PostGIS, pg_trgm) | Oui | Seulement côté PostgreSQL |
| Purge à échéance | Suppression d'une partition par jour, immédiate | Politiques de conservation intégrées | Durée de vie par table |
| Compression des événements | Non | Oui | Oui, excellente |
| Exploitation | Un seul moteur, bien connu | Extension à maintenir ; conditions de licence de certaines fonctions à vérifier | Deux moteurs à exploiter |
| Coût | Le plus bas au départ | Bas | Plus élevé en exploitation |

## Décision proposée

**PostgreSQL 16 avec PostGIS et pg_trgm, et partitionnement natif par jour** des tables `observation` et `position_event`.

**Organisation de la base :**

| Élément | Choix |
|---------|-------|
| Schémas | `network` (réseau, repères, versions), `mobility` (observations, positions, états dérivés), `identity` (comptes, numéros), `ops` (audit, flux partenaires) |
| Rôles | Un rôle par schéma. L'API n'accède à `identity` que par un rôle dédié, ce qui sépare identité et traces (H-016) |
| Partitions | Créées à l'avance et supprimées à échéance par une fonction de maintenance planifiée. Durées de conservation de [PRIVACY.md](../PRIVACY.md), à valider : positions brutes 30 jours, observations brutes 12 mois |
| Agrégats | Tables ordinaires (`queue_state`, profils d'attente et de prix, vitesses par tronçon), sans limite de durée car anonymes, avec k ≥ 20 pour tout export |
| Géométries | WGS 84 (EPSG:4326). Les calculs de distance se font dans la projection métrique de la ville (EPSG:32630 pour Abidjan), déclarée dans `city` (H-014) |
| État en direct | Stockage compatible Redis (Valkey, voir plus bas), reconstructible à partir de PostgreSQL et du flux NATS |
| Migrations | SQL brut versionné, indépendant du langage de l'API (H-013) |

**Version.** On reste sur PostgreSQL 16, comme le demande la partie 9.1. Des versions plus récentes existent : passer à une version majeure plus récente fera l'objet d'une décision avant la mise en production, en fonction de la durée de support et des extensions disponibles.

**Pourquoi pas TimescaleDB ou ClickHouse dès maintenant ?** Les gros volumes n'arrivent qu'en V2. Le partitionnement natif suffit au MVP et ne dépend d'aucune extension. Si le stockage des événements dépasse les capacités prévues, on réévalue : la compression de TimescaleDB est la piste la moins coûteuse. Seuil proposé : plus de 500 Go ou une purge qui ralentit la base.

## Conséquences

- **La conservation est garantie par la structure** : supprimer la partition d'un jour efface toutes ses lignes d'un coup, sans requête de suppression coûteuse. C'est un argument fort pour le dossier ARTCI.
- **Réversibilité** : bonne. Passer à TimescaleDB transforme les tables partitionnées en hypertables, sans changer l'API.
- **Mise en œuvre** : le schéma complet et ses tests arrivent en I0.4.

## Mise à jour du 2026-11-04 (I0.4, mise en œuvre)

- **Valkey plutôt que Redis.** Depuis la version 8, Redis n'est plus sous licence permissive (AGPL, RSAL ou SSPL). Or la politique du projet n'accepte que des dépendances sous licence permissive (Q-06). Valkey est un fork de Redis sous licence BSD, compatible au niveau du protocole. Dans la documentation, « Redis » désigne désormais ce stockage compatible.
- **Migrations par dbmate** (licence MIT), au format SQL brut `-- migrate:up` / `-- migrate:down`. dbmate est utilisé par Docker Compose et en CI ; les tests rejouent les mêmes fichiers.
- **Contraintes ajoutées par rapport à la version initiale de cet ADR** :
  - **Cohérence fictive** : clé étrangère composite `(city_id, is_fictional)` vers `network.city`.
  - **Cohérence entre villes** : les références passent par `(id, city_id)`.
  - **Honnêteté (règle 1.3.2)** : la confiance, la source et la date de dernière observation sont obligatoires sur les états publiés et les estimations.
  - **Audit** : journal en ajout seul, chaîné par empreintes, vérifiable par `ops.verify_audit_chain()`.
- **Maintenance** : `ops.maintain_partitions()` crée les partitions de 7 jours en arrière à 7 jours en avance, et supprime celles qui ont dépassé leur durée de conservation. `ops.purge_expired()` purge les tables non partitionnées. Leur planification quotidienne reste à mettre en place en phase 1. En développement, elles sont lancées au démarrage.
- **Versionnement du réseau** : voir l'[ADR-008](ADR-008-versionnement-reseau.md).
