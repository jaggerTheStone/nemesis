# services/api

API principale : NestJS 12 (ESM) sur Fastify, REST versionné sous `/v1` (partie 9.6, ADR-002). Elle suit le contrat [packages/openapi](../../packages/openapi/README.md).

## Ce que sert le squelette (I0.6)

| Route | Contenu |
|-------|---------|
| `GET /v1/health` | Sonde de vie |
| `GET /v1/cities` | Villes couvertes, avec `is_fictional` |
| `GET /v1/places?q=&city=&near=&limit=` | Recherche tolérante aux fautes, aux abréviations et aux accents (trigrammes, partie 8.4). Une gare n'apparaît qu'une fois, comme arrêt |
| `GET /v1/stops/{id}?at=` | Fiche d'arrêt (F-06) : lignes et destinations, prix observés, file en direct (signalement de moins de 30 min) ou estimation historique présentée comme telle, série d'attente du jour. Rien n'est inventé en l'absence de données |

Caractéristiques communes :
- erreurs au format problème (RFC 9457) ;
- `ETag` et réponse 304 ;
- compression Brotli au-delà de 1 Ko ;
- connexion à la base avec le rôle `nemesis_api`, qui n'a aucun accès aux identités (H-016).

Les autres opérations du contrat arrivent en phase 1.

## Lancer

```bash
make dev                                   # base, Valkey, NATS, tuiles ; jeu fictif chargé
pnpm --filter @nemesis/openapi run build
pnpm --filter @nemesis/api build && pnpm --filter @nemesis/api start
curl "http://127.0.0.1:3000/v1/places?city=lagune-fictive&q=flamboyant"
```

Variables : `DATABASE_URL` (par défaut, le compte `nemesis_api_dev` de l'environnement local), `DATABASE_ROLE` (rôle de groupe à endosser, facultatif) et `PORT` (3000).

## Tests

- `pnpm --filter @nemesis/api test` : sans base, seuls les tests sans base tournent ; les tests de contrat sont ignorés.
- `make api-test` : tests de contrat contre une base PostGIS jetable. La base est migrée par dbmate avec le jeu fictif, l'API endosse le rôle `nemesis_api`.
  - Pour chaque opération implémentée, les tests sont générés depuis le contrat : réponse 200 valide, 304 sur l'ETag, 400 au format problème quand un paramètre obligatoire manque.
  - S'y ajoutent des tests de comportement : recherche, passage à l'historique, absence d'estimation inventée, compression, rôle.
- En CI : job « API contre la base » du workflow TypeScript.
