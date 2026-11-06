import 'dart:io';

import 'package:flutter/foundation.dart';
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

const _assets = 'assets/fictif/';

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
  final mapJson = await rootBundle.loadString('${_assets}map.json');
  final support = await getApplicationSupportDirectory();
  final pack = Directory('${support.path}/pack');
  final manifest = await AssetManifest.loadFromAssetBundle(rootBundle);
  for (final asset in manifest.listAssets()) {
    if (!asset.startsWith('${_assets}pack/')) continue;
    final target = File(
      '${pack.path}/${asset.substring('${_assets}pack/'.length)}',
    );
    await target.parent.create(recursive: true);
    final bytes = await rootBundle.load(asset);
    await target.writeAsBytes(
      bytes.buffer.asUint8List(bytes.offsetInBytes, bytes.lengthInBytes),
      flush: true,
    );
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
            now: DateTime.now,
            showFictionalBanner: loaded.city.isFictional || kDebugMode,
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
