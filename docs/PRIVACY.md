# Vie privée et protection des données

Version 0 du 2026-11-04 (incrément I0.3). **Brouillon technique, ce n'est pas un avis juridique.** Chaque point marqué ⚖️ doit être validé par un avocat ivoirien ou par l'ARTCI avant toute collecte réelle (partie 12 ; questions Q-04 et H-020). Le document est construit pour faciliter cette validation.

## Cadre

- **Loi n°2013-450** du 19 juin 2013 relative à la protection des données à caractère personnel, contrôlée par l'**ARTCI**. Selon le cahier des charges (2.6), elle exige une déclaration ou une autorisation préalable, y compris pour la géolocalisation. Elle encadre aussi les transferts hors du pays. ⚖️
- **Loi n°2013-451** relative à la lutte contre la cybercriminalité : sécurité des systèmes et gestion des incidents. ⚖️
- **État en phase 0** : aucune donnée personnelle réelle n'est traitée. Les collectes de terrain sont anonymes (H-020, H-023). Le premier traitement de données personnelles réelles n'interviendra qu'après le dépôt du dossier ARTCI ou un avis juridique écrit.

## Principes appliqués dans la conception

1. **Aucune donnée personnelle pour chercher un itinéraire.** Pas de compte obligatoire (F-13).
2. **Traitement sur le téléphone d'abord.** Trajets planifiés, lieux enregistrés (Maison, Boulot), détection de montée et de descente : tout reste sur l'appareil. Le serveur ne reçoit que le nécessaire (7.2).
3. **Séparation stricte entre identité et mobilité** : deux schémas, deux rôles, aucune jointure dans le code courant (ADR-005, H-016).
4. **Pseudonymes d'appareil renouvelés** pour les données de mobilité. Le numéro de téléphone est stocké haché pour les recherches et chiffré au repos, seulement s'il y a un compte.
5. **Traces tronquées sur le téléphone** : 300 m retirés au départ et à l'arrivée de chaque segment, avant tout envoi (7.4).
6. **Agrégation avant analyse, et seuil d'anonymat** : k ≥ 20 personnes distinctes pour toute publication ou tout export (12.2).
7. **Conservation limitée, appliquée par la structure de la base** : suppression de partitions par jour (ADR-005).
8. **Ni vente de données, ni publicité ciblée.** Aucun signalement de contrôles de police, aucune plaque ni aucun nom de chauffeur publiés (3.5, 12.4).

## Registre des traitements (v0)

La colonne « Base légale » est une proposition à qualifier par le juriste. ⚖️

| N° | Traitement | Finalité | Données | Personnes | Base légale proposée | Destinataires | Phase |
|----|------------|----------|---------|-----------|----------------------|---------------|-------|
| T1 | Recherche d'itinéraire | Proposer des trajets | Origine, destination, heure, sans identifiant. Adresse IP dans les journaux techniques | Usagers | Intérêt légitime, ou aucun traitement de données personnelles si l'adresse IP n'est pas conservée avec la requête ⚖️ | Aucun | MVP |
| T2 | Compte usager | Récompenses, synchronisation | Numéro de téléphone (haché et chiffré), préférences. Lieux enregistrés synchronisés seulement sur demande, chiffrés | Usagers avec compte | Contrat (conditions d'utilisation) | Passerelle SMS pour le code de connexion | MVP |
| T3 | Contributions | Temps réel, prix observés, corrections du réseau | Pseudonyme d'appareil, position au moment du signalement (contrôle à 150 m), contenu, heure, réputation | Contributeurs | Consentement ⚖️ | Agrégats publiés | MVP |
| T4 | Suivi de trajet et capteur passif | Alertes de descente ; vitesses et positions inférées des véhicules | Segments tronqués, pseudonymes renouvelés | Usagers qui suivent un trajet | Consentement explicite, séparé du reste, retirable ⚖️ | Aucun ; agrégats seulement | MVP (alertes), V2 (capteur passif) |
| T5 | Partage de trajet et urgence | Sécurité personnelle (F-11) | Position en direct, transmise par lien au contact choisi. L'appel d'urgence passe par le composeur du téléphone. L'envoi de position par SMS utilise de préférence l'appli SMS du téléphone, et non notre passerelle | Usager, son contact | Consentement ; intérêt vital pour l'urgence ⚖️ | Le contact choisi | MVP |
| T6 | Mode Pro | Signal de demande, carte des véhicules | Position du véhicule **uniquement en service**, session pseudonyme, ligne | Chauffeurs et apprentis | Consentement ⚖️ | Agrégats ; jamais un véhicule identifiable | V2 |
| T7 | Console de gare | Annoncer départs, files et messages | Compte (numéro), messages diffusés | Chefs de gare | Contrat | Usagers abonnés à la gare (messages) | V2 |
| T8 | WhatsApp, SMS, USSD, serveur vocal | Accès sans smartphone | Numéro (connu de l'opérateur), contenu des requêtes, mémoire de session courte, abonnements consentis | Usagers des canaux | Consentement pour les abonnements ; intérêt légitime pour répondre à une requête ⚖️ | Opérateurs, agrégateur SMS, Meta pour WhatsApp | MVP (WhatsApp tenu par un humain), V2 |
| T9 | Récompenses | Remercier les contributions validées | Numéro, registre des points, versements | Contributeurs avec compte | Contrat | Opérateurs télécoms, mobile money | V2 |
| T10 | Notifications | Alertes de trajet régulier | Jeton FCM de l'appareil | Usagers | Consentement (permission système) | Google (FCM) | MVP |
| T11 | Télémétrie et plantages | Qualité, budgets de performance | Événements techniques sans position ; identifiant d'installation renouvelé | Usagers | Intérêt légitime ⚖️ | Outil de remontée des plantages, si hébergé à l'extérieur | MVP |
| T12 | Back-office | Curation, modération, sécurité | Comptes du personnel, journal d'audit | Personnel | Contrat de travail ou de prestation | Aucun | MVP |
| T13 | Exports aux partenaires | Pilotage de la mobilité | Agrégats avec k ≥ 20 | Aucune personne identifiable | Données anonymes si le seuil est respecté ⚖️ | AMUGA, communes, ministère | V3 |
| T14 | Collectes de terrain (phase 0) | Évaluation et calibration | Données anonymes (requêtes, profils déclarés sans identité) | Participants | Aucune donnée personnelle collectée ⚖️ | Aucun | Phase 0 |

## Durées de conservation proposées ⚖️

| Donnée | Durée | Mise en œuvre |
|--------|-------|---------------|
| Positions brutes (segments, positions des véhicules Pro) | 30 jours au plus (12.2) | Suppression des partitions de `position_event` |
| Observations brutes (contributions) | 12 mois (12.2) | Suppression des partitions de `observation` |
| Agrégats anonymes (k ≥ 20) | Sans limite | Tables d'agrégats |
| Journaux techniques | 90 jours (12.2) | Rotation dans l'outil de journaux |
| Sessions des canaux (mémoire courte) | 24 h | Durée de vie dans Redis |
| Lien de partage de trajet | Jusqu'à l'arrivée, ou 4 h au plus | Jeton d'au moins 128 bits, révocable |
| Compte et numéro | Jusqu'à la suppression du compte, puis 30 jours de délai de grâce | Suppression en cascade, journalisée |
| Codes de connexion par SMS | 10 min | Durée de vie |
| Journal d'audit du back-office | 3 ans ⚖️ | Table en ajout seul, chaînée |

## Transferts hors de Côte d'Ivoire ⚖️

Ils dépendent de l'[ADR-004](DECISIONS/ADR-004-hebergement-transfert-donnees.md), où l'hébergement hybride est recommandé. Même dans ce cas, plusieurs sous-traitants reçoivent des données personnelles. Il faut le déclarer et l'encadrer par contrat :
- Google : jeton FCM, attestation Play Integrity ;
- Meta : numéro et messages WhatsApp ;
- l'agrégateur SMS : numéro, s'il est hors du pays ;
- l'outil de remontée des plantages, s'il est externe.

## Droits des personnes

Accessibles dans l'appli, rubrique « Moi », sans démarche écrite (12.1) :
- consulter ses données et les exporter dans un fichier lisible ;
- rectifier ses préférences et ses lieux ;
- supprimer son compte et ses données ;
- retirer chaque consentement séparément : contributions, suivi passif, notifications.

Pour les canaux : le mot-clé « STOP » par SMS ou WhatsApp met fin aux abonnements. Une version audio courte de la politique de confidentialité est prévue (12.1).

## Analyse d'impact de la géolocalisation (brouillon) ⚖️

### 1. Périmètre

T3 (position au signalement), T4 (suivi et capteur passif), T5 (partage de trajet) et T6 (mode Pro).

### 2. Nécessité et proportionnalité

- **Pourquoi la position est nécessaire** :
  - alertes de descente ;
  - vérification qu'un signalement est fait sur place (lutte contre la fraude, 7.5) ;
  - inférence des vitesses et des véhicules, qui font la valeur du service.
- **Alternatives retenues pour réduire la collecte** :
  - calculs faits sur le téléphone ;
  - envoi de segments plutôt que de traces complètes ;
  - troncature de 300 m ;
  - aucune position envoyée hors d'un trajet suivi ou d'un service Pro.
- **Consentements séparés**, demandés au moment où ils servent (10.7) : localisation à la première recherche, en arrière-plan au premier « Je pars ».

### 3. Risques et mesures

Vraisemblance et gravité sont notées sur l'échelle « négligeable, limitée, importante, maximale ».

| Risque | Origine | Avant mesures | Mesures | Risque résiduel |
|--------|---------|---------------|---------|-----------------|
| R1. Retrouver le domicile ou le travail à partir des traces | Débuts et fins de trajets, trajets répétés | Importante | Troncature de 300 m ; pseudonymes renouvelés ; séparation identité et mobilité ; agrégation avant analyse ; suppression à 30 jours | Limitée |
| R2. Suivi d'une personne par un lien de partage (harcèlement) | Lien transféré ou deviné | Importante | Jeton imprévisible ; expiration à l'arrivée ou à 4 h ; révocation ; aucune liste publique | Limitée |
| R3. Surveillance des chauffeurs (« c'est pour nous fliquer ? ») | Position du véhicule, exports aux autorités | Importante | Partage seulement en service, avec un indicateur permanent ; jamais de plaque ni de nom ; agrégats seulement ; aucune transmission sans obligation légale formelle (6.1) | Limitée |
| R4. Fuite ou accès non autorisé | Intrusion, erreur d'un administrateur | Maximale | Chiffrement au repos ; moindre privilège ; double authentification au back-office ; audit chaîné ; tests d'intrusion avant le lancement public (12.3) | Limitée |
| R5. Détournement de finalité | Demandes d'autorités, pression commerciale | Importante | Pas de vente ; agrégats avec k ≥ 20 ; procédure écrite pour les demandes des autorités ; politique de transparence publiée | Limitée |
| R6. Mineurs | Élèves utilisateurs | Limitée | Aucune donnée d'âge ; mêmes protections pour tous (12.5) | Négligeable |

### 4. Plan d'action avant toute collecte réelle

Faire valider ce brouillon par un juriste, puis :
1. rédiger la politique de confidentialité en français simple, avec sa version audio ;
2. intégrer ces textes au dossier ARTCI ;
3. contractualiser avec les sous-traitants ;
4. faire réaliser un test d'intrusion avant le pilote.

## Dossier ARTCI : brouillon du contenu ⚖️

1. **Responsable du traitement** : entité porteuse du projet, à désigner (Q-04).
2. **Correspondant à la protection des données** : à désigner (12.1).
3. **Traitements** : le registre ci-dessus (T1 à T13), avec finalités, catégories de données, personnes concernées et destinataires.
4. **Géolocalisation** : la présente analyse d'impact.
5. **Durées de conservation** : le tableau ci-dessus.
6. **Transferts hors du pays** : selon la décision de l'ADR-004 et la liste des sous-traitants.
7. **Mesures de sécurité** : [SECURITY.md](../SECURITY.md), le modèle de menaces (à produire en phase 1) et le plan de réponse aux incidents ci-dessous.
8. **Information et consentement** : textes et écrans de consentement, conditions d'utilisation, politique de confidentialité.
9. **Exercice des droits** : parcours dans l'appli et par les canaux.

## Réponse aux incidents de sécurité (12.3)

1. **Détecter** : alertes de supervision, signalement externe ([SECURITY.md](../SECURITY.md)).
2. **Contenir** : révoquer les accès, isoler les systèmes, préserver les preuves.
3. **Évaluer** : quelles données, combien de personnes, quels risques pour elles.
4. **Notifier** l'ARTCI, et les personnes concernées si nécessaire. Les délais légaux sont à confirmer ⚖️.
5. **Corriger, puis analyser** : compte rendu sans recherche de coupable, actions de suivi.

## Questions pour le juriste

1. Quel régime (déclaration ou autorisation) s'applique à chaque traitement, et notamment à T4 et T6 ?
2. Quelles bases légales retenir, et sous quelle forme recueillir le consentement à la géolocalisation ?
3. Des données pseudonymes et tronquées, puis des agrégats avec k ≥ 20, sont-ils considérés comme anonymes ?
4. Comment encadrer les transferts vers Google, Meta et l'agrégateur SMS ?
5. Les durées de conservation proposées sont-elles acceptables ?
6. Quelles obligations pèsent sur nous pour le partage de trajet et le bouton d'urgence ?
7. Quelle licence des contributions demander aux usagers pour publier des agrégats sous une licence compatible avec l'ODbL ?
8. Comment traiter la position des chauffeurs, qui ne sont pas nos salariés ?
9. Les protocoles de terrain de la phase 0 sont-ils bien hors du champ de la loi ?
