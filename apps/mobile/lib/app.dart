import 'package:flutter/material.dart';

import 'design/tokens.dart';
import 'l10n/app_localizations.dart';
import 'screens/shell.dart';
import 'services.dart';

/// The application once its data is loaded. [services] carries the city, the engine,
/// the store and the map; tests give their own.
class NemesisApp extends StatelessWidget {
  const NemesisApp({super.key, required this.services});

  final AppServices Function(Widget child) services;

  @override
  Widget build(BuildContext context) {
    return services(
      MaterialApp(
        // Our own banner says « DONNÉES FICTIVES »; Flutter's « DEBUG » would compete.
        debugShowCheckedModeBanner: false,
        onGenerateTitle: (context) => AppLocalizations.of(context).appName,
        locale: const Locale('fr', 'CI'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        theme: buildTheme(Brightness.light),
        darkTheme: buildTheme(Brightness.dark),
        home: const HomeShell(),
      ),
    );
  }
}
