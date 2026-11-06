# ADR-001 — Stack de l'application mobile

- **Statut** : proposé, **mesuré en I0.11**. Le seuil de poids est dépassé : **décision du porteur** (15.6).
- **Date** : 2026-11-04, mesures du 2026-11-06
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
| Hors ligne, moteur Rust embarqué | Oui, via `dart:ffi` (mesuré en I0.11) | Oui, via JNI (uniffi) | Possible, via un module natif | Possible en WebAssembly, mais stockage et arrière-plan limités |
| Localisation en arrière-plan, géorepérage | Par des plugins | Natifs | Par des plugins | Insuffisant pour le suivi de trajet |
| iOS | Même base de code | Seconde base de code (Swift) | Même base de code | Oui |
| Recrutement en Côte d'Ivoire | À vérifier auprès de recruteurs locaux | À vérifier | À vérifier | Le plus large (web) |
| Maturité de la carte | maplibre_gl, plugin autour des SDK natifs | SDK MapLibre Android, mature | Plugin MapLibre | MapLibre GL JS, mature |

L'appli web progressive est écartée pour l'appli principale : le suivi de trajet en arrière-plan et les alertes de descente l'exigent. Elle reste la bonne solution pour les pages légères partagées (11.6).

## Règle fixée en I0.3

**Flutter**, à condition que le prototype d'I0.11 tienne ces seuils, mesurés en build de production :

| Mesure | Seuil pour garder Flutter |
|--------|---------------------------|
| APK arm64-v8a, avec carte, SQLite et `routing-core` | 15 Mo au plus |
| Démarrage à froid jusqu'à l'écran de recherche, téléphone de référence | 2,5 s au plus |
| Mémoire en usage normal (recherche, résultats, carte) | 150 Mo au plus |
| Carte avec 200 marqueurs | 30 images par seconde |

Si un seuil est dépassé de plus de 20 % sans correction crédible, on passe à **Kotlin natif** pour Android.

## Mesures (I0.11)

Prototype `apps/mobile`, construit en CI (workflow « Mobile (Flutter) ») :
- Flutter 3.47.7 ;
- carte `maplibre_gl` 0.27.1, avec le SDK MapLibre Android 13.5 ;
- `sqlite3` 3.7.1 ;
- moteur `routing-ffi` compilé en LTO, symboles retirés.

**APK arm64-v8a de production : 52,5 Mo.** Les bibliothèques natives y sont rangées sans compression, alignées sur les pages mémoire, comme le veut Android depuis la version 6. Le magasin d'applications les compresse au téléchargement. La colonne « compressé » estime donc ce que l'usager télécharge.

| Composant | Dans l'APK | Compressé |
|-----------|-----------|-----------|
| Carte MapLibre (bibliothèque native) | 30,0 Mo | **10,8 Mo** |
| Moteur Flutter | 11,8 Mo | 5,5 Mo |
| Code Dart compilé | 5,7 Mo | 2,2 Mo |
| SQLite | 1,75 Mo | 0,9 Mo |
| Moteur d'itinéraires (Rust) | 1,6 Mo | 0,8 Mo |
| Code Java et Kotlin des plugins | 0,7 Mo | 0,7 Mo |
| Ressources, données fictives, divers | 0,8 Mo | 0,5 Mo |
| **Total** | **52,5 Mo** | **≈ 21,3 Mo** |

Ce qu'on en tire :
- **Le budget de téléchargement n'est pas tenu** : environ 21,3 Mo pour 20 Mo au plus et 15 Mo visés. L'APK lui-même dépasse de loin son seuil de 15 Mo.
- **La carte en est la cause principale.** La bibliothèque MapLibre pèse à elle seule 10,8 Mo compressés : plus que tout le reste de l'appli, Flutter compris. Elle pèserait autant en Kotlin natif.
- **Le surcoût propre à Flutter est d'environ 7,8 Mo compressés** : son moteur et le code Dart compilé.
- **Le moteur d'itinéraires partagé ne coûte presque rien** : 0,8 Mo pour des itinéraires identiques en ligne et hors ligne.
- **Démarrage et mémoire** : mesurés sur l'émulateur Android 8, à titre indicatif seulement. L'émulateur ne remplace pas le téléphone de référence (Q-02).
- **Fluidité de la carte avec 200 marqueurs** : non mesurée. Elle exige le téléphone de référence.

## Options après mesure

| Option | Téléchargement estimé | Pour | Contre |
|--------|-----------------------|------|--------|
| **A. Flutter et MapLibre, tel quel** | ≈ 21 Mo | Mesuré, fonctionne | Hors budget |
| **B. Flutter, carte dessinée en Dart (type flutter_map avec tuiles vectorielles), SQLite du système** | ≈ 11 à 12 Mo (estimation : A moins MapLibre et SQLite, plus environ 1 Mo de code Dart) | Une seule base de code ; dans l'objectif de 15 Mo | Fluidité de la carte à prouver (30 images par seconde avec 200 marqueurs sur un téléphone de 2 Go) ; écosystème moins mûr que MapLibre |
| **C. Kotlin natif et MapLibre** | ≈ 12 à 13 Mo (estimation : MapLibre, moteur Rust, code Kotlin, SQLite du système) | Dans le budget ; carte mûre | Seconde base de code pour iOS ; interface à réécrire (quelques semaines) |
| **D. Flutter et MapLibre, carte livrée à la demande** | ≈ 10,5 Mo à l'installation, puis environ 11 Mo à la première ouverture de la carte | Une seule base de code | Livraison dynamique d'une bibliothèque native d'un plugin Flutter : non éprouvée, complexe |

## Recommandation

**Mesurer B avant de trancher.** Un prototype de carte en Dart sur les données fictives ne demande que quelques jours. Il donnerait le poids réel et la fluidité sur le téléphone de référence dès qu'il existe (Q-02).
- **Si B tient 30 images par seconde avec 200 marqueurs**, Flutter est gardé, avec cette carte.
- **Sinon, C** : Kotlin natif pour Android, iOS plus tard en Swift, comme le prévoit déjà la partie 9.1.
- **A est écartée** : il dépasse le budget de téléchargement.

En attendant, le prototype I0.11 reste en Flutter et MapLibre : il sert aux tests de maquettes, où le poids ne compte pas.

**Désaccord entre casquettes.** L'ingénieur mobile voit dans la mesure la confirmation de Kotlin. Le product manager et l'architecte notent que l'essentiel du poids vient de la carte, quel que soit le choix de stack, et qu'une seule base de code garde sa valeur pour iOS. La mesure de B tranchera.

## Conséquences

- **Ce qui ne dépend pas de ce choix** : la logique lourde vit dans le moteur Rust et l'API. Elle est déjà partagée par une interface C (`routing-ffi`), utilisable aussi bien en Kotlin qu'en Flutter. De même pour les données (pack ville, SQLite) et les contrats d'API.
- **Le budget de la carte devient un sujet en soi**, quel que soit le choix : bibliothèque, style, fond de carte (ADR-009).
- **À revoir si** B ne tient pas la fluidité, si le budget de téléchargement est révisé, ou si MapLibre publie une bibliothèque nettement plus légère.
