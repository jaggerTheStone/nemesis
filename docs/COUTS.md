# Coûts

Version 0 du 2026-11-04 (incrément I0.3). Ce document chiffre les coûts d'infrastructure et de canaux par utilisateur actif et par requête (parties 9.4 et 13.4).

## Méthode et limites

Cette version modélise les **volumes** : machines, stockage, trafic, messages. Elle donne les **formules** pour passer aux coûts. Elle ne contient **aucun prix unitaire non vérifié**. Les prix sont à collecter auprès des fournisseurs (tableau plus bas), et le budget est une décision du porteur du projet (15.6).

Le dimensionnement des machines est un ordre de grandeur. Il sera remplacé par les mesures des tests de charge k6 de la phase 1.

## Hypothèses d'usage, par utilisateur actif et par jour

| Usage | Valeur retenue | Origine |
|-------|----------------|---------|
| Recherches d'itinéraire | 2 | Hypothèse : un aller et un retour |
| Minutes de carte active | 5 | Hypothèse |
| Heures de trajet suivi | 0,5 | Hypothèse : tous les usagers ne suivent pas leur trajet |
| Contributions | 0,5 | Hypothèse ; cible de 15 % de contributeurs par semaine (14.2) |
| Usagers avec pack hors ligne | 50 % | Hypothèse |
| Requêtes passées par WhatsApp, SMS ou USSD | paramètre *c* | Inconnu : c'est un indicateur d'inclusion à suivre (14.2) |

## Paliers

Les cibles de la deuxième année viennent de la partie 9.4 : 300 000 utilisateurs actifs par jour, 50 000 connectés simultanés, 200 itinéraires par seconde et 2 000 événements par seconde. On les met à l'échelle des autres paliers en gardant les mêmes rapports.

| Palier | Utilisateurs actifs par jour | Connectés en pointe | Itinéraires par seconde (pic) | Événements par seconde (pic) | Recherches par jour |
|--------|------------------------------|---------------------|-------------------------------|------------------------------|---------------------|
| Pilote fermé | 50 | ~10 | négligeable | négligeable | 100 |
| Bêta sur le corridor | 10 000 | ~1 700 | ~7 | ~70 | 20 000 |
| Tout Abidjan | 100 000 | ~17 000 | ~67 | ~670 | 200 000 |
| Deuxième année (9.4) | 300 000 | 50 000 | 200 | 2 000 | 600 000 |

**Les cibles de la partie 9.4 laissent une grande marge.** 600 000 recherches par jour, réparties sur les 6,5 h de pointe, font environ 26 recherches par seconde. Viser 200 par seconde laisse donc une marge d'environ 8 fois, adaptée aux pics brutaux pendant les pluies, quand tout le monde recalcule en même temps. Nous gardons la cible de 9.4.

## Dimensionnement des machines (ordre de grandeur, à mesurer)

| Palier | Machines | Base de données |
|--------|----------|-----------------|
| Pilote | 1 VM (4 vCPU, 8 Go), Docker Compose | Sur la même VM ; sauvegarde quotidienne chiffrée hors de la machine |
| Bêta | 2 à 3 VM, comme le prévoit la partie 9.2 : API et moteur ; base ; supervision | Primaire et réplica |
| Abidjan | 6 à 8 VM | Primaire et réplica de taille moyenne |
| Deuxième année | 12 à 16 VM : API, moteur, agrégation, canaux, supervision | Primaire, réplica, partitions d'événements (environ 300 Go de positions sur 30 jours, ADR-005) |

## Trafic sortant vers les usagers (plafond)

Le calcul utilise les **budgets maximaux** de la partie 9.3. Le trafic réel sera plus bas grâce aux caches et au hors ligne.

| Poste | Par utilisateur actif et par jour |
|-------|-----------------------------------|
| Recherches (2 × 30 Ko) | 60 Ko |
| Carte (5 min × 150 Ko) | 750 Ko |
| Trajet suivi (0,5 h × 300 Ko) | 150 Ko |
| Différentiel du pack (50 % × 300 Ko) | 150 Ko |
| **Total** | **environ 1,1 Mo**, soit environ 33 Mo par mois |

À ce plafond s'ajoutent les packs complets des nouveaux usagers : 15 Mo, ou 60 Mo avec fond de carte, téléchargés en Wi-Fi.

| Palier | Trafic sortant mensuel (plafond, hors nouveaux packs) |
|--------|-------------------------------------------------------|
| Bêta (10 000) | environ 330 Go |
| Abidjan (100 000) | environ 3,3 To |
| Deuxième année (300 000) | environ 10 To |

La majeure partie (tuiles, packs, deltas de carte par tuile, ADR-006) peut passer par un CDN.

## Canaux sans smartphone : le poste à surveiller

Les canaux coûtent **par message**. Leur coût augmente donc avec l'usage, contrairement aux machines.

Exemple de volume, sans prix : si 10 % des requêtes de la deuxième année passent par SMS, cela fait 60 000 requêtes par jour. Avec une réponse de deux SMS au plus (11.3), on atteint 120 000 SMS sortants par jour, soit environ **3,6 millions par mois**. Les SMS entrants s'y ajoutent si le numéro court les facture.

Conséquences :
- les **prix unitaires des canaux sont la première inconnue à lever** : ce sont eux qui feront varier le coût par utilisateur ;
- les leviers sont les suivants :
  - réponse en un seul SMS quand c'est possible (le comptage des segments existe déjà dans `services/channels`) ;
  - WhatsApp pour les conversations ouvertes par l'usager, à la tarification en vigueur à vérifier au moment de l'implémentation (11.2) ;
  - accords avec les opérateurs pour la gratuité de la data ou un prix réduit des SMS et de l'USSD (13.2) ;
  - abonnements limités à ce que l'usager a demandé.

## Prix unitaires à collecter

| Poste | Unité | Où demander | Valeur | Date |
|-------|-------|-------------|--------|------|
| Machine virtuelle (option locale et option internationale, ADR-004) | par vCPU et par Go de mémoire, par mois | Hébergeurs en Côte d'Ivoire ; fournisseurs de cloud | à collecter | |
| Stockage de blocs et sauvegardes chiffrées | par Go et par mois | Idem | à collecter | |
| Stockage objet et CDN | par Go stocké, par Go servi | Fournisseurs de CDN présents dans la sous-région | à collecter | |
| Trafic sortant | par Go | Hébergeur | à collecter | |
| SMS sortant et entrant | par message | Agrégateurs agréés ; Orange, MTN, Moov | à collecter | |
| Numéro court | frais fixes | Opérateurs | à collecter | |
| Session USSD | par session, frais fixes | Opérateurs ou agrégateur (11.4) | à collecter | |
| WhatsApp Business | par conversation ou par message, selon la grille en vigueur | Grille publique de Meta ou fournisseur agréé | à collecter | |
| Firebase Cloud Messaging | — | Google | gratuit | |
| Remontée des plantages, supervision | par mois | Outil choisi, hébergé ou externe | à collecter | |

## Formules

```text
coût_mensuel = Σ (machines × prix_machine) + stockage × prix_stockage
             + trafic_sortant × prix_trafic + CDN × prix_cdn
             + SMS_sortants × prix_sms + SMS_entrants × prix_sms_entrant
             + sessions_USSD × prix_ussd + conversations_WhatsApp × prix_whatsapp
             + supervision + frais fixes (numéro court, domaines)

coût_par_utilisateur_actif = coût_mensuel ÷ (utilisateurs actifs par jour × 30)
coût_par_requête[canal]    = coût variable du canal ÷ nombre de requêtes du canal
```

Le coût par requête et par canal sera suivi en exploitation (11.7).

## Ce que l'usager paie en data

Le cahier des charges (2.6) donne un prix de la data d'environ 1 000 à 1 800 FCFA le Go. Chaque octet est donc un coût pour l'usager (principe 3.4.3). Aux budgets maximaux :

| Usage | Volume maximal | Coût pour l'usager |
|-------|----------------|--------------------|
| Une recherche d'itinéraire | 30 Ko | 0,03 à 0,05 FCFA |
| Une minute de carte active | 150 Ko | 0,15 à 0,27 FCFA |
| Une heure de trajet suivi | 300 Ko | 0,30 à 0,54 FCFA |
| Mise à jour quotidienne du pack | 300 Ko | 0,30 à 0,54 FCFA |
| Pack ville sans fond de carte (en Wi-Fi conseillé) | 15 Mo | 15 à 27 FCFA |
| Pack ville avec fond de carte léger | 60 Mo | 60 à 108 FCFA |

**Le cas d'Awa** (persona de la partie 4.1, forfait de 500 FCFA par semaine).

Une journée type :
- 2 recherches : 60 Ko ;
- 1 h de trajet suivi : 300 Ko ;
- 5 min de carte : 750 Ko.

Cela fait environ 1,1 Mo par jour, soit 1,1 à 2,0 FCFA. Sur une semaine, environ 7,8 Mo, soit **1,6 % à 2,8 % de son forfait**.

Cet ordre de grandeur sera mesuré sur le téléphone de référence en phase 1 : le compteur de data dans les réglages fait partie de F-12.

## Prochaines étapes

1. Collecter les prix unitaires, en priorité ceux des canaux et de l'hébergement local (ADR-004).
2. Remplacer le dimensionnement par les mesures k6 de la phase 1.
3. Publier un tableau par palier avec le coût par utilisateur actif et par requête, et le soumettre au porteur du projet pour fixer le budget (15.6).
