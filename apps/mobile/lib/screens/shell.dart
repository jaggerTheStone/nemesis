import 'package:flutter/material.dart';

import '../design/tokens.dart';
import '../l10n/app_localizations.dart';
import '../services.dart';
import '../widgets/common.dart';
import '../widgets/sheets.dart';
import 'map_tab.dart';
import 'me_tab.dart';
import 'trip_home.dart';

/// Three tabs at most, Trajet, Carte, Moi, and the Signaler button always visible (10.2).
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final services = AppServices.of(context);
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            if (services.showFictionalBanner) const FictionalBanner(),
            Expanded(
              child: IndexedStack(
                index: _tab,
                children: const [TripHome(), MapTab(), MeTab()],
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        heroTag: 'report',
        onPressed: () => showReportSheet(context),
        icon: const Icon(Icons.campaign),
        label: Text(l10n.reportButton),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (index) => setState(() => _tab = index),
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.directions_outlined),
            selectedIcon: const Icon(Icons.directions),
            label: l10n.tabTrip,
          ),
          NavigationDestination(
            icon: const Icon(Icons.map_outlined),
            selectedIcon: const Icon(Icons.map),
            label: l10n.tabMap,
          ),
          NavigationDestination(
            icon: const Icon(Icons.person_outline),
            selectedIcon: const Icon(Icons.person),
            label: l10n.tabMe,
          ),
        ],
      ),
    );
  }
}

/// A pushed screen with the fictional banner on top.
class BannerScaffold extends StatelessWidget {
  const BannerScaffold({
    super.key,
    required this.title,
    required this.body,
    this.bottom,
  });

  final String title;
  final Widget body;
  final Widget? bottom;

  @override
  Widget build(BuildContext context) {
    final services = AppServices.of(context);
    // Heights follow the size of the text, up to 200 % (10.6).
    final scaler = MediaQuery.textScalerOf(context);
    return Scaffold(
      appBar: AppBar(
        toolbarHeight: scaler.scale(kToolbarHeight),
        title: Text(title, maxLines: 2, overflow: TextOverflow.ellipsis),
        bottom: services.showFictionalBanner
            ? PreferredSize(
                preferredSize: Size.fromHeight(
                  scaler.scale(Tokens.textLabel) * 1.4 + Tokens.space2,
                ),
                child: const FictionalBanner(),
              )
            : null,
      ),
      body: SafeArea(child: body),
      bottomNavigationBar: bottom,
    );
  }
}
