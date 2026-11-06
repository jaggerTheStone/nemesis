import 'package:flutter/material.dart';

import '../data/city.dart';
import '../data/store.dart';
import '../design/tokens.dart';
import '../format.dart';
import '../l10n/app_localizations.dart';
import '../routing/plan.dart';
import '../services.dart';
import 'common.dart';

/// What an estimate is made of, for « Pourquoi cette estimation ? » (10.2) : d'où vient
/// le chiffre, quand, combien de personnes l'ont confirmé.
class Explanation {
  const Explanation({
    required this.from,
    required this.confidence,
    this.details = const [],
    this.contributors,
  });

  /// An option: its first wait, its duration and its fare.
  factory Explanation.forOption(AppLocalizations l10n, TripOption option) {
    final wait = option.firstWait;
    return Explanation(
      from: [
        if (wait != null) waitSource(l10n, wait),
        l10n.whyDuration,
        if (option.fare != null) l10n.whyFare,
      ],
      details: [
        if (wait != null)
          wait.regime == 'A' ? l10n.whyRegimeA : l10n.whyRegimeB,
      ],
      confidence: wait?.source == 'profile'
          ? Confidence.moyenne
          : Confidence.faible,
    );
  }

  factory Explanation.forWait(AppLocalizations l10n, Wait wait) => Explanation(
    from: [waitSource(l10n, wait)],
    details: [wait.regime == 'A' ? l10n.whyRegimeA : l10n.whyRegimeB],
    confidence: wait.source == 'profile'
        ? Confidence.moyenne
        : Confidence.faible,
  );

  static String waitSource(AppLocalizations l10n, Wait wait) =>
      wait.source == 'profile' ? l10n.whyWaitProfile : l10n.whyWaitHeadway;

  final List<String> from;
  final List<String> details;
  final Confidence confidence;

  /// People who confirmed, when known (EstimateMeta.contributors).
  final int? contributors;
}

Future<void> showWhySheet(BuildContext context, Explanation explanation) {
  final services = AppServices.of(context);
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) {
      final l10n = AppLocalizations.of(context);
      final theme = Theme.of(context);
      return SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            Tokens.space4,
            0,
            Tokens.space4,
            Tokens.space5,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Semantics(
                header: true,
                child: Text(l10n.whyTitle, style: theme.textTheme.titleLarge),
              ),
              SectionTitle(l10n.whyFrom),
              for (final line in [...explanation.from, ...explanation.details])
                Padding(
                  padding: const EdgeInsets.only(bottom: Tokens.space2),
                  child: Text(line),
                ),
              SectionTitle(l10n.whyWhen),
              Text(l10n.whyNetwork(services.city.networkVersion)),
              SectionTitle(l10n.whyConfirmed),
              Text(
                explanation.contributors == null
                    ? l10n.whyNobody
                    : l10n.whyContributors(explanation.contributors!),
              ),
              const SizedBox(height: Tokens.space3),
              ConfidenceBadge(explanation.confidence),
            ],
          ),
        ),
      );
    },
  );
}

String queueText(AppLocalizations l10n, QueueLevel level) => switch (level) {
  QueueLevel.peu => l10n.queuePeu,
  QueueLevel.moyen => l10n.queueMoyen,
  QueueLevel.beaucoup => l10n.queueBeaucoup,
  QueueLevel.tresLong => l10n.queueTresLong,
  QueueLevel.inconnu => l10n.queueInconnu,
};

/// The report sheet (F-07) : la première pression ouvre la feuille, la seconde envoie.
/// The report goes to the local queue, in the format of the API.
Future<void> showReportSheet(BuildContext context, {Stop? at}) {
  final services = AppServices.of(context);
  final stop =
      at ?? services.city.nearestStations(services.city.position).first;
  final messenger = ScaffoldMessenger.of(context);
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (sheetContext) {
      final l10n = AppLocalizations.of(sheetContext);
      final theme = Theme.of(sheetContext);
      final line = stop.lines.isEmpty
          ? null
          : services.city.line(stop.lines.first);
      final fare = line == null
          ? null
          : services.city.fareTo(line, stop, 'normale');

      void send(String kind, Map<String, dynamic> payload) {
        services.store.addContribution(
          Contribution(
            id: newUuid(),
            kind: kind,
            observedAt: services.now(),
            city: services.city.code,
            stopId: stop.id,
            routeId: kind == 'prix_paye' || kind == 'vehicule_plein'
                ? line?.id
                : null,
            location: services.city.position,
            accuracyM: 25,
            payload: payload,
          ),
        );
        services.storeChanges.value++;
        Navigator.of(sheetContext).pop();
        messenger.showSnackBar(SnackBar(content: Text(l10n.reportThanks)));
      }

      Widget big(
        String text,
        IconData icon,
        VoidCallback onPressed, {
        Color? color,
      }) => SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          style: FilledButton.styleFrom(
            backgroundColor: color,
            minimumSize: const Size.fromHeight(56),
            alignment: Alignment.centerLeft,
          ),
          onPressed: onPressed,
          icon: Icon(icon),
          label: Text(text),
        ),
      );

      return SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            Tokens.space4,
            0,
            Tokens.space4,
            Tokens.space5,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Semantics(
                header: true,
                child: Text(
                  l10n.reportTitle,
                  style: theme.textTheme.titleLarge,
                ),
              ),
              Text(l10n.reportAt(stop.name)),
              SectionTitle(l10n.reportQueue),
              for (final level in QueueLevel.values)
                if (level != QueueLevel.inconnu)
                  Padding(
                    padding: const EdgeInsets.only(bottom: Tokens.space2),
                    child: big(
                      queueText(l10n, level),
                      level.icon,
                      () => send('file', {'level': level.apiValue}),
                      color: level.color,
                    ),
                  ),
              SectionTitle(l10n.reportVehicles),
              Wrap(
                spacing: Tokens.space2,
                runSpacing: Tokens.space2,
                children: [
                  for (final (text, value) in [
                    (l10n.vehiclesNone, 'aucun'),
                    (l10n.vehiclesFew, '1_2'),
                    (l10n.vehiclesMany, '3_plus'),
                  ])
                    OutlinedButton(
                      onPressed: () =>
                          send('vehicules_presents', {'vehicles': value}),
                      child: Text(text),
                    ),
                ],
              ),
              const SizedBox(height: Tokens.space4),
              big(
                l10n.reportFull,
                Icons.groups,
                () => send('vehicule_plein', const {}),
              ),
              if (fare != null) ...[
                SectionTitle(l10n.reportPaid),
                Wrap(
                  spacing: Tokens.space2,
                  runSpacing: Tokens.space2,
                  children: [
                    for (final amount in {fare.p10, fare.p50, fare.p90})
                      OutlinedButton(
                        onPressed: () =>
                            send('prix_paye', {'amount_xof': amount}),
                        child: Text(francs(l10n, amount)),
                      ),
                  ],
                ),
              ],
            ],
          ),
        ),
      );
    },
  );
}
