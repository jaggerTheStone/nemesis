# ADR-004 — Hébergement et transfert des données hors du pays

- **Statut** : proposé. La décision revient au porteur du projet (partie 15.6) et doit être validée juridiquement.
- **Date** : 2026-11-04
- **Casquettes consultées** : expert vie privée et sécurité, SRE, architecte, product manager

## Contexte

La loi n°2013-450 encadre le transfert de données personnelles hors de Côte d'Ivoire. Il faut donc choisir entre deux voies (9.2) :
- un hébergement local, dans un centre de données en Côte d'Ivoire ;
- une autorisation de l'ARTCI pour transférer les données à l'étranger.

**Ce qui n'est pas en jeu en phase 0.** Il n'y a pas encore de production et aucune donnée personnelle réelle n'est traitée (H-004, H-020). La décision doit cependant être prise **avant le dépôt du dossier ARTCI**, lui-même requis avant toute collecte réelle. Elle conditionne aussi l'infrastructure de la phase 1.

**Les données ne sont pas toutes personnelles :**

| Catégorie | Exemples | Personnelle ? |
|-----------|----------|---------------|
| Identité | Numéro de téléphone (compte), comptes du back-office | Oui |
| Mobilité brute | Segments de trajets, positions des chauffeurs Pro, contributions horodatées et géolocalisées | Oui : rattachées à un appareil pseudonyme |
| Agrégats | États des files, profils d'attente, prix estimés, vitesses par tronçon | Non, si les seuils d'anonymat sont respectés (k ≥ 20) |
| Données ouvertes et produits | Réseau, tuiles, packs ville | Non |

## Options envisagées

| Critère | 1. Tout en local | 2. Tout à l'étranger, avec autorisation de l'ARTCI | 3. Hybride (recommandé) |
|---------|------------------|----------------------------------------------------|-------------------------|
| Conformité | La plus simple : pas de transfert | Autorisation à obtenir et à maintenir ; délai inconnu | Données personnelles en local ; seuls les agrégats anonymes et les données ouvertes sortent |
| Latence pour les usagers | La meilleure | Dépend de la région choisie | Bonne : API et données personnelles en local |
| Diffusion des tuiles et des packs | CDN à vérifier en local | CDN mondial avec présence en Afrique | CDN mondial pour les tuiles et les packs, sans données personnelles |
| Fiabilité et services gérés | Offre locale à évaluer (énergie, redondance, sauvegardes hors site) | Large choix | Partielle |
| Coût | À chiffrer : offres à recenser | Prix publics, à chiffrer | Entre les deux |
| Compétences d'exploitation | Plus d'administration système | Services gérés | Les deux |
| Réversibilité | Bonne : Docker, puis k3s | Bonne | Bonne |

## Recommandation

**Option 3, hybride.**
- **En Côte d'Ivoire** : l'API, PostgreSQL (schémas `identity` et `mobility`), Redis, NATS et les sauvegardes chiffrées.
- **À l'étranger, derrière un CDN** : les tuiles, les packs et les agrégats anonymes.

**Les sauvegardes** sont des données personnelles. Elles restent dans le pays, sur un second site : un autre centre de données local, ou un stockage chiffré dans le pays.

**Le cas de chaque service tiers est à vérifier.** Certains reçoivent des données personnelles :
- Firebase Cloud Messaging : jeton de l'appareil ;
- passerelle SMS : numéro ;
- WhatsApp Business : numéro et messages.

Ces flux sont des transferts au sens de la loi. Ils doivent figurer au dossier ARTCI, même avec l'option 3.

## Informations à réunir avant de décider

1. Les offres d'hébergement local : prix, redondance électrique et réseau, sauvegardes, assistance, références.
2. La procédure et le délai d'autorisation de transfert auprès de l'ARTCI, avec un juriste ivoirien (question Q-04).
3. La présence des CDN en Côte d'Ivoire ou dans la sous-région, et la latence mesurée depuis Abidjan.
4. Le budget mensuel accepté par le porteur du projet ([COUTS.md](../COUTS.md)).

## Conséquences

- **Architecture.** La séparation `identity` et `mobility` (H-016), déjà prévue, rend l'option 3 naturelle. Rien d'autre ne change tant que la décision n'est pas prise.
- **Infrastructure en code.** Terraform et Ansible sont reportés à la phase 1, après cette décision : simplification signalée dans [PHASE-0.md](../PHASE-0.md).
