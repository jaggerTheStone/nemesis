import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:nemesis_mobile/main.dart' as app;

/// Smoke test on an Android 8 emulator (API 26), in CI: the real app, offline, with the
/// native engine, SQLite and the MapLibre map.
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  Future<void> waitFor(
    WidgetTester tester,
    Finder finder, {
    Duration timeout = const Duration(seconds: 60),
  }) async {
    final end = DateTime.now().add(timeout);
    while (finder.evaluate().isEmpty) {
      if (DateTime.now().isAfter(end)) {
        throw TestFailure('introuvable après $timeout : $finder');
      }
      await tester.pump(const Duration(milliseconds: 200));
    }
  }

  testWidgets('search, plan offline, report, map', (tester) async {
    app.main();
    await waitFor(tester, find.text('Tu vas où ?'));
    expect(find.text('DONNÉES FICTIVES'), findsOneWidget);

    await tester.tap(find.text('Tu vas où ?'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'embarcadere sud');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Embarcadère Sud (fictif)').last);
    await tester.pumpAndSettle();

    // The network runs at 7 h 30, whatever the time of the emulator.
    await tester.tap(find.text('Partir à 7 h 30'));
    await waitFor(tester, find.text('Le plus rapide'));
    expect(find.text('Le moins cher'), findsWidgets);

    await tester.tap(find.textContaining(RegExp(r'^\d+ à \d+ min$')).first);
    await waitFor(tester, find.text('Je pars'));
    final navigator = tester.state<NavigatorState>(
      find.byType(Navigator).first,
    );
    navigator.pop();
    await tester.pumpAndSettle();
    navigator.pop();
    await tester.pumpAndSettle();

    await tester.tap(find.text('Signaler'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Beaucoup'));
    await waitFor(
      tester,
      find.text('Merci ! Envoyé dès que le réseau revient.'),
    );

    await tester.tap(find.text('Moi'));
    await tester.pumpAndSettle();
    expect(find.textContaining('en attente'), findsWidgets);

    await tester.tap(find.byIcon(Icons.map_outlined));
    for (var i = 0; i < 25; i++) {
      await tester.pump(const Duration(milliseconds: 200));
    }
    expect(find.text('Légende'), findsOneWidget);
  });
}
