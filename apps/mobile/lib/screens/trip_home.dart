import 'package:flutter/material.dart';

import '../data/city.dart';
import '../data/store.dart';
import '../design/modes.dart';
import '../design/tokens.dart';
import '../format.dart';
import '../l10n/app_localizations.dart';
import '../services.dart';
import '../widgets/common.dart';
import 'results.dart';
import 'search.dart';
import 'station.dart';

/// Home of the Trajet tab (10.2) : « Tu vas où ? », raccourcis, trajets récents et gares
/// autour de moi.
class TripHome extends StatefulWidget {
  const TripHome({super.key});

  @override
  State<TripHome> createState() => _TripHomeState();
}

class _TripHomeState extends State<TripHome> {
  Future<void> _search() async {
    final services = AppServices.of(context);
    final destination = await Navigator.of(context).push<Destination>(
      MaterialPageRoute(builder: (_) => const SearchScreen()),
    );
    if (destination == null || !mounted) return;
    _go(
      Destination(
        AppLocalizations.of(context).myPosition,
        services.city.position,
      ),
      destination,
    );
  }

  void _go(Destination from, Destination to) {
    final services = AppServices.of(context);
    services.store.addRecent(RecentTrip(to.name, to.point, services.now()));
    services.storeChanges.value++;
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => ResultsScreen(from: from, to: to),
      ),
    );
  }

  void _soon(String message) =>
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(message)));

  @override
  Widget build(BuildContext context) => ValueListenableBuilder<int>(
    valueListenable: AppServices.of(context).storeChanges,
    builder: (context, _, _) => _content(context),
  );

  Widget _content(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final services = AppServices.of(context);
    final theme = Theme.of(context);
    final recent = services.store.recentTrips();
    final nearby = services.city.nearestStations(services.city.position);
    final now = services.now();
    final seconds = now.hour * 3600 + now.minute * 60;
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        Tokens.space4,
        Tokens.space4,
        Tokens.space4,
        96,
      ),
      children: [
        Semantics(
          button: true,
          label: l10n.whereTo,
          excludeSemantics: true,
          child: Material(
            color: theme.colorScheme.primary,
            borderRadius: BorderRadius.circular(Tokens.radiusLarge),
            child: InkWell(
              borderRadius: BorderRadius.circular(Tokens.radiusLarge),
              onTap: _search,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: Tokens.space4,
                  vertical: Tokens.space3,
                ),
                child: Row(
                  children: [
                    Icon(Icons.search, color: theme.colorScheme.onPrimary),
                    const SizedBox(width: Tokens.space3),
                    Expanded(
                      child: Text(
                        l10n.whereTo,
                        style: theme.textTheme.headlineSmall?.copyWith(
                          color: theme.colorScheme.onPrimary,
                        ),
                      ),
                    ),
                    IconButton(
                      tooltip: l10n.dictate,
                      color: theme.colorScheme.onPrimary,
                      onPressed: () => _soon(l10n.voiceSoon),
                      icon: const Icon(Icons.mic),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: Tokens.space3),
        Wrap(
          spacing: Tokens.space2,
          runSpacing: Tokens.space2,
          children: [
            for (final (text, icon) in [
              (l10n.shortcutHome, Icons.home_outlined),
              (l10n.shortcutWork, Icons.work_outline),
              (l10n.shortcutSchool, Icons.school_outlined),
            ])
              ActionChip(
                avatar: Icon(icon),
                label: Text(text),
                onPressed: () => _soon(l10n.shortcutNotSaved),
              ),
          ],
        ),
        if (recent.isNotEmpty) ...[
          SectionTitle(l10n.recentTrips),
          for (final trip in recent)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.history),
              title: Text(trip.name),
              onTap: () => _go(
                Destination(l10n.myPosition, services.city.position),
                Destination(trip.name, trip.point),
              ),
            ),
        ],
        SectionTitle(l10n.aroundMe),
        for (final stop in nearby)
          Padding(
            padding: const EdgeInsets.only(bottom: Tokens.space2),
            child: _NearbyStation(
              stop: stop,
              secondsOfDay: seconds,
              day: dayType(now),
            ),
          ),
      ],
    );
  }
}

class _NearbyStation extends StatelessWidget {
  const _NearbyStation({
    required this.stop,
    required this.secondsOfDay,
    required this.day,
  });

  final Stop stop;
  final int secondsOfDay;
  final String day;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final services = AppServices.of(context);
    final metres = stop.point.distanceTo(services.city.position).round();
    final usual = [
      for (final series in services.city.waitsAt(stop.code, day))
        ?series.at(secondsOfDay),
    ];
    usual.sort((a, b) => a.$2.compareTo(b.$2));
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute<void>(builder: (_) => StationScreen(stop: stop)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(Tokens.space3),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(stop.name, style: Theme.of(context).textTheme.titleMedium),
              Text('$metres m'),
              const SizedBox(height: Tokens.space2),
              Wrap(
                spacing: Tokens.space1,
                runSpacing: Tokens.space1,
                children: [
                  for (final code in stop.lines)
                    if (services.city.line(code) case final line?)
                      ModeChip(ModeStyle.of(line.mode), line: line.shortName),
                ],
              ),
              if (usual.isNotEmpty) ...[
                const SizedBox(height: Tokens.space2),
                Text(
                  l10n.stationUsually(
                    minutesRange(
                      l10n,
                      (usual.first.$2 / 60).round(),
                      (usual.first.$3 / 60).round(),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
