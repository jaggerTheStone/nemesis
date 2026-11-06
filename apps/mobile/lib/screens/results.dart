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
import 'itinerary.dart';
import 'shell.dart';

/// The options of a trip (10.2) : une carte par option, la liste d'abord. Computed
/// offline by the engine embedded in the phone.
class ResultsScreen extends StatefulWidget {
  const ResultsScreen({super.key, required this.from, required this.to});

  final Destination from;
  final Destination to;

  @override
  State<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends State<ResultsScreen> {
  /// null: leave now; otherwise the time of day chosen, in minutes.
  int? _leaveAt;
  Future<PlanResult>? _plan;

  static const _choices = [7 * 60 + 30, 12 * 60, 18 * 60];

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _plan ??= _compute();
  }

  DateTime _departure() {
    final now = AppServices.of(context).now();
    final at = _leaveAt;
    if (at == null) return now;
    var day = DateTime(now.year, now.month, now.day, at ~/ 60, at % 60);
    if (day.isBefore(now)) day = day.add(const Duration(days: 1));
    return day;
  }

  Future<PlanResult> _compute() =>
      AppServices.of(context).routing
          .plan(PlanQuery(widget.from.point, widget.to.point, _departure()));

  void _choose(int? minutes) => setState(() {
    _leaveAt = minutes;
    _plan = _compute();
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final city = AppServices.of(context).city;
    ModeStyle modeOf(String code) =>
        ModeStyle.of(city.line(code)?.mode ?? 'autre');
    return BannerScaffold(
      title: widget.to.name,
      body: ListView(
        padding: const EdgeInsets.all(Tokens.space4),
        children: [
          Fact(Icons.trip_origin, '${l10n.fromLabel} : ${widget.from.name}'),
          Fact(Icons.place, '${l10n.toLabel} : ${widget.to.name}'),
          const SizedBox(height: Tokens.space3),
          Wrap(
            spacing: Tokens.space2,
            runSpacing: Tokens.space2,
            children: [
              ChoiceChip(
                label: Text(l10n.leaveNow),
                selected: _leaveAt == null,
                onSelected: (_) => _choose(null),
              ),
              for (final minutes in _choices)
                ChoiceChip(
                  label: Text(
                    l10n.leaveAt(
                      clockText(
                        l10n,
                        '${(minutes ~/ 60).toString().padLeft(2, '0')}:'
                        '${(minutes % 60).toString().padLeft(2, '0')}',
                      ),
                    ),
                  ),
                  selected: _leaveAt == minutes,
                  onSelected: (_) => _choose(minutes),
                ),
            ],
          ),
          const SizedBox(height: Tokens.space4),
          FutureBuilder<PlanResult>(
            future: _plan,
            builder: (context, snapshot) {
              if (snapshot.hasError) {
                return Text(l10n.routingError('${snapshot.error}'));
              }
              final result = snapshot.data;
              if (result == null) {
                return Row(
                  children: [
                    const SizedBox.square(
                      dimension: 24,
                      child: CircularProgressIndicator(strokeWidth: 3),
                    ),
                    const SizedBox(width: Tokens.space3),
                    Text(l10n.computing),
                  ],
                );
              }
              if (result.options.isEmpty) {
                return Text(result.noService ? l10n.noService : l10n.noOption);
              }
              return Column(
                children: [
                  if (result.notes.contains('fares_unknown'))
                    Padding(
                      padding: const EdgeInsets.only(bottom: Tokens.space3),
                      child: Fact(Icons.info_outline, l10n.faresUnknown),
                    ),
                  for (final option in result.options)
                    Padding(
                      padding: const EdgeInsets.only(bottom: Tokens.space3),
                      child: OptionCard(
                        option: option,
                        modeOf: modeOf,
                        onOpen: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => ItineraryScreen(
                              option: option,
                              to: widget.to.name,
                            ),
                          ),
                        ),
                        onWhy: () => showWhySheet(
                          context,
                          Explanation.forOption(l10n, option),
                        ),
                      ),
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
