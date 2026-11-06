import 'package:flutter/material.dart';

import '../design/modes.dart';
import '../design/tokens.dart';
import '../format.dart';
import '../l10n/app_localizations.dart';
import '../routing/plan.dart';
import '../services.dart';
import '../widgets/sheets.dart';
import 'shell.dart';

/// Step by step (F-03, 10.2) : des phrases courtes avec une icône, comment reconnaître
/// le véhicule, combien prévoir, où descendre ; un bouton audio par étape, « Je pars ».
class ItineraryScreen extends StatelessWidget {
  const ItineraryScreen({super.key, required this.option, required this.to});

  final TripOption option;
  final String to;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final city = AppServices.of(context).city;
    final messenger = ScaffoldMessenger.of(context);
    void soon(String text) =>
        messenger.showSnackBar(SnackBar(content: Text(text)));

    final steps = <Widget>[];
    for (final leg in option.legs) {
      switch (leg) {
        case WalkLeg(:final metres, :final minutes, :final to, :final source):
          if (metres == 0) continue;
          steps.add(
            _Step(
              icon: ModeStyle.walk.icon,
              color: ModeStyle.walk.color,
              title: l10n.stepWalk(l10n.minutes(minutes), to.name),
              lines: [if (source == 'straight_line') l10n.stepWalkStraight],
              onListen: () => soon(l10n.audioSoon),
            ),
          );
        case RideLeg():
          final line = city.line(leg.line);
          final style = ModeStyle.of(line?.mode ?? 'autre');
          steps.add(
            _Step(
              icon: style.icon,
              color: style.color,
              title: l10n.stepRide(style.label(l10n), leg.lineName),
              lines: [
                if (line != null)
                  l10n.stepAppearance(
                    line.bodyColor,
                    line.colorPattern ?? line.longName,
                  ),
                if (line?.announcedAs case final words?)
                  l10n.stepAnnounced(words),
                l10n.waitShort(
                  minutesRange(l10n, leg.wait.p50Min, leg.wait.p80Min),
                ),
                if (leg.fare case final fare?)
                  l10n.stepFare(fareRange(l10n, fare), francs(l10n, fare.p50)),
                l10n.stepAlight(leg.alight.name, l10n.minutes(leg.rideMinutes)),
              ],
              onListen: () => soon(l10n.audioSoon),
              onWhy: () =>
                  showWhySheet(context, Explanation.forWait(l10n, leg.wait)),
            ),
          );
      }
    }
    steps.add(
      _Step(
        icon: Icons.flag,
        color: Tokens.brand,
        title: l10n.stepArrive(to),
        lines: [
          l10n.arriveBetween(
            clockText(l10n, option.arriveP50),
            clockText(l10n, option.arriveP80),
          ),
        ],
        onListen: () => soon(l10n.audioSoon),
      ),
    );

    return BannerScaffold(
      title: l10n.stepsTitle,
      body: ListView(
        padding: const EdgeInsets.all(Tokens.space4),
        children: [
          Text(
            minutesRange(l10n, option.duration.low, option.duration.high),
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          Text(
            option.fare == null
                ? l10n.fareUnknown
                : fareRange(l10n, option.fare!),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: Tokens.space4),
          ...steps,
        ],
      ),
      bottom: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(Tokens.space4),
          child: FilledButton.icon(
            style: FilledButton.styleFrom(
              minimumSize: const Size.fromHeight(56),
            ),
            onPressed: () => soon(l10n.startSoon),
            icon: const Icon(Icons.navigation),
            label: Text(l10n.start),
          ),
        ),
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({
    required this.icon,
    required this.color,
    required this.title,
    required this.lines,
    required this.onListen,
    this.onWhy,
  });

  final IconData icon;
  final Color color;
  final String title;
  final List<String> lines;
  final VoidCallback onListen;
  final VoidCallback? onWhy;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: Tokens.space4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            backgroundColor: color,
            child: Icon(icon, color: Colors.white),
          ),
          const SizedBox(width: Tokens.space3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                for (final line in lines) Text(line),
                if (onWhy != null)
                  TextButton.icon(
                    onPressed: onWhy,
                    icon: const Icon(Icons.info_outline),
                    label: Text(l10n.whyEstimateFull),
                  ),
              ],
            ),
          ),
          IconButton(
            tooltip: l10n.listenStep,
            onPressed: onListen,
            icon: const Icon(Icons.volume_up_outlined),
          ),
        ],
      ),
    );
  }
}
