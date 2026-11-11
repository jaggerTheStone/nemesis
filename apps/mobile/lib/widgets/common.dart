import 'package:flutter/material.dart';

import '../design/modes.dart';
import '../design/tokens.dart';
import '../format.dart';
import '../l10n/app_localizations.dart';
import '../routing/plan.dart';
import '../services.dart';

/// « DONNÉES FICTIVES », always on screen with the fictional city (règle 1) ; with
/// the real lines of 2023, « LIGNES DE 2023 · À CONFIRMER » (H-030).
class FictionalBanner extends StatelessWidget {
  const FictionalBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final fictional = AppServices.of(context).city.isFictional;
    final text = fictional ? l10n.fictionalBanner : l10n.evaluationBanner;
    final hint = fictional
        ? l10n.fictionalBannerHint
        : l10n.evaluationBannerHint;
    return Semantics(
      container: true,
      label: '$text. $hint',
      excludeSemantics: true,
      child: Container(
        width: double.infinity,
        color: fictional ? Tokens.fictional : Tokens.ink,
        padding: const EdgeInsets.symmetric(
          horizontal: Tokens.space4,
          vertical: Tokens.space1,
        ),
        child: Text(
          text,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: fictional ? Tokens.onFictional : Tokens.accent,
            fontSize: Tokens.textLabel,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.2,
          ),
        ),
      ),
    );
  }
}

/// Icon and name of a mode, in its colour: never the colour alone (10.3).
class ModeChip extends StatelessWidget {
  const ModeChip(this.style, {super.key, this.line});

  final ModeStyle style;
  final String? line;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final line = (this.line?.isEmpty ?? true) ? null : this.line;
    final name = line == null
        ? style.label(l10n)
        : '${style.label(l10n)} $line';
    return Semantics(
      label: name,
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: Tokens.space2,
          vertical: Tokens.space1,
        ),
        decoration: BoxDecoration(
          color: style.color,
          borderRadius: BorderRadius.circular(Tokens.radius),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(style.icon, color: Colors.white, size: 20),
            if (line != null) ...[
              const SizedBox(width: Tokens.space1),
              // Real line names are long (« Yopougon Lavage ↔ Plateau Super U ») :
              // they end in an ellipsis rather than leave the screen.
              Flexible(
                child: Text(
                  line,
                  maxLines: 1,
                  softWrap: false,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: Tokens.textBody,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

String labelText(AppLocalizations l10n, String label) => switch (label) {
  'cheapest' => l10n.labelCheapest,
  'fastest' => l10n.labelFastest,
  'simplest' => l10n.labelSimplest,
  _ => l10n.otherOption,
};

/// The label of an option: « Le moins cher », « Le plus rapide », « Le plus simple ».
class LabelBadge extends StatelessWidget {
  const LabelBadge(this.label, {super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final icon = switch (label) {
      'cheapest' => Icons.savings_outlined,
      'fastest' => Icons.bolt,
      'simplest' => Icons.thumb_up_alt_outlined,
      _ => Icons.alt_route,
    };
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: Tokens.space2,
        vertical: Tokens.space1,
      ),
      decoration: BoxDecoration(
        color: Tokens.accent,
        borderRadius: BorderRadius.circular(Tokens.radius),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: Tokens.onAccent),
          const SizedBox(width: Tokens.space1),
          Flexible(
            child: Text(
              labelText(l10n, label),
              style: const TextStyle(
                color: Tokens.onAccent,
                fontSize: Tokens.textBody,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

String confidenceText(AppLocalizations l10n, Confidence c) => switch (c) {
  Confidence.elevee => l10n.confidenceHigh,
  Confidence.moyenne => l10n.confidenceMedium,
  Confidence.faible => l10n.confidenceLow,
  Confidence.inconnue => l10n.confidenceUnknown,
};

/// Confidence badge: full, half or empty circle, and the word (DATA.md).
class ConfidenceBadge extends StatelessWidget {
  const ConfidenceBadge(this.confidence, {super.key});

  final Confidence confidence;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(confidence.icon, size: 18),
        const SizedBox(width: Tokens.space1),
        Flexible(
          child: Text(l10n.confidence(confidenceText(l10n, confidence))),
        ),
      ],
    );
  }
}

/// One line with an icon: the facts of an option (wait, transfers, walk, fare).
class Fact extends StatelessWidget {
  const Fact(this.icon, this.text, {super.key, this.strong = false});

  final IconData icon;
  final String text;
  final bool strong;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 20),
        const SizedBox(width: Tokens.space2),
        Expanded(
          child: Text(
            text,
            style: strong
                ? Theme.of(context).textTheme.titleMedium
                : Theme.of(context).textTheme.bodyMedium,
          ),
        ),
      ],
    );
  }
}

/// One option of the results (10.2) : étiquettes, modes dans l'ordre, durée et prix en
/// fourchette, attente, changements, marche, fraîcheur.
class OptionCard extends StatelessWidget {
  const OptionCard({
    super.key,
    required this.option,
    required this.modeOf,
    required this.onOpen,
    required this.onWhy,
  });

  final TripOption option;
  final ModeStyle Function(String line) modeOf;
  final VoidCallback onOpen;
  final VoidCallback onWhy;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final wait = option.firstWait;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onOpen,
        child: Padding(
          padding: const EdgeInsets.all(Tokens.space4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: Tokens.space2,
                runSpacing: Tokens.space2,
                children: [
                  for (final label in option.labels) LabelBadge(label),
                  if (option.labels.isEmpty) LabelBadge(''),
                ],
              ),
              const SizedBox(height: Tokens.space3),
              Wrap(
                spacing: Tokens.space1,
                runSpacing: Tokens.space1,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  for (final (index, ride) in option.rides.indexed) ...[
                    if (index > 0) const Icon(Icons.chevron_right, size: 20),
                    ModeChip(modeOf(ride.line), line: ride.lineName),
                  ],
                ],
              ),
              const SizedBox(height: Tokens.space3),
              Text(
                minutesRange(l10n, option.duration.low, option.duration.high),
                style: theme.textTheme.headlineSmall,
              ),
              Text(
                l10n.arriveBetween(
                  clockText(l10n, option.arriveP50),
                  clockText(l10n, option.arriveP80),
                ),
              ),
              const SizedBox(height: Tokens.space2),
              Fact(
                Icons.payments_outlined,
                option.fare == null
                    ? l10n.fareUnknown
                    : fareRange(l10n, option.fare!),
                strong: true,
              ),
              if (wait != null)
                Fact(
                  Icons.hourglass_bottom,
                  l10n.waitShort(minutesRange(l10n, wait.p50Min, wait.p80Min)),
                ),
              Fact(Icons.swap_horiz, l10n.transfers(option.transfers)),
              Fact(Icons.directions_walk, l10n.walkMinutes(option.walkMinutes)),
              const SizedBox(height: Tokens.space2),
              // Wraps when the text is enlarged (10.6).
              Wrap(
                alignment: WrapAlignment.spaceBetween,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Text(l10n.dataFreshness, style: theme.textTheme.labelMedium),
                  TextButton.icon(
                    onPressed: onWhy,
                    icon: const Icon(Icons.info_outline),
                    label: Text(l10n.whyEstimate),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Title of a section of a screen.
class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: Tokens.space5, bottom: Tokens.space2),
    child: Semantics(
      header: true,
      child: Text(text, style: Theme.of(context).textTheme.titleLarge),
    ),
  );
}
