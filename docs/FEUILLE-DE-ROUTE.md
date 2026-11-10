# Feuille de route : rendre yafohi vraiment utilisable

Statut : version 1 du 2026-11-10, à valider par le porteur. Elle part de l'essai de yafohi sur les lignes réelles de 2023 du corridor Yopougon – Adjamé – Plateau (canevas de la maquette, rangée « Nouveau »).

## Ce que l'essai a montré

L'appli fonctionne sur de vraies données. Le moteur calcule un trajet réel en moins d'une seconde, avec ses marches, ses correspondances et son pas à pas. Mais ces données ne suffisent pas pour un vrai usager :

| Constat | Conséquence pour l'usager |
|---------|---------------------------|
| Les lignes datent de 2023. 33 des lignes du corridor sont des « Gbaka d'Adjamé », d'avant l'interdiction des gbakas à Adjamé (mars 2025) et d'avant la réorganisation de l'AMUGA (octobre 2026) | Des trajets proposés n'existent plus |
| Aucun prix dans les données | L'appli affiche « prix inconnu » partout |
| Une seule fréquence par ligne, de 5 h à 22 h, annoncée et non observée | Les attentes ne changent pas entre la pointe et le creux |
| Ni bus SOTRA ni bateau-bus | Des trajets plus simples manquent |
| Des noms d'arrêts vagues ou en double (« Bord de route après… », deux « Pont piéton ») | Difficile de savoir où monter et descendre |
| Des tracés de ligne qui font de grands détours | Le dessin du trajet est parfois faux |
| Le moteur garde parfois des options absurdes (un trajet de 1 minute suivi d'une correspondance) | Des choix inutiles à l'écran |
| Aucune information en direct (affluence, incidents, véhicules) | L'appli ne fait pas encore mieux qu'un plan papier |

## Ce qu'il reste à faire, dans l'ordre

### 1. Les données du corridor : indispensable avant tout lancement

| Tâche | Qui | Effort |
|-------|-----|--------|
| Écrire à DigitalTransport4Africa : autorisation d'usage, et proposition de mise à jour commune | Vous, à partir de mon brouillon | Un courrier |
| Demander à la SOTRA ses lignes de bus et de bateau-bus, à l'AMUGA l'organisation actuelle des gbakas et des wôrô-wôrôs | Vous, à partir de mes brouillons | Deux courriers |
| Vérifier sur place les lignes du corridor : arrêts, tracés, prix payés, fréquences à la pointe | Une mission courte rémunérée (1 ou 2 personnes, 2 à 3 semaines), avec les fiches déjà prêtes | Budget à fixer |
| Intégrer les relevés, corriger les noms d'arrêts, retirer les lignes disparues | Moi | Quelques jours |
| Régler le moteur : écarter les options absurdes, tester sur 200 trajets de référence | Moi | Quelques jours |

### 2. Le nom et le cadre légal

| Tâche | Qui |
|-------|-----|
| Vérifier « yafohi » : sens auprès d'Abidjanais, marque à l'OAPI, noms de domaine, magasins d'applis, réseaux sociaux | Vous |
| Avis juridique écrit ou déclaration à l'ARTCI, avant toute donnée personnelle (position, numéro) | Vous, avec un juriste ; je fournis le dossier préparé (PRIVACY.md) |
| Choisir un fond de carte et une vue satellite sous licence commerciale | Moi, après votre accord sur le budget |

### 3. L'appli elle-même

| Tâche | Qui |
|-------|-----|
| Trancher la technique de l'appli (ADR-001), en tenant compte de « en ligne d'abord » | Moi, avec une recommandation simple à valider |
| Construire les écrans de la maquette yafohi dans la vraie appli Android | Moi |
| Mettre en ligne le serveur : itinéraires, recherche de lieux, signalements (hébergement, ADR-004) | Moi, après votre choix d'hébergeur |
| Recherche de tous les lieux d'Abidjan (33 000 lieux d'OpenStreetMap déjà importés), avec les noms tels qu'on les dit | Moi |
| Signalements des usagers : ligne disparue, arrêt déplacé, prix payé, affluence. C'est ce qui rend l'appli vivante | Moi, et les usagers |
| Hors connexion : trajets enregistrés et temps habituels | Moi |
| Voix et pas à pas audio, pour ceux qui lisent difficilement | Moi |

### 4. Tester, puis lancer

| Tâche | Qui |
|-------|-----|
| Tester la maquette avec 5 à 8 personnes, dont des personnes qui lisent difficilement et une personne âgée | Une personne sur place, avec mon protocole |
| Pilote fermé : 50 usagers sur le corridor pendant quelques semaines | Vous, pour recruter ; moi, pour suivre les chiffres |
| Compte développeur Google Play, fiche de l'appli, politique de confidentialité | Vous, pour le compte ; moi, pour les textes |
| Bêta ouverte sur le corridor, puis extension à d'autres quartiers | Ensemble |

## Le point qui bloque le plus

Sans une vérification sur place, même courte, l'appli proposera des lignes de 2023 dont une partie a disparu. Les étapes 1 et 2 ne coûtent qu'un courrier. La mission courte de l'étape 1 est la seule dépense qui conditionne tout le reste.
