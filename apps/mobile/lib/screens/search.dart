import 'package:flutter/material.dart';

import '../data/city.dart';
import '../design/tokens.dart';
import '../l10n/app_localizations.dart';
import '../services.dart';
import 'shell.dart';

/// Search of a destination among the stops and places of the city (F-01) : sans
/// accents, sans casse, par les alias, hors ligne.
class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final city = AppServices.of(context).city;
    final results = city.search(_query);
    return BannerScaffold(
      title: l10n.whereTo,
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(Tokens.space4),
            child: TextField(
              autofocus: true,
              textInputAction: TextInputAction.search,
              style: const TextStyle(fontSize: Tokens.textTitle),
              decoration: InputDecoration(
                prefixIcon: const Icon(Icons.search),
                hintText: l10n.searchHint,
                border: const OutlineInputBorder(),
              ),
              onChanged: (value) => setState(() => _query = value),
              onSubmitted: (_) {
                if (results.isNotEmpty) {
                  Navigator.of(context).pop(results.first);
                }
              },
            ),
          ),
          Expanded(
            child: _query.trim().isNotEmpty && results.isEmpty
                ? Padding(
                    padding: const EdgeInsets.all(Tokens.space4),
                    child: Text(l10n.searchNothing),
                  )
                : ListView(
                    children: [
                      for (final result in results)
                        ListTile(
                          leading: Icon(_icon(result)),
                          title: Text(result.name),
                          subtitle: Text(_kind(l10n, result)),
                          onTap: () => Navigator.of(context).pop(result),
                        ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  IconData _icon(Destination d) => switch (d) {
    Destination(stop: final s?) when s.isStation => Icons.storefront,
    Destination(stop: _?) => Icons.signpost_outlined,
    _ => Icons.place_outlined,
  };

  String _kind(AppLocalizations l10n, Destination d) => switch (d) {
    Destination(stop: final s?) when s.isStation => l10n.searchStation,
    Destination(stop: _?) => l10n.searchStop,
    _ => l10n.searchPlace,
  };
}
