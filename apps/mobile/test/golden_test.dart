/// Visual references of the main screens, on a 5-inch phone, with the text at 100 % and
/// at 200 % (10.6). An overflow at 200 % makes the test fail: the text must grow
/// without breaking the layout. Regenerate with `flutter test --update-goldens`.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support.dart';

/// Scrolls the list of the screen on top until [finder] matches, then taps its first
/// match. Lists build their items lazily, hence the scrolling before the search.
Future<void> reveal(WidgetTester tester, Finder finder) async {
  final list = find.byType(Scrollable).hitTestable().first;
  for (var i = 0; i < 30 && finder.evaluate().isEmpty; i++) {
    await tester.drag(list, const Offset(0, -300));
    await tester.pumpAndSettle();
  }
  await tester.ensureVisible(finder.first);
  await tester.pumpAndSettle();
  await tester.tap(finder.first);
  await tester.pumpAndSettle();
}

void main() {
  Future<void> openResults(WidgetTester tester) async {
    await tester.tap(find.text('Tu vas où ?'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'embarcadere sud');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Embarcadère Sud (fictif)').last);
    await tester.pumpAndSettle();
  }

  final screens = <String, Future<void> Function(WidgetTester)>{
    'accueil': (_) async {},
    'resultats': openResults,
    'pas_a_pas': (tester) async {
      await openResults(tester);
      await reveal(tester, find.textContaining(RegExp(r'^\d+ à \d+ min$')));
    },
    'fiche_gare': (tester) async {
      await reveal(tester, find.text('Gare des Flamboyants (fictif)'));
    },
    'signaler': (tester) async {
      await tester.tap(find.text('Signaler'));
      await tester.pumpAndSettle();
    },
    'pourquoi': (tester) async {
      await openResults(tester);
      await reveal(tester, find.text('Pourquoi ?'));
    },
    'moi': (tester) async {
      await tester.tap(find.byIcon(Icons.person_outline));
      await tester.pumpAndSettle();
    },
  };

  for (final scale in [1.0, 2.0]) {
    final percent = (scale * 100).round();
    for (final MapEntry(key: name, value: open) in screens.entries) {
      testWidgets('$name at $percent %', (tester) async {
        await phone(tester, textScale: scale);
        await tester.pumpWidget(testApp());
        await tester.pumpAndSettle();
        await open(tester);
        await expectLater(
          find.byType(MaterialApp),
          matchesGoldenFile('goldens/${name}_$percent.png'),
        );
      });
    }
  }
}
