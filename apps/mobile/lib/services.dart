import 'package:flutter/widgets.dart';

import 'data/city.dart';
import 'data/store.dart';
import 'routing/plan.dart';

/// Builds the map of the Carte tab; tests replace it, since the native map does not
/// render in widget tests.
typedef MapBuilder = Widget Function(
  BuildContext context,
  CityData city,
  String mapJson,
  void Function(Stop stop) onStopTapped,
);

/// Everything the screens need, given once at start-up (and replaced in tests).
class AppServices extends InheritedWidget {
  const AppServices({
    super.key,
    required this.city,
    required this.mapJson,
    required this.routing,
    required this.store,
    required this.mapBuilder,
    required this.now,
    required this.showFictionalBanner,
    required this.storeChanges,
    required super.child,
  });

  final CityData city;
  final String mapJson;
  final RoutingService routing;
  final LocalStore store;
  final MapBuilder mapBuilder;
  final DateTime Function() now;

  /// « DONNÉES FICTIVES » : always with the fictional city, and in development builds.
  final bool showFictionalBanner;

  /// Bumped after each write to the store, so that lists of reports and trips refresh.
  final ValueNotifier<int> storeChanges;

  static AppServices of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<AppServices>()!;

  @override
  bool updateShouldNotify(AppServices oldWidget) =>
      city != oldWidget.city ||
      routing != oldWidget.routing ||
      store != oldWidget.store;
}
