import 'package:flutter/material.dart';

import '../design/tokens.dart';
import '../l10n/app_localizations.dart';
import '../services.dart';
import 'station.dart';

/// Carte tab (F-05) : la carte hors ligne de la ville, et une légende toujours visible.
class MapTab extends StatelessWidget {
  const MapTab({super.key});

  @override
  Widget build(BuildContext context) {
    final services = AppServices.of(context);
    final l10n = AppLocalizations.of(context);
    return Stack(
      children: [
        Positioned.fill(
          child: services.mapBuilder(
            context,
            services.city,
            services.mapJson,
            (stop) => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => StationScreen(stop: stop),
              ),
            ),
          ),
        ),
        Positioned(
          left: Tokens.space3,
          top: Tokens.space3,
          right: 96,
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(Tokens.space3),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Semantics(
                    header: true,
                    child: Text(
                      l10n.mapLegend,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  _LegendRow(size: 18, text: l10n.mapStation),
                  _LegendRow(size: 12, text: l10n.mapStop),
                  Text(
                    l10n.mapOffline,
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _LegendRow extends StatelessWidget {
  const _LegendRow({required this.size, required this.text});

  final double size;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 2),
    child: Row(
      children: [
        SizedBox(
          width: 24,
          child: Center(
            child: Container(
              width: size,
              height: size,
              decoration: BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
                border: Border.all(color: Tokens.brand, width: 3),
              ),
            ),
          ),
        ),
        const SizedBox(width: Tokens.space2),
        Expanded(child: Text(text)),
      ],
    ),
  );
}
