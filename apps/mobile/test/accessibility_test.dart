import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nemesis_mobile/design/tokens.dart';

import 'support.dart';

/// Bases of accessibility (10.3, 10.6) : zones tactiles de 48 dp, libellés, contraste,
/// texte courant de 16 sp, agrandissement à 200 % sans casse.
void main() {
  test('body text is at least 16 sp in both themes', () {
    for (final brightness in Brightness.values) {
      final text = buildTheme(brightness).textTheme;
      for (final style in [
        text.bodyLarge,
        text.bodyMedium,
        text.bodySmall,
        text.titleMedium,
        text.labelLarge,
      ]) {
        expect(style!.fontSize, greaterThanOrEqualTo(Tokens.textBody));
      }
    }
  });

  test('the fictional banner and the labels keep a high contrast', () {
    double luminance(Color c) => c.computeLuminance();
    double ratio(Color a, Color b) {
      final (l1, l2) = (luminance(a), luminance(b));
      return (l1 > l2 ? l1 + 0.05 : l2 + 0.05) /
          (l1 > l2 ? l2 + 0.05 : l1 + 0.05);
    }

    expect(ratio(Tokens.onFictional, Tokens.fictional), greaterThan(7));
    expect(ratio(Tokens.onAccent, Tokens.accent), greaterThan(7));
    expect(ratio(Tokens.onBrand, Tokens.brand), greaterThan(4.5));
    expect(ratio(Tokens.ink, Tokens.paper), greaterThan(7));
    for (final level in QueueLevel.values) {
      expect(
        ratio(Colors.white, level.color),
        greaterThan(4.5),
        reason: level.name,
      );
    }
  });

  Future<void> checkGuidelines(WidgetTester tester) async {
    await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
    await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
    await expectLater(tester, meetsGuideline(textContrastGuideline));
  }

  testWidgets('home meets the tap target, label and contrast guidelines', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    await phone(tester);
    await tester.pumpWidget(testApp());
    await tester.pumpAndSettle();
    await checkGuidelines(tester);
    handle.dispose();
  });

  testWidgets('results and report sheet meet the guidelines', (tester) async {
    final handle = tester.ensureSemantics();
    await phone(tester);
    await tester.pumpWidget(testApp());
    await tester.pumpAndSettle();
    await tester.tap(find.text('Tu vas où ?'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'embarcadere sud');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Embarcadère Sud (fictif)').last);
    await tester.pumpAndSettle();
    await checkGuidelines(tester);

    tester.state<NavigatorState>(find.byType(Navigator).first).pop();
    await tester.pumpAndSettle();
    await tester.tap(find.text('Signaler'));
    await tester.pumpAndSettle();
    await checkGuidelines(tester);
    handle.dispose();
  });
}
