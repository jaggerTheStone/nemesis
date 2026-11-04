import 'package:flutter_test/flutter_test.dart';
import 'package:nemesis_mobile/main.dart';

void main() {
  testWidgets('home screen shows translated texts', (tester) async {
    await tester.pumpWidget(const NemesisApp());
    await tester.pumpAndSettle();

    expect(find.text('nemesis'), findsOneWidget);
    expect(find.text('Ton trajet commence ici.'), findsOneWidget);
  });
}
