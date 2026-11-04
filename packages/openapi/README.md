# packages/openapi

Contrat de l'API principale : [openapi.yaml](openapi.yaml), OpenAPI 3.1, `/v1` (partie 9.6). Il est utilisé par l'API (types, tests de contrat), puis par l'appli, le back-office et les canaux.

## Règles du contrat

Elles sont vérifiées par `test/contract-rules.test.ts`, en plus du linter Redocly :

- **Honnêteté (règle 1.3.2)** : toute estimation (`x-estimate: true` : attente, durée, prix, file, série d'attente) exige un objet `meta` (`EstimateMeta`) avec `observed_at`, `confidence` et `source`. Un schéma qui porte des valeurs d'estimation sans être marqué comme estimation est refusé.
- **Idempotence** : toute écriture exige l'en-tête `Idempotency-Key`. Seule la recherche d'itinéraire, une lecture en POST, est déclarée `x-safe`.
- **Limites de débit** : chaque opération déclare `x-rate-limit` et une réponse 429 (en-têtes `Retry-After` et `RateLimit-*`).
- **Erreurs** : toujours `application/problem+json` (RFC 9457).
- **Cache** : une réponse avec `ETag` accepte `If-None-Match` et répond 304.
- **Pagination** : par curseur (`items`, `next_cursor`).
- **Données fictives** : les réponses de données portent `is_fictional`.

`x-implemented: true` marque les opérations servies par l'API actuelle. Pour elles seules, des tests de contrat sont générés automatiquement dans `services/api/test/contract.test.ts`.

## Commandes

```bash
pnpm --filter @nemesis/openapi run lint:openapi   # Redocly
pnpm --filter @nemesis/openapi run types          # régénère src/schema.ts après une modification
pnpm --filter @nemesis/openapi test               # règles du projet
```

`src/schema.ts` est généré par openapi-typescript. Le script `types:check`, lancé en CI, vérifie qu'il reste à jour.

Le contrat temps réel en Protocol Buffers (`nemesis.live.v1.TileDelta`, ADR-006) est dans [packages/proto](../proto/README.md).
