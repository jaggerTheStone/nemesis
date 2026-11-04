import 'package:flutter/material.dart';

import 'l10n/app_localizations.dart';

void main() {
  runApp(const NemesisApp());
}

/// Root widget. Screens arrive with the clickable prototype (increment I0.11).
class NemesisApp extends StatelessWidget {
  const NemesisApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      onGenerateTitle: (context) => AppLocalizations.of(context).appName,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.appName)),
      body: Center(child: Text(l10n.homePlaceholder)),
    );
  }
}
