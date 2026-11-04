# ADR-001 — Stack de l'application mobile

- **Statut** : proposé. Il sera figé en I0.11, après mesure sur le prototype.
- **Date** : 2026-11-04
- **Casquettes consultées** : ingénieur mobile, architecte, chercheur UX, product manager

## Contexte

L'appli doit fonctionner sur Android 8.0 avec 2 Go de mémoire et en 3G instable (règle 1.3.3). Elle doit pouvoir calculer un itinéraire hors ligne, afficher une carte vectorielle et partager le moteur d'itinéraires avec le serveur. iOS vient ensuite, avec la même base de code si possible (9.1).

Budgets bloquants (partie 9.3) :
- téléchargement : 20 Mo au plus, objectif 15 Mo ;
- démarrage à froid : 2,5 s ;
- mémoire : 150 Mo ;
- carte : 30 images par seconde avec 200 marqueurs.

## Options envisagées

| Critère (partie 9) | Flutter | Kotlin natif | React Native | Appli web progressive |
|--------------------|---------|--------------|--------------|-----------------------|
| Poids de l'appli | Moteur Flutter embarqué : surcoût fixe, à mesurer | Le plus léger | Moteur JavaScript embarqué : surcoût fixe | Rien à installer |
| Performance sur entrée de gamme | Bonne, rendu propre au framework | La meilleure | Correcte ; le pont JavaScript coûte sur les petits processeurs | Dépend du navigateur ; carte lourde |
| Hors ligne, moteur Rust embarqué | Oui, via flutter_rust_bridge | Oui, via JNI (uniffi) | Possible, via un module natif | Possible en WebAssembly, mais stockage et arrière-plan limités |
| Localisation en arrière-plan, géorepérage | Par des plugins | Natifs | Par des plugins | Insuffisant pour le suivi de trajet |
| iOS | Même base de code | Seconde base de code (Swift) | Même base de code | Oui |
| Recrutement en Côte d'Ivoire | À vérifier auprès de recruteurs locaux | À vérifier | À vérifier | Le plus large (web) |
| Maturité de la carte | maplibre_gl, plugin autour des SDK natifs ; le coût des vues natives intégrées sur les vieux téléphones est à mesurer | SDK MapLibre Android, mature | Plugin MapLibre | MapLibre GL JS, mature |

L'appli web progressive est écartée pour l'appli principale : le suivi de trajet en arrière-plan et les alertes de descente l'exigent. Elle reste la bonne solution pour les pages légères partagées (11.6).

## Décision proposée

**Flutter**, à condition que le prototype d'I0.11 tienne ces seuils, mesurés en build de production :

| Mesure | Seuil pour garder Flutter |
|--------|---------------------------|
| APK arm64-v8a, avec carte, SQLite (drift) et `routing-core` | 15 Mo au plus |
| Démarrage à froid jusqu'à l'écran de recherche, téléphone de référence | 2,5 s au plus |
| Mémoire en usage normal (recherche, résultats, carte) | 150 Mo au plus |
| Carte avec 200 marqueurs | 30 images par seconde |

Si un seuil est dépassé de plus de 20 % sans correction crédible, on passe à **Kotlin natif** pour Android. iOS arrive alors plus tard, en Swift, et cette alternative est explicitement prévue par la partie 9.1.

**Désaccord entre casquettes.** L'ingénieur mobile préfère Kotlin pour le poids et la carte. Le product manager et l'architecte préfèrent Flutter : une seule base de code pour Android et iOS, et des itinéraires identiques en ligne et hors ligne grâce au moteur Rust partagé. On tranche par la mesure, pas par préférence. L'émulateur ne suffit pas pour le démarrage, la mémoire et la batterie : il faut un vrai téléphone de référence (question Q-02).

## Conséquences

- **Ce qui ne dépend pas de ce choix** : la logique métier lourde vit dans `routing-core` (Rust) et dans l'API. Un changement de stack ne réécrit donc que l'interface.
- **Coût** : surcoût de poids et de mémoire de Flutter, accepté contre une seule base de code. La liaison Rust ajoute de la complexité au build : une bibliothèque par architecture de processeur.
- **Réversibilité** : moyenne. La réécriture de l'interface en Kotlin représente quelques semaines pour le MVP. Les données (SQLite, pack ville) et les contrats d'API restent inchangés.
- **À revoir si** un des seuils n'est pas tenu, ou si le plugin de carte ne suit pas les versions de MapLibre.
