import 'package:flutter/material.dart';

import '../data/city.dart';
import '../design/modes.dart';
import '../design/tokens.dart';
import '../format.dart';
import '../l10n/app_localizations.dart';
import '../routing/plan.dart';
import '../services.dart';
import '../widgets/common.dart';
import '../widgets/sheets.dart';
import 'shell.dart';

/// Station sheet (F-06) : lignes, état actuel avec sa fraîcheur (ici l'estimation
/// historique, faute de signalement), meilleure heure pour partir, prix par destination.
class StationScreen extends StatelessWidget {
  const StationScreen({super.key, required this.stop});

  final Stop stop;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final services = AppServices.of(context);
    final city = services.city;
    final theme = Theme.of(context);
    final now = services.now();
    final seconds = now.hour * 3600 + now.minute * 60;
    final day = dayType(now);
    final lines = [for (final code in stop.lines) ?city.line(code)];
    final waits = city.waitsAt(stop.code, day);
    final week = city.waitsAt(stop.code, 'ouvrable');

    return BannerScaffold(
      title: stop.name,
      body: ListView(
        padding: const EdgeInsets.fromLTRB(
          Tokens.space4,
          Tokens.space4,
          Tokens.space4,
          Tokens.space6,
        ),
        children: [
          Fact(
            Icons.schedule,
            l10n.stationHours(
              clockText(l10n, stop.hours.$1),
              clockText(l10n, stop.hours.$2),
            ),
          ),
          Fact(
            Icons.light_mode_outlined,
            l10n.stationLighting(switch (stop.lighting) {
              'oui' => l10n.yes,
              'non' => l10n.no,
              _ => l10n.unknown,
            }),
          ),
          SectionTitle(l10n.stationLines),
          for (final line in lines)
            Padding(
              padding: const EdgeInsets.only(bottom: Tokens.space2),
              child: Row(
                children: [
                  ModeChip(ModeStyle.of(line.mode), line: line.shortName),
                  const SizedBox(width: Tokens.space2),
                  Expanded(child: Text(line.longName)),
                ],
              ),
            ),
          SectionTitle(l10n.stationNow),
          Fact(Icons.history, l10n.stationNoReport),
          for (final series in waits)
            if (series.at(seconds) case final slot?)
              Padding(
                padding: const EdgeInsets.only(top: Tokens.space2),
                child: Row(
                  children: [
                    if (city.line(series.line) case final line?)
                      ModeChip(ModeStyle.of(line.mode), line: line.shortName),
                    const SizedBox(width: Tokens.space2),
                    Expanded(
                      child: Text(
                        l10n.stationUsually(
                          minutesRange(
                            l10n,
                            (slot.$2 / 60).round(),
                            (slot.$3 / 60).round(),
                          ),
                        ),
                      ),
                    ),
                    IconButton(
                      tooltip: l10n.whyEstimateFull,
                      icon: const Icon(Icons.info_outline),
                      onPressed: () => showWhySheet(
                        context,
                        Explanation(
                          from: [l10n.whyWaitProfile],
                          details: [
                            series.regime == 'A'
                                ? l10n.whyRegimeA
                                : l10n.whyRegimeB,
                          ],
                          confidence: slot.$4 >= 50
                              ? Confidence.elevee
                              : slot.$4 >= 20
                              ? Confidence.moyenne
                              : Confidence.faible,
                          contributors: slot.$4,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
          if (week.isNotEmpty) ...[
            SectionTitle(l10n.stationBestHour),
            Text(
              l10n.stationBestHourHint(
                city.line(week.first.line)?.shortName ?? week.first.line,
              ),
              style: theme.textTheme.labelMedium,
            ),
            const SizedBox(height: Tokens.space2),
            _BestHour(series: week.first),
          ],
          SectionTitle(l10n.stationFares),
          for (final line in lines)
            if (city.fareTo(line, stop, 'normale') case final fare?)
              Fact(
                Icons.payments_outlined,
                '${l10n.stationFareTo(line.shortName, city.stop(line.terminals.last)?.name ?? '')} : '
                '${fareRange(l10n, Fare(fare.p10, fare.p50, fare.p90))}',
              ),
          const SizedBox(height: Tokens.space4),
          FilledButton.icon(
            onPressed: () => showReportSheet(context, at: stop),
            icon: const Icon(Icons.campaign),
            label: Text(l10n.stationReport),
          ),
        ],
      ),
    );
  }
}

/// Usual wait hour by hour: one bar per hour, the value written beside it.
class _BestHour extends StatelessWidget {
  const _BestHour({required this.series});

  final WaitSeries series;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final hours = <(int, int)>[];
    for (var hour = 5; hour < 22; hour++) {
      final slot = series.at(hour * 3600);
      if (slot != null) hours.add((hour, (slot.$2 / 60).round()));
    }
    if (hours.isEmpty) return const SizedBox.shrink();
    final longest = hours.map((h) => h.$2).reduce((a, b) => a > b ? a : b);
    final color = Theme.of(context).colorScheme.primary;
    return Column(
      children: [
        for (final (hour, minutes) in hours)
          Semantics(
            label: l10n.stationBestHourValue(
              l10n.clockHour(hour),
              l10n.minutes(minutes),
            ),
            excludeSemantics: true,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                children: [
                  SizedBox(width: 64, child: Text(l10n.clockHour(hour))),
                  Expanded(
                    child: FractionallySizedBox(
                      alignment: Alignment.centerLeft,
                      widthFactor: longest == 0 ? 0 : minutes / longest,
                      child: Container(height: 12, color: color),
                    ),
                  ),
                  const SizedBox(width: Tokens.space2),
                  Text(l10n.minutes(minutes)),
                ],
              ),
            ),
          ),
      ],
    );
  }
}
