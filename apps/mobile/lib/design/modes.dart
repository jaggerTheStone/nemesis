import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';

/// Icon, colour and name of each mode (F-05, 10.3): never the colour alone. The codes
/// are those of the icon recognition test (docs/UX/PROTOCOLE-TESTS-MAQUETTES.md).
class ModeStyle {
  const ModeStyle(this.code, this.icon, this.color);

  /// Icon code of the recognition test, e.g. `mode_gbaka`.
  final String code;
  final IconData icon;
  final Color color;

  String label(AppLocalizations l10n) => switch (code) {
    'mode_gbaka' => l10n.modeGbaka,
    'mode_woro_communal' => l10n.modeWoroCommunal,
    'mode_woro_intercommunal' => l10n.modeWoroIntercommunal,
    'mode_bus_sotra' => l10n.modeBus,
    'mode_bus_express' => l10n.modeBusExpress,
    'mode_bateau_bus' => l10n.modeBoat,
    'mode_marche' => l10n.modeWalk,
    _ => l10n.modeOther,
  };

  static const walk = ModeStyle(
    'mode_marche',
    Icons.directions_walk,
    Color(0xFF4A4F5A),
  );

  static const _byMode = {
    'gbaka': ModeStyle('mode_gbaka', Icons.airport_shuttle, Color(0xFF13855A)),
    'woro_communal': ModeStyle(
      'mode_woro_communal',
      Icons.local_taxi,
      Color(0xFFBF5A00),
    ),
    'woro_intercommunal': ModeStyle(
      'mode_woro_intercommunal',
      Icons.hail,
      Color(0xFF8A4A00),
    ),
    'bus_sotra': ModeStyle(
      'mode_bus_sotra',
      Icons.directions_bus,
      Color(0xFF2B59C3),
    ),
    'bus_express': ModeStyle(
      'mode_bus_express',
      Icons.directions_bus_filled,
      Color(0xFF8E2C00),
    ),
    'bateau_bus': ModeStyle(
      'mode_bateau_bus',
      Icons.directions_boat,
      Color(0xFF077B99),
    ),
  };

  static ModeStyle of(String mode) =>
      _byMode[mode] ??
      const ModeStyle('mode_autre', Icons.commute, Color(0xFF4A4F5A));
}
