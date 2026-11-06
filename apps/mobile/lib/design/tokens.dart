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

  static const double radius = 12;
  static const double radiusLarge = 20;

  /// Smallest touch target (10.3).
  static const double touch = 48;

  /// Type scale, sp. Body text is never under 16 sp (10.3).
  static const double textBody = 16;
  static const double textLabel = 14;
  static const double textTitle = 20;
  static const double textHeadline = 24;
  static const double textDisplay = 28;

  // Colours: high contrast, readable in full sun (10.3).
  static const Color ink = Color(0xFF16181D);
  static const Color inkMuted = Color(0xFF4A4F5A);
  static const Color paper = Color(0xFFFFFFFF);
  static const Color surface = Color(0xFFF3F5F7);
  static const Color brand = Color(0xFF0A5C5A);
  static const Color onBrand = Color(0xFFFFFFFF);
  static const Color accent = Color(0xFFFFC233);
  static const Color onAccent = Color(0xFF16181D);
  static const Color fictional = Color(0xFFA4001D);
  static const Color onFictional = Color(0xFFFFFFFF);

  // Dark mode, to save battery (10.3).
  static const Color inkDark = Color(0xFFF1F3F5);
  static const Color paperDark = Color(0xFF101214);
  static const Color surfaceDark = Color(0xFF1D2125);
  static const Color brandDark = Color(0xFF6FD3CF);
}

/// State of a queue (F-05) : couleur, icône et mot — jamais la couleur seule.
enum QueueLevel {
  peu(Color(0xFF1E7B34), Icons.sentiment_satisfied_alt),
  moyen(Color(0xFFB25E00), Icons.sentiment_neutral),
  beaucoup(Color(0xFFB3261E), Icons.sentiment_dissatisfied),
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
    onPrimary: dark ? Tokens.paperDark : Tokens.onBrand,
    secondary: Tokens.accent,
    onSecondary: Tokens.onAccent,
    surface: dark ? Tokens.paperDark : Tokens.paper,
    onSurface: dark ? Tokens.inkDark : Tokens.ink,
    error: Tokens.fictional,
  );
  const body = TextStyle(fontSize: Tokens.textBody, height: 1.35);
  final text = TextTheme(
    displaySmall: const TextStyle(
      fontSize: Tokens.textDisplay,
      fontWeight: FontWeight.w700,
    ),
    headlineSmall: const TextStyle(
      fontSize: Tokens.textHeadline,
      fontWeight: FontWeight.w700,
    ),
    titleLarge: const TextStyle(
      fontSize: Tokens.textTitle,
      fontWeight: FontWeight.w700,
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
      fontWeight: FontWeight.w600,
    ),
    labelMedium: const TextStyle(fontSize: Tokens.textLabel),
  ).apply(bodyColor: scheme.onSurface, displayColor: scheme.onSurface);
  final shape = RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(Tokens.radius),
  );
  const minimum = Size(Tokens.touch, Tokens.touch);
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    textTheme: text,
    scaffoldBackgroundColor: dark ? Tokens.paperDark : Tokens.paper,
    materialTapTargetSize: MaterialTapTargetSize.padded,
    visualDensity: VisualDensity.standard,
    cardTheme: CardThemeData(
      color: dark ? Tokens.surfaceDark : Tokens.surface,
      elevation: 0,
      shape: shape,
      margin: EdgeInsets.zero,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(minimumSize: minimum, shape: shape),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(minimumSize: minimum, shape: shape),
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
