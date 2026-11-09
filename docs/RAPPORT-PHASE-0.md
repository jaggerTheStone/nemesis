# Rapport de la phase 0 — Fondations

Statut : version 1 du 2026-11-09, **à relire par le porteur**. Plan : [PHASE-0.md](PHASE-0.md). Suivi au jour le jour : [ETAT.md](ETAT.md).

## En bref

- **Critère de fin atteint.** Un itinéraire réel d'Abidjan se calcule de bout en bout en CI, sur le GTFS 2023 et le graphe piéton OSM : 43 ms en médiane, 123 ms au 95ᵉ centile. L'intégration continue est au vert. Chaque décision structurante a son ADR, de 001 à 009.
- **Ce qui reste au porteur.** Une seule ADR est acceptée (ADR-003, le moteur). Les autres sont « proposées ». L'ADR-001 (stack mobile) attend une décision : le prototype mesuré dépasse le budget de poids.
- **Ce qui bloque la suite.** Pas de collecte réelle sans équipe sur place (Q-03). Rien de personnel sans avis juridique (Q-07). Pas d'usage produit du GTFS 2023 sans l'accord de son auteur (H-030).
- **La démo** tient en une commande, hors ligne, en moins de 5 minutes : `make demo`.

## Fait : les livrables de la partie 15.1

| Livrable | État | Preuve |
|----------|------|--------|
| 1. Documents et premiers ADR | Fait, à relire | ARCHITECTURE, DATA, PRIVACY, COUTS, ALGORITHMES ; ADR-001 à ADR-009 ; 35 hypothèses ([HYPOTHESES.md](HYPOTHESES.md)) |
| 2. Monorepo, CI verte, `docker compose up` | Fait | 13 workflows ; `make dev` lance PostGIS, Valkey, NATS, Caddy et les migrations |
| 3. Schéma complet et OpenAPI v0 | Fait | 8 migrations dbmate, 25 tests de base ; OpenAPI 3.1 (26 opérations) et Protobuf contrôlés par buf |
| 4. Pipelines OSM, GTFS, tuiles et rapports | Fait | Import réel hebdomadaire en CI : 33 284 lieux, 4 815 arrêts du GTFS sur 4 834 retrouvés dans OSM, tuiles d'Abidjan de 4,5 Mo |
| 5. Fixtures fictives et simulateur v0 | Fait | Ville « Lagune-Fictive » (GTFS, extension, SQL, OSM, pack, données de l'appli) ; une journée de pointe simulée en 0,1 s |
| 6. Moteur d'itinéraires en ligne de commande | Fait | `routing plan` et `routing bench` ; McRAPTOR à quatre critères, attentes tirées 500 fois ; workflow « Itinéraire réel de bout en bout » |
| 7. Prototype cliquable et protocoles UX et WhatsApp | Fait, ADR-001 en attente | Appli Flutter hors ligne avec le moteur natif, fumée sur Android 8 ; protocole WhatsApp prêt, bloqué par Q-07 |
| 8. Kit de campagne terrain | Fait | Huit fiches imprimables ; treize formats d'échange validés en CI ; protocole qualité avec `nemesis-terrain accord` |

Le détail de chaque incrément, avec ses limites, est dans [PHASE-0.md](PHASE-0.md), de I0.1 à I0.13.

## Lancement

Prérequis : uv 0.11.32 et la chaîne Rust de `rust-toolchain.toml`. Flutter 3.47.7 pour l'appli, Docker pour la base.

```bash
uv sync --locked --all-packages
```

```bash
make demo
```

La démo enchaîne cinq étapes, sans réseau ni base de données :

1. vérifier que le jeu fictif est à jour de son générateur ;
2. compiler le moteur, puis calculer un itinéraire fictif à 7 h 30 : quatre options étiquetées, avec durées p50 et p80, prix en fourchette et régime d'attente de chaque montée ;
3. simuler une journée du corridor G1, puis mesurer la couverture du p80 des formules d'attente ;
4. valider les données de terrain fictives et mesurer l'accord des doubles relevés ;
5. calculer un itinéraire réel si le pack d'Abidjan est présent ; sinon, renvoyer au workflow de CI qui le fait.

`make demo DEMO_OPTIONS=--avec-mobile` ajoute les tests des parcours de l'appli. Le compte rendu est écrit dans `data/work/demo/demo.md`. La démo échoue si une étape échoue ou si elle dépasse 5 minutes.

Durées mesurées : 6 s quand le moteur est déjà compilé, 80 s avec la compilation et les tests de l'appli. Le workflow « Démo de la phase 0 » la rejoue sur une machine neuve et publie le compte rendu dans le résumé de l'exécution.

Autres points d'entrée :

| Pour | Commande |
|------|----------|
| Tout vérifier, hors réseau | `make check` |
| L'environnement local (base, cache, bus) | `make dev` |
| Les tests contre une base jetable | `make db-test`, `make api-test`, `make pipelines-test` |
| La chaîne d'import fictive | `make data-import-fictif` |
| Un itinéraire réel | `uv run nemesis-data pack reel`, puis `services/routing/target/release/routing plan` (réseau requis, voir [services/routing/README.md](../services/routing/README.md)) |
| L'appli sur un téléphone | [apps/mobile/README.md](../apps/mobile/README.md) |

## Tests

| Composant | Tests | Workflow |
|-----------|-------|----------|
| Moteur d'itinéraires (Rust) | 40, dont 3 par propriétés | ci-rust, routing-real, routing-spike |
| Pipelines de données, terrain, jeu fictif (Python) | 110, et 6 contre une base | ci-python, data-pipelines, data-import, ci-gtfs |
| Simulateur (Python) | 19 | ci-python |
| Appli mobile (Flutter) | 35, dont 14 références visuelles à 100 % et 200 % de texte ; fumée sur émulateur API 26 | ci-mobile |
| API (NestJS) | 2, et 20 contre une base | ci-typescript |
| Contrat OpenAPI | 19 | ci-typescript |
| Canaux SMS, web léger, back-office | 9, 4, 1 | ci-typescript |
| Service d'apprentissage (FastAPI) | 1 | ci-python |
| Base de données | 25 | ci-database |
| Documentation | liens vérifiés | docs |
| Sécurité | Trivy, audits de dépendances, cargo-deny | security |
| Démo | `make demo` sur machine neuve | demo |

Trois vérifications portent le plus de confiance :

- **la comparaison avec OpenTripPlanner** (spike I0.8) : 375 requêtes, une même fonction de coût, et un défaut de reconstruction trouvé grâce à elle ;
- **le simulateur** : il confronte les formules d'attente à une vérité connue. Il a montré que la formule du régime B sous-couvre le p80 (63 % pour 80 % visés) ; des corrections sont proposées ;
- **l'itinéraire réel en CI**, qui tourne à chaque modification du moteur.

## Limites

### Simplifications signalées (règle 1.3.8)

La liste complète, avec le retour prévu de chacune, est dans [PHASE-0.md](PHASE-0.md#simplifications-signalées-règle-138). Les plus visibles :

- **aucune donnée observée** : les attentes du régime A et les prix ne viennent que des fixtures. Sur les données réelles, le moteur répond « prix inconnu » ;
- **pas de pénalités de marche** (traversées dangereuses, zones inondées) ni de temps à bord variable ;
- **un simulateur à un corridor et un sens**, avec des comportements inventés (H-033) ;
- **pas d'infrastructure cible, de pile d'observabilité ni de tests de charge** : ils attendent l'ADR-004 et des services à charger.

### Données réelles

- **Le GTFS 2023 sert d'évaluation, jamais d'état présenté comme actuel** : sa licence interdit l'usage commercial (H-030), et il précède l'interdiction d'Adjamé aux gbakas (mars 2025) puis la réorganisation de l'AMUGA (octobre 2026). La base refuse toute entrée de ce GTFS dans le réseau.
- **Son calendrier ne couvre que 2023** : les itinéraires réels se calculent à des dates de 2023.
- **28 % de ses courses ont une durée forfaitaire de 120 min** : les durées réelles ne valent donc qu'à titre indicatif.

### Mesures manquantes

- **Pas de téléphone de référence** (Q-02) : démarrage et mémoire de l'appli mesurés sur émulateur, à titre indicatif ; fluidité de la carte non mesurée.
- **Pas de collecte réelle** (Q-03) : les seuils de qualité de la campagne et les 300 requêtes et 200 trajets de référence attendent une équipe sur place.

### Environnement de développement

L'environnement cloud bloque Geofabrik, GHCR et le build Android (H-021). Ces parties ne se vérifient qu'en GitHub Actions, avec des boucles de correction plus lentes.

## Décisions en attente du porteur (partie 15.6)

Par ordre d'impact sur la phase 1 :

1. **ADR-001, stack mobile.** L'APK arm64 pèse 52,5 Mo, soit environ 21,3 Mo à télécharger pour un budget de 20 Mo. La carte MapLibre en prend 10,8 Mo. Recommandation : mesurer une carte dessinée en Dart avant de choisir entre Flutter et Kotlin natif.
2. **Le corridor pilote (Q-05)** : il fixe les gares, les lignes et les couples origine-destination de la phase 1.
3. **Une équipe sur place (Q-03)**, pour lancer la campagne « Éclaireurs », les requêtes réelles et les trajets de référence.
4. **L'avis juridique (Q-07, H-020)** : il débloque le mode relevé, le protocole WhatsApp et toute donnée personnelle.
5. **La licence du GTFS 2023 (H-030)** : demander l'autorisation à DigitalTransport4Africa, avec un juriste.
6. **ADR-004, hébergement et transfert des données** : il conditionne l'infrastructure et le dossier ARTCI.
7. **Les corrections des formules d'attente** proposées après le simulateur (ALGORITHMES.md 1.2 et 1.3).
8. **La relecture des ADR proposées** (002, 005 à 009) et des hypothèses H-022 à H-035.
9. **Le téléphone de référence (Q-02)**, pour les mesures de l'ADR-001 et de la batterie du mode relevé.

La liste complète, avec les prix de COUTS.md et les questions au juriste, est dans [ETAT.md](ETAT.md#où-en-est-on).

## Risques

- **Données vieillissantes** : tant que la campagne n'a pas commencé, le réseau du pilote n'a pas de source actuelle.
- **Poids de l'appli** : si aucune option de carte ne tient le budget, l'ADR-001 bascule vers Kotlin natif, et le prototype Flutter est à refaire.
- **Formule du régime B** : sans correction, elle annonce des attentes trop optimistes, surtout sous la pluie. C'est le cœur de la promesse « fraîcheur et confiance ».
- **Compétences Rust à Abidjan** : le moteur retenu (ADR-003) est plus rare à recruter.

## Prochaine étape : la phase 1

La partie 15.2 prévoit 10 à 12 semaines pour le MVP sur le corridor pilote, en tranches verticales. Ce que la phase 0 prépare pour chacune :

| Tranche | Ce qui existe | Ce qui manque avant de commencer |
|---------|---------------|-----------------------------------|
| 1. Données et modèle de réseau, puis moteur | Schéma versionné, imports, extension GTFS, moteur et pack ville | Le corridor (Q-05) et ses premiers relevés |
| 2. API d'itinéraire, écrans et pack hors ligne | Contrat OpenAPI, squelette d'API, prototype et moteur natif | La décision de l'ADR-001 |
| 3. Fiche gare, contributions, files | Format des signalements, simulateur pour régler l'agrégation | Les corrections des formules d'attente |
| 4. Suivi de trajet et alertes de descente | Pas à pas du prototype | L'avis juridique sur la position (Q-07) |
| 5. Back-office | Squelette React, versions du réseau, audit chaîné | — |
| 6. Partage de trajet et bouton d'urgence | Cadre de PRIVACY.md | L'avis juridique (Q-07) |

Proposition : commencer la phase 1 par la tranche 1, dès que le corridor est choisi. Elle ne dépend ni de l'ADR-001 ni de Q-07. Le plan détaillé de la phase 1 sera soumis au porteur avant tout code, comme celui de la phase 0.
