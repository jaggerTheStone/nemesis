import 'package:flutter/material.dart';

/// Design tokens (partie 10.3) : couleurs, espacements, rayons, typographie et zones
/// tactiles. Every screen takes its sizes and colours from here, never from literals.
abstract final class Tokens {
  // Spacing scale, dp.
  static const double space1 = 4;
  static const double space2 = 8;
  static const double space3 = 12;
  static const double space4 = 16;
  static const double space5 = 24;
  static const double space6 = 32;

  static const double radius = 16;
  static const double radiusLarge = 28;

  /// Smallest touch target (10.3).
  static const double touch = 48;

  /// Type scale, sp. Body text is never under 16 sp (10.3).
  static const double textBody = 16;
  static const double textLabel = 14;
  static const double textTitle = 20;
  static const double textHeadline = 24;
  static const double textDisplay = 28;

  // Colours of the yafohi charter (docs/UX/identite-yafohi) : high contrast, readable
  // in full sun (10.3). Mango never carries white text, only ink.
  static const Color ink = Color(0xFF16130F);
  static const Color inkMuted = Color(0xFF5E574C);
  static const Color paper = Color(0xFFFFF9EE);
  static const Color card = Color(0xFFFFFFFF);
  static const Color surface = Color(0xFFFFF2D9);
  static const Color line = Color(0xFFF0E3C8);
  static const Color brand = Color(0xFF16130F);
  static const Color onBrand = Color(0xFFFFFFFF);
  static const Color accent = Color(0xFFFFC21A);
  static const Color onAccent = Color(0xFF16130F);
  static const Color fictional = Color(0xFFA4001D);
  static const Color onFictional = Color(0xFFFFFFFF);

  // Dark mode, to save battery (10.3).
  static const Color inkDark = Color(0xFFF4F1EA);
  static const Color paperDark = Color(0xFF16130F);
  static const Color surfaceDark = Color(0xFF26221C);
  static const Color brandDark = Color(0xFFFFC21A);

  /// Typefaces of the charter, embedded (SIL Open Font License).
  static const String fontText = 'Nunito';
  static const String fontDisplay = 'Baloo 2';
}

/// State of a queue (F-05) : couleur, icône et mot — jamais la couleur seule.
enum QueueLevel {
  peu(Color(0xFF1F7A47), Icons.sentiment_satisfied_alt),
  moyen(Color(0xFFA35A00), Icons.sentiment_neutral),
  beaucoup(Color(0xFFC2332B), Icons.sentiment_dissatisfied),
  tresLong(Color(0xFF7A0019), Icons.sentiment_very_dissatisfied),
  inconnu(Color(0xFF5F6368), Icons.help_outline);

  const QueueLevel(this.color, this.icon);

  final Color color;
  final IconData icon;

  /// Value of the `level` payload of a `file` report (H-033).
  String get apiValue => this == tresLong ? 'tres_long' : name;
}

/// Confidence of an estimate (DATA.md) : badge plein, moyen ou faible.
enum Confidence {
  elevee(Icons.circle),
  moyenne(Icons.contrast),
  faible(Icons.circle_outlined),
  inconnue(Icons.help_outline);

  const Confidence(this.icon);

  final IconData icon;

  static Confidence parse(String? value) => switch (value) {
    'elevee' => elevee,
    'moyenne' => moyenne,
    'faible' => faible,
    _ => inconnue,
  };
}

ThemeData buildTheme(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final scheme = ColorScheme.fromSeed(
    seedColor: Tokens.brand,
    brightness: brightness,
    primary: dark ? Tokens.brandDark : Tokens.brand,
    onPrimary: dark ? Tokens.ink : Tokens.onBrand,
    primaryContainer: dark ? Tokens.surfaceDark : Tokens.surface,
    onPrimaryContainer: dark ? Tokens.inkDark : Tokens.ink,
    secondaryContainer: Tokens.accent,
    onSecondaryContainer: Tokens.onAccent,
    surfaceContainerHighest: dark ? Tokens.surfaceDark : Tokens.surface,
    outlineVariant: dark ? const Color(0xFF3A342B) : Tokens.line,
    secondary: Tokens.accent,
    onSecondary: Tokens.onAccent,
    surface: dark ? Tokens.paperDark : Tokens.paper,
    onSurface: dark ? Tokens.inkDark : Tokens.ink,
    error: Tokens.fictional,
  );
  const body = TextStyle(
    fontSize: Tokens.textBody,
    height: 1.35,
    fontWeight: FontWeight.w600,
  );
  final text = TextTheme(
    displaySmall: const TextStyle(
      fontFamily: Tokens.fontDisplay,
      fontSize: Tokens.textDisplay,
      fontWeight: FontWeight.w800,
      height: 1.1,
    ),
    headlineSmall: const TextStyle(
      fontFamily: Tokens.fontDisplay,
      fontSize: Tokens.textHeadline,
      fontWeight: FontWeight.w800,
      height: 1.15,
    ),
    titleLarge: const TextStyle(
      fontFamily: Tokens.fontDisplay,
      fontSize: Tokens.textTitle,
      fontWeight: FontWeight.w800,
      height: 1.2,
    ),
    titleMedium: const TextStyle(
      fontSize: Tokens.textBody,
      fontWeight: FontWeight.w700,
    ),
    bodyLarge: body,
    bodyMedium: body,
    bodySmall: body,
    labelLarge: const TextStyle(
      fontSize: Tokens.textBody,
      fontWeight: FontWeight.w800,
    ),
    labelMedium: const TextStyle(
      fontSize: Tokens.textLabel,
      fontWeight: FontWeight.w600,
    ),
  ).apply(bodyColor: scheme.onSurface, displayColor: scheme.onSurface);
  const pill = StadiumBorder();
  const minimum = Size(Tokens.touch, Tokens.touch);
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    fontFamily: Tokens.fontText,
    textTheme: text,
    scaffoldBackgroundColor: dark ? Tokens.paperDark : Tokens.paper,
    materialTapTargetSize: MaterialTapTargetSize.padded,
    visualDensity: VisualDensity.standard,
    cardTheme: CardThemeData(
      color: dark ? Tokens.surfaceDark : Tokens.card,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Tokens.radiusLarge),
        side: BorderSide(color: dark ? const Color(0xFF3A342B) : Tokens.line),
      ),
      margin: EdgeInsets.zero,
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: dark ? Tokens.paperDark : Tokens.paper,
      foregroundColor: dark ? Tokens.inkDark : Tokens.ink,
      surfaceTintColor: Colors.transparent,
      titleTextStyle: TextStyle(
        fontFamily: Tokens.fontDisplay,
        fontSize: Tokens.textTitle,
        fontWeight: FontWeight.w800,
        color: dark ? Tokens.inkDark : Tokens.ink,
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: dark ? Tokens.paperDark : Tokens.card,
      indicatorColor: Tokens.accent,
      surfaceTintColor: Colors.transparent,
    ),
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: Tokens.accent,
      foregroundColor: Tokens.onAccent,
      shape: pill,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: minimum,
        shape: pill,
        textStyle: const TextStyle(
          fontFamily: Tokens.fontDisplay,
          fontSize: Tokens.textBody,
          fontWeight: FontWeight.w800,
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(minimumSize: minimum, shape: pill),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: dark ? Tokens.surfaceDark : Tokens.surface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(999),
        borderSide: BorderSide.none,
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(minimumSize: minimum),
    ),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(minimumSize: minimum),
    ),
    chipTheme: ChipThemeData(
      labelStyle: TextStyle(fontSize: Tokens.textBody, color: scheme.onSurface),
      secondaryLabelStyle: TextStyle(
        fontSize: Tokens.textBody,
        color: scheme.onSurface,
      ),
    ),
    listTileTheme: const ListTileThemeData(minTileHeight: Tokens.touch),
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
  );
}
