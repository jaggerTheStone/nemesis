# ADR-006 — Temps réel vers les clients

- **Statut** : proposé. **Écart signalé à la partie 9.1** : la carte en direct utilise d'abord l'interrogation périodique, et non une connexion permanente (Server-Sent Events ou WebSocket). Voir la justification ci-dessous.
- **Date** : 2026-11-04
- **Casquettes consultées** : ingénieur backend et temps réel, ingénieur mobile, SRE, architecte

## Contexte

Ce que doit offrir la carte en direct (F-05) :
- elle ne charge que les mises à jour de la zone visible ;
- elle se rafraîchit toutes les 10 à 15 s au premier plan, et s'arrête en arrière-plan ;
- elle consomme moins de 150 Ko par minute ;
- elle tient en pointe, avec 50 000 personnes connectées en même temps.

**Au MVP**, la carte montre les **gares et les incidents**, dont l'état change à l'échelle de la minute. Les **véhicules** en direct arrivent en V2.

Le suivi de trajet (F-04) a un besoin différent : une seule personne, des alertes ponctuelles (incident sur le trajet, nouvel itinéraire proposé) qui doivent arriver vite.

La partie 9.1 recommande Server-Sent Events ou WebSocket, avec des deltas compacts en Protocol Buffers, et l'interrogation périodique en repli.

## Options envisagées

| Critère | Server-Sent Events | WebSocket | Interrogation périodique par tuile |
|---------|--------------------|-----------|------------------------------------|
| Connexions permanentes en pointe | 50 000 | 50 000 | Aucune |
| Mise en cache par un CDN | Non | Non | Oui : tous les usagers d'une même tuile partagent la réponse, gardée en cache quelques secondes |
| Réseau 3G instable, intermédiaires des opérateurs | Reconnexion automatique, reprise au dernier événement | Coupures fréquentes, reconnexion à gérer | Chaque requête est indépendante ; une perte coûte un rafraîchissement |
| Données binaires (protobuf) | Texte uniquement : base64, environ 33 % de plus | Binaire natif | Binaire natif |
| Changement de zone quand la carte bouge | Nouvelle connexion | Message sur la connexion | Nouvelles tuiles demandées |
| Latence d'une alerte | Immédiate | Immédiate | Jusqu'à un intervalle de rafraîchissement |
| Complexité côté serveur | Gestion des abonnements par zone | Gestion des abonnements par zone | Sans état : instantanés et deltas précalculés par tuile dans Redis |

**Estimation data par interrogation**, hypothèse à mesurer :
- la carte visible couvre de 4 à 6 tuiles au zoom 14 ;
- un rafraîchissement toutes les 12 s fait 5 requêtes par tuile et par minute, soit 20 à 30 requêtes par minute ;
- avec HTTP/2 et un en-tête compressé, chaque réponse delta pèse moins de 1 Ko.

On obtient moins de 30 Ko par minute, bien sous le budget de 150 Ko.

## Décision proposée

1. **Carte : interrogation périodique par tuile.**
   - Requête : `GET /v1/live/tiles/{z}/{x}/{y}?depuis=<version>`.
   - Réponse : un delta Protocol Buffers depuis la version connue du client, ou un instantané si elle est trop ancienne.
   - Mise en cache par le CDN pendant 5 s environ, avec ETag.
   - Rafraîchissement de 10 à 15 s au premier plan, arrêt en arrière-plan.
2. **Trajet suivi : Server-Sent Events** (`GET /v1/trips/{id}/events`), car une seule connexion par personne suit son trajet. Les alertes sont du texte court, sans base64 coûteux. En cas de coupure, l'appli reprend par interrogation.
3. **Notifications hors de l'appli** : Firebase Cloud Messaging (9.1).

**Pourquoi s'écarter de la partie 9.1 ?** À un rythme de 10 à 15 s, l'interrogation par tuile coûte moins de data. Elle supprime 50 000 connexions permanentes : avec un CDN qui met en cache, le serveur répond à une requête par tuile et par intervalle, pas une par usager. Elle tolère mieux les réseaux instables. Elle suffit largement pour les gares et les incidents du MVP. La partie 9.1 prévoit déjà l'interrogation périodique comme repli : nous en faisons le mode principal de la carte, et réservons la connexion permanente au trajet suivi.

**Désaccord entre casquettes.** L'ingénieur temps réel préfère WebSocket pour la V2, quand les véhicules bougeront à chaque rafraîchissement. Le SRE préfère l'interrogation pour le coût et la robustesse. On tranche pour l'interrogation au MVP, avec un point de réexamen à l'arrivée des véhicules en direct, mesures k6 à l'appui (9.4).

## Conséquences

- **Implémentation** :
  - l'agrégation écrit, pour chaque tuile, un numéro de version et un journal de deltas récents dans Redis ;
  - l'API sert ces blobs sans calcul ;
  - le contrat est dans `packages/proto` (I0.6).
- **Budget data** : il est mesuré en phase 1, sur le téléphone de référence en 3G simulée.
- **Réversibilité** : bonne. Le format des deltas est le même, quel que soit le transport ; passer à WebSocket ne change que la façon de les acheminer.
