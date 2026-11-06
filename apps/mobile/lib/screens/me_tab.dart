import 'package:flutter/material.dart';

import '../design/tokens.dart';
import '../l10n/app_localizations.dart';
import '../services.dart';
import '../widgets/common.dart';

/// Moi tab: the reports waiting for the network, the data, privacy, text size, language.
class MeTab extends StatelessWidget {
  const MeTab({super.key});

  @override
  Widget build(BuildContext context) => ValueListenableBuilder<int>(
    valueListenable: AppServices.of(context).storeChanges,
    builder: (context, _, _) => _content(context),
  );

  String _kind(AppLocalizations l10n, String kind) => switch (kind) {
    'file' => l10n.reportQueue,
    'vehicules_presents' => l10n.reportVehicles,
    'vehicule_plein' => l10n.reportFull,
    'prix_paye' => l10n.reportPaid,
    _ => kind,
  };

  Widget _content(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final services = AppServices.of(context);
    final pending = services.store.pendingContributions();
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        Tokens.space4,
        Tokens.space4,
        Tokens.space4,
        96,
      ),
      children: [
        Semantics(
          header: true,
          child: Text(
            l10n.meTitle,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
        ),
        SectionTitle(l10n.mePending(pending.length)),
        Text(l10n.mePendingHint),
        for (final contribution in pending.take(10))
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.outbox_outlined),
            title: Text(_kind(l10n, contribution.kind)),
            subtitle: Text(
              contribution.payload.values.map((v) => '$v').join(', '),
            ),
          ),
        SectionTitle(l10n.meData),
        Text(
          l10n.meDataValue(services.city.name, services.city.networkVersion),
        ),
        SectionTitle(l10n.mePrivacy),
        Text(l10n.mePrivacyValue),
        SectionTitle(l10n.meTextSize),
        Text(l10n.meTextSizeValue),
        SectionTitle(l10n.meLanguage),
        Text(l10n.meLanguageValue),
      ],
    );
  }
}
