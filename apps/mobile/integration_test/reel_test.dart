import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:nemesis_mobile/main.dart' as app;

/// The test APK on an Android 8 emulator, in CI : the lines of 2023 of Abidjan, the native
/// engine on the real pack, the yafohi map. Run with the data of 2023 declared
/// (tool/avec_donnees_2023.py) and `--dart-define=NEMESIS_DATA=reel`.
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  Future<void> waitFor(
    WidgetTester tester,
    Finder finder, {
    Duration timeout = const Duration(seconds: 90),
  }) async {
    final end = DateTime.now().add(timeout);
    while (finder.evaluate().isEmpty) {
      if (DateTime.now().isAfter(end)) {
        throw TestFailure('introuvable après $timeout : $finder');
      }
      await tester.pump(const Duration(milliseconds: 200));
    }
  }

  testWidgets('Yopougon to Le Plateau on the lines of 2023, then the map', (
    tester,
  ) async {
    app.main();
    await waitFor(tester, find.text('Tu vas où ?'));
    expect(find.text('LIGNES DE 2023 · À CONFIRMER'), findsWidgets);

    await tester.tap(find.text('Tu vas où ?'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'le plateau');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Le Plateau').last);
    await tester.pumpAndSettle();

    // The 2023 lines run from 5 h to 22 h, whatever the time of the emulator.
    await tester.tap(find.text('Partir à 7 h 30'));
    // The engine works on the real pack for a second or two: wait for its answer,
    // then for the screen to settle, and tap only what can be tapped.
    final duration = find
        .textContaining(RegExp(r'^\d+ à \d+ min$'))
        .hitTestable();
    await waitFor(tester, duration);
    await tester.pumpAndSettle();
    expect(find.textContaining('Prix inconnu'), findsWidgets);

    await tester.ensureVisible(duration.first);
    await tester.pumpAndSettle();
    await tester.tap(duration.first);
    await waitFor(tester, find.text('Je pars'));
    final navigator = tester.state<NavigatorState>(
      find.byType(Navigator).first,
    );
    navigator.pop();
    await tester.pumpAndSettle();
    navigator.pop();
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.map_outlined));
    await tester.pump(const Duration(seconds: 3));
    expect(tester.takeException(), isNull);
  });
}
