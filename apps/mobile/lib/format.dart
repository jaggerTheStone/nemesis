import 'package:intl/intl.dart';

import 'l10n/app_localizations.dart';
import 'routing/plan.dart';

/// Formats of the microcopy (10.4) : « 300 F », « 6 h 30 », « 10 à 20 min ».

final _thousands = NumberFormat('#,##0', 'fr');

String francs(AppLocalizations l10n, int amount) =>
    l10n.francs(_thousands.format(amount));

String fareRange(AppLocalizations l10n, Fare fare) => fare.p10 == fare.p90
    ? francs(l10n, fare.p50)
    : l10n.fareRange(_thousands.format(fare.p10), _thousands.format(fare.p90));

String minutesRange(AppLocalizations l10n, int low, int high) =>
    low >= high ? l10n.minutes(low) : l10n.minutesRange(low, high);

/// « 07:30 » → « 7 h 30 » ; « 08:00 » → « 8 h ».
String clockText(AppLocalizations l10n, String hhmm) {
  final parts = hhmm.split(':');
  final hours = int.parse(parts[0]);
  final minutes = int.parse(parts[1]);
  return minutes == 0
      ? l10n.clockHour(hours)
      : l10n.clockHourMinute(hours, minutes.toString().padLeft(2, '0'));
}

String clockOf(AppLocalizations l10n, DateTime time) => clockText(
  l10n,
  '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}',
);

/// Type of day of the fictional network for a date.
String dayType(DateTime date) => switch (date.weekday) {
  DateTime.saturday => 'samedi',
  DateTime.sunday => 'dimanche',
  _ => 'ouvrable',
};
