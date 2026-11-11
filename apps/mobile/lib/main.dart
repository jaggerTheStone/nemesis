import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

import 'app.dart';
import 'data/city.dart';
import 'data/store.dart';
import 'design/tokens.dart';
import 'l10n/app_localizations.dart';
import 'routing/native_engine.dart';
import 'screens/map_view.dart';
import 'services.dart';

/// Embedded data set: `fictif` (default, tests and measured APK) or `reel`, the lines
/// of 2023 for the test APK (`--dart-define=NEMESIS_DATA=reel`, H-030).
const _data = String.fromEnvironment('NEMESIS_DATA', defaultValue: 'fictif');
const _assets = 'assets/$_data/';

/// The lines of 2023 run on a 2023 calendar : the clock keeps the day of the week and
/// the time of day, on a week of June 2023.
DateTime in2023() {
  final now = DateTime.now();
  return DateTime(2023, 6, 11 + now.weekday, now.hour, now.minute);
}

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const Bootstrap());
}

/// What the app loads at start-up, all offline: the city, the map, the engine on its
/// pack, and the local store.
class Loaded {
  const Loaded(this.city, this.mapJson, this.routing, this.store);

  final CityData city;
  final String mapJson;
  final NativeRoutingService routing;
  final SqliteStore store;
}

/// Copies the engine's pack out of the APK (the engine reads files), then opens it.
Future<Loaded> loadEverything() async {
  final city = CityData.fromJson(
    await rootBundle.loadString('${_assets}city.json'),
  );
  var mapJson = await rootBundle.loadString('${_assets}map.json');
  final support = await getApplicationSupportDirectory();
  final pack = Directory('${support.path}/pack');
  final manifest = await AssetManifest.loadFromAssetBundle(rootBundle);
  for (final asset in manifest.listAssets()) {
    if (!asset.startsWith('${_assets}pack/') &&
        !asset.startsWith('${_assets}carte/')) {
      continue;
    }
    final target = File('${support.path}/${asset.substring(_assets.length)}');
    await target.parent.create(recursive: true);
    final bytes = await rootBundle.load(asset);
    await target.writeAsBytes(
      bytes.buffer.asUint8List(bytes.offsetInBytes, bytes.lengthInBytes),
      flush: true,
    );
  }
  // The map engine reads the background quarters from files.
  final map = jsonDecode(mapJson) as Map<String, dynamic>;
  final background = map['background'] as Map<String, dynamic>?;
  if (background != null) {
    for (final image
        in (background['images'] as List).cast<Map<String, dynamic>>()) {
      image['url'] = 'file://${support.path}/carte/${image['file']}';
    }
    mapJson = jsonEncode(map);
  }
  final routing = NativeRoutingService.open(pack.path);
  final store = SqliteStore.open('${support.path}/nemesis.db');
  return Loaded(city, mapJson, routing, store);
}

class Bootstrap extends StatefulWidget {
  const Bootstrap({super.key});

  @override
  State<Bootstrap> createState() => _BootstrapState();
}

class _BootstrapState extends State<Bootstrap> {
  late final Future<Loaded> _loading = loadEverything();
  final _changes = ValueNotifier(0);

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Loaded>(
      future: _loading,
      builder: (context, snapshot) {
        final loaded = snapshot.data;
        if (loaded == null) {
          return _Waiting(error: snapshot.error);
        }
        return NemesisApp(
          services: (child) => AppServices(
            city: loaded.city,
            mapJson: loaded.mapJson,
            routing: loaded.routing,
            store: loaded.store,
            mapBuilder: mapLibreBuilder,
            now: loaded.city.isFictional ? DateTime.now : in2023,
            showFictionalBanner: true,
            storeChanges: _changes,
            child: child,
          ),
        );
      },
    );
  }
}

class _Waiting extends StatelessWidget {
  const _Waiting({this.error});

  final Object? error;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      locale: const Locale('fr', 'CI'),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      theme: buildTheme(Brightness.light),
      home: Builder(
        builder: (context) {
          final l10n = AppLocalizations.of(context);
          return Scaffold(
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(Tokens.space5),
                child: Text(
                  error == null
                      ? l10n.loadingCity
                      : l10n.startupError('$error'),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
