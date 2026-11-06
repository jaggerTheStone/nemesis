import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nemesis_mobile/data/store.dart';

import 'support.dart';

void main() {
  testWidgets('home: banner, « Tu vas où ? », shortcuts and stations nearby', (
    tester,
  ) async {
    await phone(tester);
    await tester.pumpWidget(testApp());
    await tester.pumpAndSettle();

    expect(find.text('DONNÉES FICTIVES'), findsOneWidget);
    expect(find.text('Tu vas où ?'), findsOneWidget);
    expect(find.text('Maison'), findsOneWidget);
    expect(find.text('Autour de moi'), findsOneWidget);
    expect(find.text('Gare des Flamboyants (fictif)'), findsOneWidget);
    expect(find.text('Trajet'), findsOneWidget);
    expect(find.text('Carte'), findsWidgets);
    expect(find.text('Moi'), findsOneWidget);
    expect(find.text('Signaler'), findsOneWidget);
  });

  testWidgets('search, results with labelled options, then step by step', (
    tester,
  ) async {
    await phone(tester);
    final routing = FixtureRouting();
    await tester.pumpWidget(testApp(routing: routing));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Tu vas où ?'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'embarcadere sud');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Embarcadère Sud (fictif)').last);
    await tester.pumpAndSettle();

    expect(routing.queries, hasLength(1));
    expect(routing.queries.single.at, testNow);
    expect(find.text('Le plus rapide'), findsWidgets);
    expect(find.text('Le moins cher'), findsWidgets);
    expect(find.text('Le plus simple'), findsWidgets);
    expect(find.text('59 à 64 min'), findsOneWidget);
    // French thousands use a narrow no-break space.
    expect(find.textContaining(RegExp(r'^700 à 1.250 F$')), findsOneWidget);

    // Leaving later computes again.
    await tester.tap(find.text('Partir à 18 h'));
    await tester.pumpAndSettle();
    expect(routing.queries.last.at, DateTime(2026, 11, 10, 18));

    await tester.tap(find.text('59 à 64 min'));
    await tester.pumpAndSettle();
    expect(find.text('Ton trajet'), findsOneWidget);
    expect(find.textContaining('Prends le gbaka'), findsWidgets);
    expect(find.textContaining('Descends à'), findsWidgets);
    expect(find.text('Je pars'), findsOneWidget);
  });

  testWidgets('« Pourquoi cette estimation ? » says where, when and who', (
    tester,
  ) async {
    await phone(tester);
    await tester.pumpWidget(testApp());
    await tester.pumpAndSettle();
    await tester.tap(find.text('Tu vas où ?'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'embarcadere sud');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Embarcadère Sud (fictif)').last);
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Pourquoi ?').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Pourquoi ?').first);
    await tester.pumpAndSettle();
    expect(find.text("D'où vient ce chiffre"), findsOneWidget);
    expect(find.text('Quand'), findsOneWidget);
    expect(find.textContaining('Réseau fictif'), findsOneWidget);
    expect(find.textContaining('Confiance'), findsOneWidget);
  });

  testWidgets('a report takes two taps and waits in the local queue (F-07)', (
    tester,
  ) async {
    await phone(tester);
    final store = SqliteStore.inMemory();
    await tester.pumpWidget(testApp(store: store));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Signaler')); // first tap
    await tester.pumpAndSettle();
    expect(find.text('Que vois-tu ?'), findsOneWidget);
    await tester.tap(find.text('Beaucoup')); // second tap
    await tester.pumpAndSettle();

    expect(
      find.text('Merci ! Envoyé dès que le réseau revient.'),
      findsOneWidget,
    );
    final pending = store.pendingContributions();
    expect(pending, hasLength(1));
    expect(pending.single.kind, 'file');
    expect(pending.single.payload, {'level': 'beaucoup'});
    expect(pending.single.stopId, testCity().stop('flamboyants')!.id);

    await tester.tap(find.text('Moi'));
    await tester.pumpAndSettle();
    expect(find.text('1 signalement en attente'), findsOneWidget);
  });

  testWidgets('station sheet: lines, usual wait, best hour, fares (F-06)', (
    tester,
  ) async {
    await phone(tester);
    await tester.pumpWidget(testApp());
    await tester.pumpAndSettle();
    await tester.tap(find.text('Gare des Flamboyants (fictif)'));
    await tester.pumpAndSettle();

    expect(find.text('Lignes'), findsOneWidget);
    expect(
      find.text('Aucun signalement récent. Estimation historique.'),
      findsOneWidget,
    );
    expect(find.textContaining('Habituellement à cette heure'), findsWidgets);
    await tester.scrollUntilVisible(find.text('Prix par destination'), 300);
    expect(find.text('Prix par destination'), findsOneWidget);
  });

  testWidgets('the map tab shows the map and its legend', (tester) async {
    await phone(tester);
    await tester.pumpWidget(testApp());
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.map_outlined));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('map')), findsOneWidget);
    expect(find.text('Légende'), findsOneWidget);

    await tester.tap(
      find.descendant(
        of: find.byKey(const Key('map')),
        matching: find.byType(TextButton),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Gare des Flamboyants (fictif)'), findsOneWidget);
  });
}
