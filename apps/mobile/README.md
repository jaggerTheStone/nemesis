# apps/mobile

Appli Flutter (usagers, puis mode Pro). Android d'abord, `minSdk 26` (Android 8.0).

Depuis I0.11, un **prototype cliquable** sur la ville fictive Lagune-Fictive. Il fonctionne entièrement hors ligne, sans serveur, et affiche toujours le bandeau « DONNÉES FICTIVES ».

## Ce que fait le prototype

- **Trois onglets et un bouton** (10.2) : Trajet, Carte, Moi, et le bouton flottant Signaler.
- **Trajet**, pour aller d'un point à un autre :
  - accueil « Tu vas où ? », avec les raccourcis Maison, Boulot, École, les trajets récents et les gares autour de moi ;
  - recherche de lieux sans accents ni casse, par les alias (F-01) ;
  - résultats : une carte par option, étiquetée « Le moins cher », « Le plus rapide » ou « Le plus simple ». Chaque carte donne la durée et le prix en fourchette, l'attente, les changements et la marche ;
  - pas à pas : comment reconnaître le véhicule, ce que crie l'apprenti, combien prévoir, où descendre (F-03).
- **Fiche gare** (F-06) : lignes, attente habituelle présentée comme une estimation historique, meilleure heure pour partir, prix par destination.
- **Signaler en deux pressions** (F-07). Les signalements suivent le format `ContributionRequest` et les conventions de H-033. Ils restent dans une file SQLite sur le téléphone, faute de serveur.
- **« Pourquoi cette estimation ? »** (10.2) : d'où vient le chiffre, quand, qui l'a confirmé, avec la confiance.
- **Carte** : MapLibre, hors ligne, sans tuiles. Les rues, les lignes et les arrêts viennent de GeoJSON embarqué ; une légende reste visible.

Pas encore de dictée, de lecture vocale, de suivi « Je pars » ni de lieux enregistrés : le prototype affiche « bientôt ».

## Architecture

| Dossier | Contenu |
|---------|---------|
| `lib/design` | Jetons de design : couleurs claires et sombres, espacements, typographie de 16 sp au moins, zones tactiles de 48 dp. Styles des modes avec les codes du test d'icônes |
| `lib/data` | Ville embarquée et recherche ; stockage SQLite (`sqlite3`) des signalements et trajets récents |
| `lib/routing` | Interface `RoutingService`, et le moteur natif appelé par `dart:ffi` |
| `lib/screens`, `lib/widgets` | Écrans et composants (carte d'option, puce de mode, badges, étape, feuilles) |
| `assets/fictif` | Données générées par `uv run nemesis-fixtures generer`, ne pas modifier à la main |

**Le moteur d'itinéraires est celui du serveur.** C'est la bibliothèque Rust `services/routing/crates/routing-ffi`, `libnemesis_routing.so`, construite par cargo-ndk pour arm64-v8a et x86_64. Au démarrage, le pack ville est copié hors de l'APK, puis chaque calcul tourne dans un isolate. La bibliothèque n'est pas versionnée : elle est construite en CI.

## Lancer les contrôles

- `make check-mobile` depuis la racine : pub get, traductions, format, analyse, tests.
- **Test du moteur natif** : il demande la bibliothèque de la machine.

  ```bash
  cd services/routing && cargo build --release -p routing-ffi
  ```

  ```bash
  NEMESIS_ROUTING_LIB=$PWD/services/routing/target/release/libnemesis_routing.so make check-mobile
  ```

- **Références visuelles** (`test/goldens`, à 100 % et 200 % de taille de texte) : après un changement d'écran voulu, les régénérer avec `flutter test --update-goldens`.
- **SQLite** : dans les tests sur ordinateur, c'est la bibliothèque du système (Linux). Dans l'APK, c'est celle publiée avec le paquet `sqlite3`, vérifiée par SHA-256. Voir `hooks` dans `pubspec.yaml`.

En CI (workflow « Mobile (Flutter) ») :
- analyse et tests, dont le moteur natif ;
- APK arm64 de production, dont le poids total et par composant est écrit dans le résumé ;
- test de fumée sur un émulateur Android 8 (API 26).

## Notes

- Traductions : `lib/l10n/app_fr.arb` (modèle) et `app_fr_CI.arb`. Les fichiers Dart sont générés par `flutter gen-l10n` et ne sont pas versionnés.
- Identifiant d'application provisoire `ci.nemesis.nemesis_mobile` : il sera fixé avec le nom public, avant la première publication (H-003).
- Versions des dépendances épinglées, publiées depuis au moins 14 jours.
