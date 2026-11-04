# apps/mobile

Appli Flutter (usagers, puis mode Pro). Android d'abord, `minSdk 26` (Android 8.0).

- Contrôles : `make check-mobile` depuis la racine (pub get, traductions, format, analyse, tests).
- Traductions : `lib/l10n/app_fr.arb` ; les fichiers Dart sont générés par `flutter gen-l10n` et ne sont pas versionnés.
- Identifiant d'application provisoire `ci.nemesis.nemesis_mobile` : il sera fixé avec le nom public, avant la première publication (H-003).
- Écrans du prototype : incrément I0.11.
