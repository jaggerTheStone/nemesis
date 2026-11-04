# services/api

API principale : NestJS (ESM) sur Fastify, REST versionné sous `/v1` (partie 9.6). Le choix final du langage fait l'objet de l'ADR-002 (I0.3).

- `pnpm --filter @nemesis/api build && PORT=3000 pnpm --filter @nemesis/api start`
- `GET /v1/health` : sonde de vie.
- Les tests compilent avec SWC, car NestJS a besoin des métadonnées de décorateurs.
