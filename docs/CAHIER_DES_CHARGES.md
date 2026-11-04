<!-- Source : « Prompt pour le LLM » (.docx) reçu le 2026-11-04, converti en Markdown sans modification du fond. -->
<!-- Document de référence du projet. Toute modification passe par une décision explicite du porteur du projet. -->

# Prompt pour le LLM

**Mode d'emploi.** Copie tout ce qui se trouve sous la ligne de séparation et envoie-le en un seul message à ton LLM, idéalement un assistant de code qui peut créer des fichiers (Claude Code, Cursor ou équivalent). Tu peux aussi exporter cet onglet en Markdown et joindre le fichier. Remplace {{NOM_APP}} par le nom choisi. Le LLM est censé travailler par phases : réponds à ses questions, puis demande-lui de passer à la phase suivante.

## Partie 1 — Ton rôle, ta mission, ta méthode

### 1.1 Qui tu es

Tu agis comme une équipe produit et ingénierie complète, riche de plusieurs décennies d'expérience cumulée dans les transports publics des pays émergents, les applications mobiles grand public à faible bande passante et les systèmes temps réel. Pour chaque décision importante, tu raisonnes successivement avec ces casquettes :

- **Product manager** : quel problème, pour qui, quelle valeur, quelle priorité.

- **Chercheur UX et designer** : usagers peu ou pas alphabétisés, petits écrans, plein soleil, une seule main libre, foule, bruit.

- **Architecte logiciel et tech lead** : structure, compromis, dette technique, réversibilité.

- **Ingénieur mobile** : Android d'entrée de gamme, batterie, mémoire, réseau instable.

- **Ingénieur backend et temps réel** : flux d'événements, cohérence, montée en charge aux heures de pointe.

- **Data scientist et ingénieur transport** : GTFS, RAPTOR, modélisation des files d'attente, prévision, calibration.

- **Ingénieur géomatique** : OpenStreetMap, PostGIS, tuiles vectorielles, géocodage.

- **Expert sécurité et vie privée** : loi ivoirienne n°2013-450, ARTCI, OWASP.

- **QA et SRE / DevOps** : tests, observabilité, déploiement, coûts d'exploitation.

Quand ces casquettes sont en désaccord, rends le désaccord explicite, puis tranche avec une justification écrite.

### 1.2 Ta mission

Concevoir et construire **{{NOM_APP}}**, une solution d'abord mobile qui réduit le temps que les Ivoiriens perdent à attendre et à chercher un transport en commun, en priorité les personnes qui n'ont pas de véhicule personnel et ne peuvent pas payer un VTC chaque jour. Ce n'est pas un concurrent de Yango. La solution tient trois promesses :

1.  **« Dis-moi où tu vas, je te dis comment y aller. »** L'usager saisit sa destination ; l'appli lui dit quelle gare ou quel arrêt rejoindre, quel véhicule prendre et comment le reconnaître, où changer, où descendre, combien prévoir en FCFA et combien de temps il attendra. Elle propose au minimum l'option la moins chère, la plus rapide et la plus simple.

2.  **« Montre-moi ce qui circule et où ça attend, maintenant. »** Une carte en temps réel des véhicules de transport public, classés par catégorie, et de l'état des files d'attente dans les gares.

3.  **« Aide les chauffeurs à aller là où on les attend. »** Les chauffeurs et apprentis voient où les passagers attendent, ce qui réduit l'attente des deux côtés.

La mesure du succès est le nombre de minutes d'attente et de trajet épargnées aux usagers, pas le nombre de téléchargements.

### 1.3 Règles non négociables

1.  **N'invente jamais de données réelles** : lignes, gares, prix, fréquences, horaires, noms de personnes, numéros de téléphone. Pour développer et tester, crée un jeu de données nommé fixtures_fictives, dont chaque enregistrement porte is_fictional = true, et affiche un bandeau « DONNÉES FICTIVES » dans les builds de développement. Les vraies données viennent uniquement des sources de la partie 7.

2.  **Toute estimation montrée à l'usager affiche sa fraîcheur et son niveau de confiance.** Jamais de fausse précision.

3.  **Inclusion d'abord** : chaque fonctionnalité doit marcher sur Android 8.0 avec 2 Go de RAM et en 3G instable, et rester utilisable hors ligne pour ce qui a été préchargé. Si ce n'est pas possible, la fonctionnalité est marquée « dégradable » et possède un mode dégradé documenté.

4.  **Vie privée dès la conception** : collecte minimale, consentement explicite, anonymisation, conformité à la loi n°2013-450.

5.  **Pas de manipulation** : pas de dark patterns, pas de publicité intrusive, pas de collecte inutile, pas de notifications abusives.

6.  **Livrables exécutables** : du code qui compile, testé et documenté. Pas de pseudo-code dans les livrables finaux, sauf demande explicite.

7.  **Quand une information manque**, pose la question si elle est bloquante ; sinon, pose une hypothèse explicite, note-la dans docs/HYPOTHESES.md et avance.

8.  **Ne simplifie jamais une exigence de ce document sans le signaler**, avec la raison et le plan pour y revenir.

### 1.4 Ta méthode de travail

- **Travaille par phases** (partie 15). À la fin de chaque phase, livre : ce qui a été fait, comment le lancer, les tests et leur résultat, les limites connues, la prochaine étape. Attends ma validation avant de passer à la phase suivante.

- **Ton premier message** contient : (a) ta reformulation du besoin en dix lignes maximum ; (b) au plus dix questions vraiment bloquantes ; (c) les hypothèses par défaut que tu retiens pour tout le reste ; (d) le plan détaillé de la phase 0.

- **Tiens à jour ces documents dans le dépôt** : README.md, docs/ARCHITECTURE.md, docs/DECISIONS/ADR-NNN-titre.md (une décision d'architecture par fichier), docs/HYPOTHESES.md, docs/DATA.md, docs/PRIVACY.md, docs/ETAT.md et CHANGELOG.md.

- **Chaque décision structurante** documente les options envisagées, les compromis, le coût, la réversibilité et la raison du choix.

- **Avance par petits incréments** : chaque incrément compile, passe ses tests et laisse l'intégration continue au vert.

- **Si ta fenêtre de contexte arrive à saturation**, résume l'état exact du projet dans docs/ETAT.md pour qu'une nouvelle session puisse reprendre sans perte.

- **Langues** : code, identifiants et commentaires techniques en anglais ; textes visibles par l'usager en français, via des clés de traduction ; documentation en français.

## Partie 2 — Le contexte ivoirien en faits

Ces faits viennent de sources publiées entre 2018 et 2026 (AMUGA, CODATU, Banque mondiale, presse ivoirienne, ARTCI). Ils servent à dimensionner et à concevoir ; ne les affiche jamais à l'usager comme des vérités actuelles, et considère-les comme à revérifier sur le terrain.

### 2.1 La demande

- Le Grand Abidjan compte 19 communes ; le District comptait 6,3 millions d'habitants au recensement de 2021, en hausse de 34,3 % depuis 2014, avec un fort étalement vers Abobo, Yopougon, Anyama, Bingerville et Songon.

- Environ 17 millions de déplacements par jour en 2020, dont 7,25 millions en transport en commun. La marche et les transports collectifs pèsent chacun plus de 40 % des déplacements.

- Un ménage fait en moyenne 6,09 déplacements par jour ouvrable, d'environ 33 minutes chacun attente comprise, pour 1 075 FCFA par jour. Les ménages pauvres font 60 % de leurs déplacements à pied, souvent faute d'offre abordable.

- Le transport coûte aux ménages d'Abidjan environ 4,1 milliards de FCFA par jour.

### 2.2 L'offre

- **Transport artisanal (environ 80 % des voyages en commun, plus de 5 millions de voyageurs par jour)** :

  - **Gbakas** : minibus de 18 à 32 places (environ 8 000 en 2018). Ils chargent dans des gares informelles et partent quand ils sont pleins. L'apprenti crie la destination et le prix (« Adjamé Liberté 300 F ! »). Le chauffeur doit reverser 20 000 à 30 000 FCFA par jour au propriétaire, d'où une forte incitation à remplir vite et à augmenter les prix aux heures de pointe.

  - **Wôrô-wôrôs** : taxis collectifs de 4 passagers, à itinéraire et prix forfaitaires, communaux ou intercommunaux. Couleur par commune selon la presse de 2021 (à vérifier sur le terrain) : bleu à Yopougon, jaune à Cocody, vert à Adjamé, Attécoubé, Marcory et Koumassi, beige à bandes marron à Abobo, jaune à bas de caisse bleu à Port-Bouët. Yopougon compterait à lui seul près de 6 500 wôrô-wôrôs.

  - **Motos-taxis et tricycles** en périphérie d'Abidjan ; dominants à Bouaké et Korhogo.

  - Des syndicats, chefs de gare et « coxers » organisent le chargement et prélèvent des frais sur les véhicules.

- **SOTRA** (bus et bateaux-bus, entreprise publique) : environ 1 million de voyageurs par jour, environ 68 lignes urbaines dont une douzaine d'express et 3 lignes lagunaires selon une source secondaire. Ticket à 200 FCFA (Monbus) et 500 FCFA (Express) selon son communiqué de juillet 2024. Billettique MonPass ; application Sotra Mobile depuis décembre 2025 (carte virtuelle, QR/NFC, recharge mobile money, suivi des bus).

- **Lagunaire** : environ 100 000 à 120 000 voyageurs par jour (bateaux-bus SOTRA, STL, CITRANS, pinasses), objectif de 530 000 avec 25 pôles lagunaires.

- **Taxis** : environ 10 000 taxis-compteurs déclarés et 19 000 non déclarés. **VTC** : Yango, Heetch, InDrive, Uber, avec des prix dynamiques jugés trop chers pour l'usage quotidien.

- **Prix artisanaux** : généralement entre 100 et 500 FCFA par trajet, mais ils varient avec l'heure, la pluie, les fêtes et le carburant (super à 905 FCFA et gasoil à 725 FCFA le litre depuis août 2026). Des doublements sont rapportés. Paiement surtout en espèces, avec un manque fréquent de monnaie ; des QR codes Wave ou Orange Money apparaissent dans les wôrô-wôrôs.

### 2.3 Les irritants

- Files d'attente de plus d'une heure, parfois deux, aux heures de pointe ; véhicules rares pendant les pluies ; congestion chronique.

- Information voyageur quasi inexistante : on se renseigne auprès du chauffeur ou des autres passagers.

- Prix opaques et changeants ; peur de se tromper de véhicule quand on ne connaît pas le réseau.

- Insécurité routière et sentiment d'insécurité, en particulier pour les femmes et le soir.

### 2.4 Le réseau change

- **Ligne 1 du métro** : 37,4 km d'Anyama à l'aéroport, plus de 500 000 voyageurs par jour, mise en service annoncée entre fin 2028 et 2029.

- **BRT Yopougon–Bingerville** : bus électriques en site propre, 300 000 à 500 000 voyageurs par jour, prévu en 2028.

- **Projet AIM** : 32 pôles d'échanges et 180 points d'arrêt ; arrêts-minute et têtes de stationnement pour gbakas et wôrô-wôrôs.

- **AMUGA** (autorité organisatrice des 19 communes) : prépare billettique interopérable, système d'aide à l'exploitation et d'information voyageur, observatoire de la mobilité et poste central de régulation ; anime un groupe de travail de la mobilité dans chaque commune avec syndicats, chauffeurs et gestionnaires de gare ; a lancé en octobre 2026 une réorganisation du transport artisanal.

- Les règles changent vite : les gbakas ont été interdits d'entrer dans Adjamé en mars 2025, par exemple. L'appli doit absorber ces changements en quelques heures.

### 2.5 Ce qui existe déjà

- **AMUGA mon trajet** (2022) : itinéraires statiques bus, gbaka, wôrô-wôrô, bateau-bus, et signalements.

- **Sotra Mobile** (2025) : billettique et suivi des bus SOTRA uniquement.

- **Traaf** de Kaanari (août 2026) : itinéraires bus, gbaka et wôrô-wôrô, questions en langage courant à l'écrit ou à la voix. C'est le concurrent le plus proche.

- **Sanouka** (bêta, cartographie), **KEBE** (covoiturage), **eWarren** (paiement en wôrô-wôrô à Cocody).

- **Données ouvertes** : cartographie du réseau d'Abidjan dans OpenStreetMap réalisée à partir de 2019 par Jungle Bus pour le ministère des Transports avec l'AFD ; fichier GTFS « Abidjan 2023 » de DigitalTransport4Africa (mis à jour en janvier 2024), qui décrit notamment les réseaux de gbakas et de wôrô-wôrôs par commune, disponible sur le TUMI Data Hub et Transitland.

Ton avantage concurrentiel doit venir de ce que personne ne fait : le temps réel du transport artisanal, l'attente estimée, les prix observés, le signal de demande pour les chauffeurs et l'accès sans smartphone.

### 2.6 L'environnement numérique et social

- 53,6 millions de cartes SIM actives en 2024, mais seulement 13,4 millions d'internautes fin 2025 (40,7 % de la population) et environ 40 % de détenteurs de smartphone ; le gouvernement vise 80 % fin 2027.

- La data coûte cher : environ 1 000 à 1 800 FCFA le Go, pour un SMIG de 75 000 FCFA.

- Près de 50 millions de comptes mobile money (Wave, Orange Money, MTN MoMo, Moov Money).

- Analphabétisme de 43,7 % en 2019. À Abidjan, le français domine ; le dioula est la principale langue véhiculaire ; le nouchi imprègne le parler urbain.

- Saisons des pluies d'avril à juillet et de septembre à novembre ; inondations meurtrières récurrentes, comme les 28 et 29 juin 2026.

- Interurbain : les compagnies (UTB et autres) sont concentrées à la gare routière d'Adjamé.

- Numéros d'urgence : police 110, 111 ou 170 ; sapeurs-pompiers 180 ; SAMU 185.

- Cadre légal : loi n°2013-450 du 19 juin 2013 sur les données personnelles, contrôlée par l'ARTCI (déclaration ou autorisation préalable, y compris pour la géolocalisation) ; loi n°2013-451 sur la cybercriminalité.

## Partie 3 — Vision produit, principes et non-objectifs

### 3.1 Vision

« Plus personne en Côte d'Ivoire ne perd une heure au bord de la route sans savoir. » {{NOM_APP}} devient le réflexe de chaque usager avant de quitter la maison, de chaque apprenti avant de choisir sa gare, et la source de données de référence sur la mobilité réelle pour les autorités.

### 3.2 Le vrai problème à résoudre

Le temps perdu ne vient pas seulement du manque de véhicules. Il vient d'une **asymétrie d'information des deux côtés** : les passagers ne savent pas quel véhicule passe où, à quel prix et dans combien de temps ; les chauffeurs ne savent pas où les passagers attendent. Résultat : des files de passagers à un endroit, des véhicules qui tournent à vide ailleurs, et des usagers qui choisissent au hasard.

### 3.3 Proposition de valeur

| Pour qui                               | Ce que {{NOM_APP}} apporte                                                                                                                       |
|----------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| Usager quotidien                       | Le trajet le moins cher ou le plus rapide, l'attente probable, le prix à prévoir, l'alerte au bon moment ; moins de stress, moins de temps perdu |
| Usager occasionnel ou nouvel arrivant  | Comprendre un réseau sans plan : quelle gare, quel véhicule, comment le reconnaître, quoi dire à l'apprenti                                      |
| Usager sans smartphone                 | Une réponse par WhatsApp, SMS, USSD ou appel vocal                                                                                               |
| Chauffeur et apprenti                  | Savoir où sont les passagers, remplir plus vite, rouler moins à vide                                                                             |
| Chef de gare                           | Un outil simple pour annoncer départs, files et changements                                                                                      |
| Autorités (AMUGA, communes, ministère) | Des données agrégées et anonymes sur la demande, l'attente et la fiabilité, pour décider                                                         |

### 3.4 Principes de conception

1.  **L'utile en 10 secondes** : depuis l'ouverture de l'appli jusqu'à la première recommandation exploitable, en moins de 10 secondes sur un téléphone d'entrée de gamme.

2.  **Hors ligne par défaut** : l'appli reste utile sans réseau ; le temps réel est un bonus qui enrichit, pas une condition.

3.  **Sobriété data** : chaque octet a un coût pour l'usager ; tout est compressé, mis en cache, différentiel.

4.  **Honnêteté** : toujours montrer la fraîcheur, la source et l'incertitude ; afficher des fourchettes plutôt que de faux chiffres exacts.

5.  **Parler comme les gens** : noms de lieux et repères tels qu'on les dit à Abidjan, phrases courtes, icônes, voix.

6.  **Les usagers sont aussi les capteurs** : contribuer doit prendre une ou deux pressions sur l'écran, et rapporter quelque chose.

7.  **Gagnant-gagnant avec les transporteurs** : l'appli aide gbakas et wôrô-wôrôs à mieux travailler ; elle ne les dénonce pas et ne les remplace pas.

8.  **Multimodal et multi-villes dès le modèle de données**, même si le lancement se fait sur un seul corridor d'Abidjan.

9.  **Prêt pour le métro et le BRT** : ils s'intègrent comme des lignes structurantes, avec le transport artisanal en rabattement.

10. **Sûreté** : aucune fonctionnalité ne doit inciter à manipuler son téléphone en conduisant, ni exposer la position d'une personne identifiable.

### 3.5 Non-objectifs (à ne pas construire, au moins au départ)

- Pas de VTC ni de commande de course individuelle ; pas de tarification dynamique imposée par l'appli.

- Pas de réservation de place ni de paiement intégré dans le MVP (l'architecture doit les permettre plus tard).

- Pas de signalement des contrôles de police : risque juridique et conflit avec les autorités, dont on a besoin comme partenaires.

- Pas de notation nominative des chauffeurs ni de publication de plaques d'immatriculation : risque de diffamation, de conflit et de rejet par la profession.

- Pas de réseau social, de fil d'actualité ou de messagerie entre usagers.

- Pas de publicité ciblée sur des données personnelles.

### 3.6 Indicateur phare

**Minutes d'attente évitées par semaine**, estimées à partir de la différence entre l'attente prévue sur l'option choisie et l'attente médiane historique du même trajet sans conseil, puis validées par sondage après trajet. Les indicateurs secondaires sont détaillés en partie 14.

## Partie 4 — Utilisateurs, personas et parcours clés

Les personas ci-dessous sont des archétypes fictifs construits à partir de la recherche. Utilise-les pour arbitrer chaque écran et chaque fonctionnalité : « Est-ce que Awa peut s'en servir ? Est-ce que Mamadou est exclu ? »

### 4.1 Personas

| Persona                                                    | Profil                                                  | Téléphone et data                                               | Ce qui compte pour elle ou lui                                               | Risque d'exclusion                                                       |
|------------------------------------------------------------|---------------------------------------------------------|-----------------------------------------------------------------|------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| **Awa**, 24 ans, vendeuse au marché d'Adjamé, habite Abobo | Part à 5 h, rentre à la nuit tombée ; lit difficilement | Android d'entrée de gamme 2 Go, forfait de 500 FCFA par semaine | Le prix d'abord, puis l'attente ; utilise surtout les notes vocales WhatsApp | Textes longs, data, écrans complexes                                     |
| **Koffi**, 35 ans, comptable au Plateau, habite Yopougon   | Horaires fixes, retards sanctionnés                     | Smartphone de milieu de gamme, 4G                               | Fiabilité et temps ; prêt à payer un peu plus (bateau-bus, express)          | Peu ; impatient si l'info est fausse                                     |
| **Fatou**, 19 ans, étudiante à Cocody, habite Port-Bouët   | Budget très serré, cours tardifs                        | Android partagé avec sa sœur                                    | Coût, sécurité le soir, trajets simples                                      | Sécurité, data                                                           |
| **Mamadou**, 58 ans, commerçant à Treichville              | Parle surtout dioula, lit peu le français               | Téléphone basique sans internet                                 | Savoir quel gbaka prendre pour un nouveau fournisseur                        | Totalement exclu d'une appli seule : canaux USSD, SMS, vocal             |
| **Serge**, chauffeur de gbaka, et **Junior**, son apprenti | Doivent verser la recette quotidienne au propriétaire   | Un smartphone bas de gamme pour deux                            | Remplir vite, moins de trajets à vide, moins de carburant perdu              | Méfiance (« c'est pour nous fliquer ? »), aucune manipulation en roulant |
| **Bakary**, chef de gare                                   | Organise l'ordre de chargement, connaît tout le monde   | Smartphone simple                                               | Reconnaissance, outil simple, éviter les conflits                            | Peur de perdre du pouvoir ou des revenus                                 |
| **Aïcha**, analyste à l'AMUGA                              | Prépare la restructuration du réseau                    | Ordinateur                                                      | Données agrégées fiables, exportables                                        | Données personnelles : doit n'avoir que de l'agrégé                      |
| **Jean**, nouvel arrivant venu de Bouaké                   | Ne connaît pas Abidjan                                  | Smartphone récent                                               | Comprendre le réseau, ne pas se faire arnaquer sur le prix                   | Vocabulaire local inconnu                                                |
| **Mariam**, 45 ans, se déplace avec une canne              | Marche difficilement                                    | Android moyen                                                   | Moins de marche, moins de changements, véhicules accessibles                 | Itinéraires « optimaux » mais épuisants                                  |

### 4.2 Parcours clés à concevoir et tester

1.  **Planifier le trajet du matin.** Awa ouvre l'appli à 4 h 50, tape ou dit « Adjamé marché ». L'appli propose : « Le moins cher : 300 F, gbaka depuis la gare X à 6 min à pied, attente estimée 10 à 20 min ». Elle lance le trajet et reçoit une alerte avant de descendre.

2.  **Arrivée à une gare saturée.** Koffi arrive à la gare : la file est longue. L'appli le savait (« file très longue, signalée il y a 4 min par 6 personnes ») et propose : « Marche 9 min jusqu'à l'arrêt Y, prends le bateau-bus : tu gagnes environ 25 min pour 200 F de plus ».

3.  **Attendre au bord de la route.** Fatou est à un arrêt informel en milieu de ligne ; les gbakas passent pleins. L'appli estime l'attente à 25 à 40 min et suggère de « remonter » à la gare de départ à 7 min à pied, où l'attente est de 5 à 10 min.

4.  **Pendant le trajet.** Le suivi détecte qu'Awa est à bord, lui annonce l'arrêt suivant à voix haute et vibre 2 arrêts avant sa descente.

5.  **Contribuer en deux pressions.** En attendant, Koffi touche « Je suis dans la file », puis « Beaucoup de monde ». À la montée, l'appli lui demande en une pression « Tu as payé combien ? ».

6.  **Le chauffeur cherche des passagers.** Serge passe en mode « En service ». La carte lui montre qu'une file importante attend à la gare Z, à 2 km ; il y va et remplit en 5 minutes.

7.  **Sans smartphone.** Mamadou compose un code USSD, choisit sa commune, sa gare de départ et sa destination ; il reçoit un SMS : « Gbaka Treichville-Adjamé, gare X, 200 F. Puis gbaka Adjamé-Abobo, 250 F. »

8.  **Jour de pluie.** Une inondation est signalée sur un carrefour clé. L'appli recalcule les itinéraires de ceux qui suivent un trajet, prévient que les prix sont souvent plus élevés pendant la pluie et propose le lagunaire s'il est plus sûr.

9.  **Retour de nuit.** Fatou partage son trajet avec sa mère par un lien WhatsApp léger ; l'itinéraire privilégie les arrêts signalés comme éclairés et fréquentés.

10. **Le réseau change.** La commune interdit l'accès d'une zone aux gbakas. Un contributeur le signale, un modérateur valide, et les itinéraires sont corrigés dans l'heure.

## Partie 5 — Fonctionnalités usager

Chaque fonctionnalité a un identifiant, une priorité (**MVP**, **V2** ou **V3**, voir partie 15) et des critères d'acceptation vérifiables. Les durées de performance s'entendent sur un téléphone de référence Android 8, 2 Go de RAM, en 3G simulée (débit 750 kbit/s, latence 300 ms), sauf mention contraire.

### F-01 Saisir sa destination (MVP)

- Champ unique « Tu vas où ? » ; saisie texte, dictée vocale, choix sur la carte, lieux enregistrés (Maison, Boulot, École), historique, et « position partagée » reçue par WhatsApp ou SMS.

- Recherche par **repères** tels qu'on les dit : carrefours, pharmacies, églises, mosquées, maquis, marchés, gares, terminus, écoles (« carrefour Siporex », « derrière la pharmacie Y », « Adjamé Liberté »).

- Tolérance aux fautes, aux abréviations et aux variantes orales (« Sipo », « Yop », « Adj », « Koum »), aux accents et à leur absence.

- Départ par défaut : position GPS ; sinon dernier lieu connu ; sinon choix rapide de la commune et du quartier.

- **Critères** : suggestions affichées en moins de 300 ms hors ligne pour les lieux de la ville préchargée ; au moins 90 % de réussite au premier essai sur un jeu de 300 requêtes réelles collectées en phase 0 ; un lieu introuvable peut être ajouté par l'usager en trois pressions (nom, photo facultative, position).

### F-02 Calculer des itinéraires (MVP)

- Trois options étiquetées au minimum : **« Le moins cher »**, **« Le plus rapide »**, **« Le plus simple »** (moins de changements et de marche) ; plus **« Le plus sûr »** le soir (V2).

- Chaque option affiche : durée totale en fourchette (médiane et 80e centile), attente estimée, coût total en fourchette (FCFA), nombre de changements, minutes de marche, fiabilité, date de la dernière donnée temps réel utilisée.

- Comparaison avec le taxi-compteur et le VTC : « Économie estimée : 2 100 F par rapport à un VTC ».

- Options « Partir maintenant », « Partir à… », « Arriver avant… » ; préférences : marche maximale, budget maximal, éviter un mode (gbaka, lagune, moto), moins de changements, accessibilité.

- **Critères** : réponse en ligne en moins de 2 s au 95e centile côté serveur ; calcul hors ligne de secours en moins de 3 s sur le téléphone de référence avec les données préchargées et les attentes historiques ; aucun itinéraire proposé sans source de données identifiée ; sur la suite de 200 trajets de référence validés par des locaux (partie 14), au moins 85 % des options proposées jugées réalistes.

### F-03 Fiche itinéraire pas à pas (MVP)

- Étapes en phrases courtes avec icône et lecture vocale : « Marche 4 min jusqu'à la gare Siporex, à côté de \[repère\] » ; « Prends un gbaka “Adjamé Liberté” : l'apprenti crie “Adjamé Liberté !” » ; « Prévois 300 F, souvent 400 F aux heures de pointe ; prépare la monnaie » ; « Descends à \[repère\] : on te prévient ».

- **Comment reconnaître le véhicule** : type, couleur par commune, panneau ou inscription, photo de la gare et du point de montée quand elle existe.

- Mini-carte schématique ; bouton « Partager ce trajet » (lien léger lisible sans appli).

- **Critères** : chaque étape tient en deux lignes maximum sur un écran de 5 pouces ; chaque étape possède une version audio ; la fiche s'ouvre hors ligne si l'itinéraire a été calculé ou enregistré.

### F-04 Suivre son trajet (MVP)

- Bouton « Je pars » : guidage actif, détection de la montée et de la descente (partie 8), annonce de l'arrêt suivant, vibration et voix deux arrêts avant la descente, puis à l'arrêt.

- Recalcul automatique si la file est trop longue, si le véhicule dévie ou en cas d'incident ; proposition, jamais imposition.

- **Critères** : alerte de descente déclenchée au bon arrêt dans au moins 95 % des cas lors des tests terrain ; consommation de batterie inférieure à 4 % par heure de suivi sur le téléphone de référence ; consommation data inférieure à 300 Ko par heure de suivi ; arrêt automatique du suivi à destination ou après 20 min d'immobilité inattendue, avec confirmation.

### F-05 Carte en temps réel (MVP pour les gares et incidents, V2 pour les véhicules)

- Catégories de véhicules avec icône, forme et couleur distinctes (jamais la couleur seule) : bus SOTRA, bus express, bateau-bus et pinasse, gbaka, wôrô-wôrô communal, wôrô-wôrô intercommunal, taxi-compteur, moto-taxi (villes concernées), car interurbain ; métro et BRT dès leur mise en service.

- Filtres par catégorie et par ligne ; légende toujours accessible.

- **Niveaux de certitude visibles** : icône pleine pour une position GPS récente ; icône estompée pour une position estimée ; « vu il y a 6 min » sinon. Disparition après un délai défini par catégorie.

- Gares et arrêts avec état de la file (vert, orange, rouge, gris si inconnu) et attente estimée.

- Couche congestion (vitesses mesurées), couche incidents (accident, inondation, route barrée, travaux, manifestation), zones inondables connues pendant les saisons des pluies.

- **Critères** : seules les mises à jour de la zone visible sont téléchargées ; rafraîchissement toutes les 10 à 15 s au premier plan, arrêt en arrière-plan ; moins de 150 Ko par minute de carte active ; 30 images par seconde au défilement sur le téléphone de référence avec 200 marqueurs.

### F-06 Fiche gare et arrêt (MVP)

- Lignes et destinations desservies, prix observés par destination, horaires d'activité, état actuel de la file et des véhicules présents, attente estimée, graphique « meilleure heure pour partir » par jour de la semaine, photos, accessibilité, éclairage le soir.

- **Critères** : l'état actuel affiche toujours sa fraîcheur ; au-delà de 30 min sans signalement, il bascule sur l'estimation historique, présentée comme telle.

### F-07 Contribuer en une ou deux pressions (MVP)

- En gare : « Je suis dans la file » ; taille de la file (peu, moyen, beaucoup, très long) ; véhicules présents (aucun, 1 à 2, 3 et plus) ; « Je viens de monter ».

- À bord : « J'ai payé combien ? » (montants usuels proposés en boutons) ; « Le véhicule est plein ».

- Partout : incident, arrêt déplacé, ligne déviée, prix anormal, nouveau lieu, photo de gare.

- Micro-sondage après trajet : « Tu as attendu combien ? » en un geste.

- **Critères** : chaque contribution prend au plus deux pressions et se fait d'une main ; les contributions sont mises en file hors ligne et envoyées dès que le réseau revient ; aucune contribution n'est demandée pendant que le téléphone détecte une conduite.

### F-08 Alertes et notifications (MVP pour les trajets suivis, V2 pour le reste)

- Trajets réguliers : l'usager programme « tous les jours ouvrables à 6 h 30, Maison vers Boulot » ; il reçoit 15 min avant un résumé : attente actuelle, meilleure option, incidents.

- Alertes pluie et inondation sur ses trajets ; perturbations de lignes suivies.

- **Critères** : au plus 3 notifications non demandées par semaine ; chaque type désactivable en un geste.

### F-09 Quand partir (V2)

- « Si tu pars à 6 h 10 au lieu de 6 h 30, tu attends environ 20 min de moins » à partir des attentes historiques et des prévisions météo.

### F-10 Budget transport (V2)

- Estimation du coût mensuel des trajets réguliers selon l'option choisie ; comparaison avec l'abonnement SOTRA quand il existe (dont les tarifs réduits comme la Carte Jeunes) et avec le VTC.

### F-11 Sécurité personnelle (MVP pour le partage et le bouton d'urgence, V2 pour le reste)

- Partage de trajet en direct par lien WhatsApp ou SMS, sans appli côté destinataire ; fin automatique à l'arrivée.

- Bouton d'urgence : appel direct à la police (110, 111, 170), aux pompiers (180) ou au SAMU (185), et envoi de la position à un contact choisi.

- Signalement anonyme de harcèlement ou d'agression, agrégé par zone et par tranche horaire, sans désigner de personne.

- Mode nuit : privilégier les arrêts signalés comme éclairés et fréquentés.

### F-12 Hors ligne et économie de data (MVP)

- Pack ville téléchargeable (réseau, repères, attentes historiques, fond de carte léger), proposé en Wi-Fi, avec mises à jour différentielles.

- Mode « économie de data » : carte sans fond détaillé, listes et texte, images désactivées.

- Compteur de data consommée par l'appli, visible dans les réglages.

- **Critères** : pack ville d'Abidjan sans fond de carte inférieur à 15 Mo ; avec fond de carte léger, inférieur à 60 Mo ; mise à jour quotidienne différentielle inférieure à 300 Ko.

### F-13 Compte et préférences (MVP)

- Aucun compte obligatoire pour chercher un itinéraire. Compte facultatif par numéro de téléphone avec code SMS, nécessaire pour les récompenses et la synchronisation.

- Préférences : langue, voix, taille du texte, contraste, modes à éviter, marche maximale, budget, accessibilité.

### F-14 Récompenses (V2)

- Points pour les contributions **validées** uniquement ; échange contre de la data ou du crédit via des partenaires opérateurs, ou de petites sommes en mobile money ; badges par commune.

- **Critères** : aucune récompense pour une contribution non validée ; plafonds quotidiens ; détection de fraude (partie 7).

### F-15 Interurbain (V3)

- « Je vais à Bouaké » : quelle gare de compagnie rejoindre à Adjamé ou ailleurs, comment y aller, compagnies, départs connus et prix observés.

### F-16 Accessibilité physique (V2)

- Profil « mobilité réduite » : minimiser marche, escaliers, passerelles et changements ; signaler les véhicules accessibles (par exemple les nouveaux bus équipés de rampe) quand l'information existe.

## Partie 6 — Les autres faces du produit

### 6.1 {{NOM_APP}} Pro : chauffeurs et apprentis (V2, pilote en fin de MVP)

Objectif : que les chauffeurs de gbaka et de wôrô-wôrô aient un intérêt direct à partager leur position, ce qui alimente la carte en temps réel pour tous.

- **Même application avec un mode Pro** activable, ou application séparée ultra-légère si les tests montrent que c'est mieux ; à décider par un ADR.

- **Passage « En service »** : choix de la ligne habituelle et du sens, ou « ligne libre » ; partage de position uniquement pendant le service, avec un indicateur permanent et un arrêt en un geste.

- **Carte de la demande** : files signalées dans les gares et aux arrêts proches, sur la ligne et autour (« Gare X : beaucoup de monde, 1 gbaka présent, signalé il y a 3 min »).

- **Sûreté au volant** : au-dessus de 10 km/h, l'écran passe en lecture seule avec annonces vocales ; aucune saisie possible ; les interactions sont pensées pour l'apprenti, pas pour le chauffeur.

- **Bénéfices concrets** : récapitulatif de journée (trajets, distance, temps à vide estimé), conseils de gare la plus demandée par tranche horaire, points convertibles en data ou crédit, priorité d'accès à de futurs services (paiement numérique des passagers, formation, assurance via partenaires).

- **Confiance** : la position n'est jamais partagée hors service ; elle n'est jamais vendue ; elle n'est jamais transmise à des tiers sans obligation légale formelle ; l'usager du grand public voit un véhicule anonyme sur la ligne, jamais une plaque ou un nom.

- **Critères** : moins de 3 % de batterie par heure de service ; moins de 1 Mo de data par heure ; fonctionnement sur un Android 8 d'entrée de gamme partagé entre deux personnes.

### 6.2 Console de gare (V2)

Pour les chefs de gare et gestionnaires volontaires, avec leur accord et celui des organisations concernées.

- Mise à jour en quelques pressions : véhicules en chargement, file de passagers, prochain départ estimé, destinations actives, prix du moment, gare fermée ou déplacée.

- Messages diffusés aux usagers abonnés à la gare (« Ligne suspendue jusqu'à 14 h »).

- Statistiques de fréquentation de la gare, utiles aux syndicats et aux communes.

- Statut « source vérifiée » qui donne plus de poids à ces contributions dans les estimations (partie 7).

### 6.3 Back-office d'administration et de curation (MVP)

Application web interne, protégée par authentification forte et rôles.

- **Éditeur de réseau** sur carte : lignes, variantes d'itinéraire, gares, arrêts formels et zones de montée informelles, prix, horaires d'activité, couleurs et repères de reconnaissance des véhicules.

- **Versionnement** du réseau : toute modification passe par proposition, revue, publication ; historique, comparaison et retour arrière ; date d'effet ; export et import GTFS ; validation automatique avec le validateur GTFS canonique de MobilityData.

- **File de modération** des contributions : doublons, incohérences, signalements suspects, photos ; actions groupées ; raison obligatoire en cas de rejet.

- **Gestion des incidents** et des messages diffusés ; programmation des perturbations connues (travaux, événements).

- **Tableaux de bord qualité des données** : fraîcheur par gare et par ligne, couverture des trajets fréquents, précision des estimations d'attente, taux de contributions rejetées, anomalies.

- **Gestion des sources** : flux partenaires (GTFS, GTFS-Realtime), état et dernière synchronisation.

- **Rôles** : administrateur, curateur de données, modérateur, analyste, partenaire en lecture seule ; journal d'audit de toute action.

### 6.4 Portail partenaires et autorités (V3)

- Tableaux de bord agrégés : matrices origine-destination, attentes moyennes par gare et tranche horaire, fiabilité par ligne, impacts des pluies et des incidents.

- Exports et API pour l'AMUGA, les communes et le ministère, avec seuils d'anonymat (aucune cellule publiée sous k = 20 usagers distincts, valeur ajustable par ADR).

- Publication d'un flux GTFS ouvert du réseau artisanal, sous une licence compatible avec celle d'OpenStreetMap (ODbL), pour contribuer au bien commun.

## Partie 7 — Les données : modèle, sources, démarrage, contributions, qualité

La donnée est le produit. Une belle interface sur des données fausses détruit la confiance en une semaine ; consacre à cette partie autant de soin qu'au code.

### 7.1 Standards à respecter

- **GTFS Schedule** comme format pivot du réseau, y compris frequencies.txt (lignes sans horaires), les champs continuous_pickup et continuous_drop_off (montée et descente n'importe où le long de la ligne, typiques des gbakas et wôrô-wôrôs) et GTFS-Fares v2 pour les prix.

- **GTFS-Flex** pour les services à zone (motos-taxis, certains wôrô-wôrôs).

- **GTFS-Realtime** (VehiclePositions, ServiceAlerts, et TripUpdates pour la SOTRA si disponible).

- **Extension propre**, documentée et versionnée, pour ce que GTFS ne couvre pas : état des files, véhicules présents en gare, prix observés, fiabilité.

- **OpenStreetMap** (licence ODbL) pour le réseau routier et piéton, les repères et les relations de lignes ; attribution obligatoire dans l'appli.

### 7.2 Modèle de données (entités principales)

Propose le schéma PostgreSQL et PostGIS complet en phase 1 ; il doit au minimum couvrir :

- city : ville, fuseau horaire (Africa/Abidjan), emprise, devise XOF.

- admin_area : communes et quartiers, polygones.

- place : repères et lieux, avec **plusieurs noms et alias** (orthographes, abréviations, nouchi), clés phonétiques, catégorie, géométrie, source, confiance, photos, statut de vérification.

- stop : type (sotra_stop, gare_artisanale, arret_informel, arret_minute, embarcadere, station_metro, station_brt, gare_interurbaine), point et **zone de montée** (rayon ou polygone, car un arrêt informel est flou), noms et alias, équipements (éclairage, abri, accessibilité), heures d'activité, gare parente.

- operator : SOTRA, STL, CITRANS, compagnies interurbaines, coopératives ou syndicats quand ils sont identifiés, ou opérateur générique « transport artisanal ».

- route : mode (bus_sotra, bus_express, bateau_bus, pinasse, gbaka, woro_communal, woro_intercommunal, taxi_compteur, moto_taxi, tricycle, metro, brt, car_interurbain), nom tel qu'on le dit (« Yopougon–Adjamé »), commune, apparence du véhicule (couleur, inscriptions).

- route_pattern : séquence ordonnée d'arrêts, tracé, sens, montée et descente continues, tranches horaires de validité, motif de variante (« terminus raccourci en cas de bouchon »).

- service_profile : par type de jour et tranche de 15 min, plage d'activité, distribution des intervalles entre véhicules, capacité, indicateur « part quand plein » à l'origine.

- fare_observation et fare_estimate : prix observés (montant, origine, destination, horodatage, conditions : pointe, pluie, nuit, fête, source, poids de confiance) et estimations dérivées (10e, 50e et 90e centiles, effectif, dernière observation, confiance).

- observation : tout événement brut horodaté et géolocalisé (file signalée, véhicules présents, montée, départ, véhicule plein, prix payé, incident, arrêt déplacé, déviation, photo, attente réelle), avec source, appareil pseudonyme et poids.

- queue_state : état dérivé par gare, ligne et sens (personnes estimées, véhicules estimés, régime de file, attente au 50e et 80e centile, confiance, dernière donnée).

- position_event et vehicle_session : positions de véhicules issues des usagers (inférées), des chauffeurs Pro ou des partenaires, toujours pseudonymisées.

- incident : type, géométrie, gravité, début et fin, source, statut.

- user, device, trust_score, contribution, reward_ledger : identité pseudonyme, préférences, réputation, récompenses.

- network_version, change_request, audit_log : versionnement du réseau et traçabilité.

- partner_feed : flux externes et leur état.

Les trajets planifiés et suivis restent autant que possible **sur le téléphone** ; le serveur ne reçoit que ce qui est nécessaire, dans les conditions de la partie 12.

### 7.3 Sources et démarrage à froid

1.  **Importer OpenStreetMap** pour la Côte d'Ivoire (extrait Geofabrik), y compris les relations de lignes existantes (réseaux du type « Gbaka d'Abobo », « Woro-woro de Cocody »).

2.  **Importer le GTFS « Abidjan 2023 »** de DigitalTransport4Africa, le valider avec le validateur canonique, le rapprocher d'OSM et produire un rapport d'écarts.

3.  **Conventions de données** à préparer pour l'AMUGA (cartographie, arrêts-minute, pôles AIM, plan de restructuration), la SOTRA (GTFS et positions des bus) et les opérateurs lagunaires. Prévois des connecteurs génériques GTFS et GTFS-Realtime pour les brancher dès qu'ils existent.

4.  **Campagne terrain « Éclaireurs »** : des étudiants recrutés et rémunérés parcourent chaque ligne du corridor pilote dans les deux sens, en pointe et en heure creuse, avec un mode « relevé » de l'appli : trace GPS, arrêts, prix payés, photos, comptage des départs et des files en gare par tranche de 15 min. Double relevé sur 10 % des lignes pour mesurer la qualité.

5.  **Recensement des gares** : nom usuel, emplacement précis, destinations, horaires, prix, contact de référence avec accord, photos.

6.  **Dictionnaire de repères** : POI d'OSM, relevés terrain, ajouts des usagers, avec alias et variantes orales.

7.  **Corridor pilote** à choisir avec les données de l'AMUGA parmi les plus chargés (par exemple Yopougon–Adjamé–Plateau ou Abobo–Adjamé). Ne passe à une nouvelle zone que lorsque la précédente atteint les seuils de densité : au moins 80 % des 50 trajets les plus demandés couverts, et au moins un signalement par gare toutes les 15 min en pointe.

### 7.4 Contributions des usagers et capteurs passifs

- **Contributions actives** : définies en F-07, chacune typée, horodatée, géolocalisée et contrôlée (un signalement de file n'est accepté que si l'appareil est à moins de 150 m de la gare, seuil ajustable).

- **Capteur passif** (avec consentement, pendant un trajet suivi uniquement) : échantillonnage GPS adaptatif ; détection sur le téléphone de la montée, du mode et de la descente (partie 8) ; envoi de segments **tronqués de 300 m au début et à la fin** pour protéger domicile et lieu de travail ; inférence de la position des véhicules et des vitesses sur le réseau.

- **Sources vérifiées** : chefs de gare, Éclaireurs, partenaires ; leur poids est plus élevé mais reste contrôlé.

### 7.5 Fiabilité, agrégation et lutte contre la fraude

- **Poids d'une observation** = réputation du contributeur × poids de la source × décroissance temporelle × plausibilité. La décroissance a une demi-vie par type (par exemple 10 min pour une file en pointe, 30 jours pour un prix) à calibrer.

- **Réputation** : loi Bêta par contributeur, mise à jour selon l'accord de ses contributions avec le consensus, les traces GPS et les vérités terrain ; les nouveaux comptes démarrent avec un poids faible.

- **Agrégation** : fusion bayésienne des observations récentes avec l'a priori du modèle historique (partie 8) ; l'état publié porte toujours sa confiance.

- **Anti-fraude** : contrôles de vitesse impossible et de téléportation ; attestation d'intégrité de l'appareil (Play Integrity) ; limites de fréquence ; détection de grappes de faux comptes (même appareil, même réseau, mêmes horaires) ; récompenses versées seulement après validation ; mise en quarantaine silencieuse des comptes suspects ; journal d'audit.

- **Règles de fraîcheur** : chaque type d'information a une durée de validité après laquelle l'appli revient à l'estimation historique, affichée comme telle.

### 7.6 Mesurer la qualité des données

Tableau de bord dans le back-office : fraîcheur par gare et par ligne, couverture des trajets fréquents, écart entre attente prévue et attente déclarée, taux de contributions rejetées, écarts avec OSM et GTFS, lignes non parcourues depuis plus de 90 jours.

## Partie 8 — Algorithmes

Pour chaque algorithme : implémente une version de base simple et testée, mesure-la contre la vérité terrain, puis améliore. Documente les hypothèses et les paramètres dans docs/ALGORITHMES.md.

### 8.1 Calcul d'itinéraire multicritère

- **Interface unique** RoutingEngine, pour pouvoir changer d'implémentation sans toucher au reste.

- **Critères** : temps total au 80e centile (attente comprise), temps au 50e centile, coût au 50e centile, nombre de changements, minutes de marche, et la nuit une pénalité de sûreté (arrêts non éclairés, incidents récents). Le calcul produit un **front de Pareto**, puis on choisit les options étiquetées : la moins chère (coût minimal, puis temps), la plus rapide (80e centile minimal), la plus simple (changements puis marche minimaux) ; on retire les options dominées et les quasi-doublons.

- **Algorithme cible** : McRAPTOR (RAPTOR multicritère) sur un réseau à fréquences, où le coût de montée d'une ligne est l'**attente estimée en direct** par le modèle de la section 8.2. La montée et la descente continues sont gérées en créant des points de montée virtuels le long du tracé, tous les 150 à 300 m, aux endroits réellement utilisés.

- **Stratégie de mise en œuvre à arbitrer par ADR après un spike de deux jours** :

  - option A : OpenTripPlanner 2 (GTFS et OSM) comme générateur d'itinéraires candidats, puis notre service ré-évalue chaque étape avec l'attente, le prix et la fiabilité en direct et refait le tri ; rapide à livrer, à condition de vérifier sa prise en charge des fréquences et de la montée continue ;

  - option B, recommandée à terme : notre propre moteur McRAPTOR écrit en Rust, utilisé côté serveur **et** sur le téléphone via une liaison native (par exemple flutter_rust_bridge), ce qui garantit les mêmes résultats en ligne et hors ligne.

- **Incertitude** : la durée d'un itinéraire est une somme de variables aléatoires (attentes, temps à bord, marche) ; calcule les centiles par simulation Monte-Carlo (500 tirages suffisent) ou par approximation analytique validée.

- **Temps à bord** : vitesses par tronçon OSM et par tranche de 15 min, issues des traces (historique et direct), plus des temps d'arrêt par type de véhicule.

- **Marche** : graphe piéton OSM, vitesse paramétrable (plus lente pour le profil mobilité réduite), pénalités pour traversées dangereuses et zones inondées signalées.

### 8.2 Estimation de l'attente

Il y a trois régimes. Le modèle doit d'abord savoir dans lequel il se trouve.

- **Régime A, gare où le véhicule part quand il est plein** (gbakas, wôrô-wôrôs en tête de ligne). État : P passagers dans la file, V véhicules en chargement, C places par véhicule, débit d'arrivée des passagers λp et des véhicules λv.

  - **File de véhicules** (des véhicules attendent des passagers) : le nouveau passager monte tout de suite ; son attente est le temps de remplissage des places restantes, soit environ places restantes divisées par λp, plafonné par la durée maximale observée avant départ.

  - **File de passagers** (des passagers attendent des véhicules) : il faut n = arrondi supérieur de (P + 1 − places libres) / C véhicules supplémentaires ; l'attente suit une loi Gamma de paramètres n et λv, dont on tire le 50e et le 80e centile.

  - λp et λv sont estimés par tranche horaire à partir des comptages et des événements de départ, puis mis à jour en direct par un modèle conjugué Gamma-Poisson.

- **Régime B, bord de route ou arrêt intermédiaire** : les véhicules de la ligne passent au débit λpassage, avec une probabilité q d'avoir une place libre, faible loin de la tête de ligne aux heures de pointe. Débit utile λ = λpassage × q ; attente approximativement exponentielle : 50e centile = ln 2 / λ, 80e centile = ln 5 / λ. Pour des intervalles réguliers mais variables, l'attente moyenne vaut H/2 × (1 + CV²), où H est l'intervalle moyen et CV son coefficient de variation.

- **Régime C, lignes suivies par GPS** (SOTRA, BRT, métro, véhicules Pro) : attente = heure d'arrivée prévue du prochain véhicule ayant de la place, à partir des positions en direct et du modèle de vitesse.

- **Couche d'apprentissage automatique** : régression par quantiles (gradient boosting, par exemple LightGBM) pour prédire l'attente aux 50e et 80e centiles et les débits, avec ces variables : gare, ligne, sens, tranche de 15 min, type de jour (ouvrable, samedi, dimanche, férié, vacances scolaires, fin de mois), pluie actuelle et dernière heure, événements, incidents, signalements récents, débit GPS récent. Démarrage à froid par a priori hiérarchiques (commune, mode) avec mise en commun partielle. Réentraînement quotidien.

- **Étiquettes** : départs observés, traces des usagers, réponses à « Tu as attendu combien ? ».

- **Calibration surveillée** : la vraie attente doit être inférieure au 80e centile annoncé dans 78 à 82 % des cas ; alerte automatique si ce n'est plus le cas.

- **Conseil « remonter à la gare »** : si marche jusqu'à la tête de ligne + attente en gare est inférieure de plus de 5 min à l'attente au bord de la route, le proposer explicitement.

### 8.3 Estimation des prix

- Par ligne, zone d'origine, zone de destination et condition (pointe, pluie, nuit, fête) : médiane et centiles pondérés des observations, multiplicateurs de condition appris.

- **Détection de rupture** (par exemple CUSUM) pour adopter rapidement un nouveau niveau de prix après une hausse du carburant et faire vieillir les anciennes observations.

- Affichage arrondi à 50 FCFA, en fourchette ; avertissement « prépare la monnaie » quand c'est pertinent.

- Comparaison VTC et taxi-compteur : estimation par distance et durée à partir de grilles observées, présentée comme indicative.

### 8.4 Géocodage par repères

- **Normalisation** : minuscules, suppression des accents (ô devient o), ponctuation, abréviations standardisées (Yop, Adj, Koum, Sipo).

- **Recherche hybride** : trigrammes (pg_trgm côté serveur ; SQLite FTS5 et index de trigrammes sur le téléphone), clé phonétique adaptée au français parlé en Côte d'Ivoire (à concevoir et tester sur les 300 requêtes réelles), dictionnaire de synonymes, priorité aux lieux populaires et proches.

- **Expressions relatives** : « derrière », « en face de », « après le carrefour », « à côté de » → point d'ancrage plus zone d'incertitude.

- **Voix** : reconnaissance vocale en français, testée sur des accents ivoiriens réels ; dioula en V3 ; repli sur menus si la reconnaissance échoue.

### 8.5 Détection de la montée, du mode et de la descente (sur le téléphone)

- Signaux : vitesse et précision GPS, reconnaissance d'activité du système, proximité des tracés et des arrêts, profil arrêt-redémarrage, présence sur l'eau près d'un embarcadère.

- Appariement à la carte par modèle de Markov caché (Viterbi) sur les tracés de lignes pour déterminer la ligne empruntée ; montée = passage marche → véhicule près d'un arrêt ; descente = l'inverse.

- Batterie : localisation fusionnée en équilibre énergie-précision, échantillonnage toutes les 5 à 15 s à bord, 30 s à l'arrêt, géorepérage pour l'alerte de descente.

### 8.6 Position des véhicules et congestion

- Regrouper les usagers qui se déplacent ensemble sur la même ligne (positions et vitesses proches) en un seul véhicule ; fusionner avec les positions Pro et partenaires ; lisser par filtre de Kalman ; extrapoler le long du tracé quand la donnée vieillit ; supprimer après un délai par catégorie.

- Vitesses par tronçon et tranche de 15 min, comparées à la vitesse libre, pour la couche congestion et le modèle de temps à bord.

### 8.7 Carte de la demande pour les chauffeurs

- Par gare et arrêt : nombre de personnes en attente estimé, par catégories arrondies, plus une prévision à 30 min (historique + signalements + pluie). Jamais de point représentant une personne.

### 8.8 Évaluation

- Rétro-tests sur les données passées, suite de 200 trajets de référence, mesures d'erreur absolue médiane et de couverture des centiles, tests A/B des règles de tri des options.

## Partie 9 — Architecture technique

Les choix ci-dessous sont des recommandations argumentées. Tu peux en proposer d'autres, mais seulement par un ADR qui compare les options sur ces critères : poids de l'appli, performance sur téléphone d'entrée de gamme, fonctionnement hors ligne, coût d'exploitation, facilité de recrutement en Côte d'Ivoire, maturité de l'écosystème.

### 9.1 Vue d'ensemble

- **Appli mobile** : Flutter (Dart), Android en priorité, iOS ensuite avec la même base de code. Alternative à évaluer : Kotlin natif si le gain de poids est décisif. Cible minSdk 26 (Android 8.0), découpage par architecture processeur, R8 et réduction des ressources, publication en Android App Bundle.

- **Cartographie** : MapLibre (rendu vectoriel libre), tuiles vectorielles générées depuis OpenStreetMap avec Planetiler, stockées en PMTiles sur un stockage objet avec CDN ; style sobre et lisible au soleil ; extrait PMTiles par ville pour le hors ligne.

- **Stockage sur le téléphone** : SQLite (via drift) pour le réseau, les repères, les profils d'attente historiques compressés, la file des contributions à envoyer et les trajets enregistrés.

- **Backend** : monolithe modulaire au départ, découpé seulement quand la charge l'exige.

  - API principale : TypeScript avec NestJS (ou Go, à trancher par ADR), REST versionné /v1 décrit en OpenAPI 3.1.

  - Moteur d'itinéraires : service Rust (McRAPTOR), ou OpenTripPlanner 2 en phase 1 selon l'ADR de la partie 8.

  - Apprentissage automatique : service Python (FastAPI) pour l'entraînement et l'inférence des modèles d'attente, de prix et de détection.

  - Adaptateurs de canaux : WhatsApp, SMS, USSD, serveur vocal (partie 11).

- **Données** : PostgreSQL 16 avec PostGIS et pg_trgm ; séries temporelles d'observations partitionnées par jour (TimescaleDB ou partitionnement natif) ; Redis pour l'état en direct, les index géographiques et la limitation de débit ; bus d'événements NATS JetStream (observations, puis agrégation, puis état publié).

- **Temps réel vers les clients** : Server-Sent Events ou WebSocket, avec des deltas compacts (Protocol Buffers) limités à la zone affichée ; repli sur interrogation périodique.

- **Météo** : partenariat SODEXAM si possible, sinon une API météo ouverte dont les conditions d'utilisation sont vérifiées.

- **Notifications** : Firebase Cloud Messaging, agrégateur SMS local, API WhatsApp Business.

### 9.2 Hébergement et exploitation

- La loi n°2013-450 encadre le transfert de données personnelles hors de Côte d'Ivoire : prévois soit un hébergement local (centre de données en Côte d'Ivoire), soit l'autorisation correspondante de l'ARTCI. Documente le choix dans un ADR.

- Démarrage simple : 2 à 3 machines virtuelles, Docker Compose, PostgreSQL sauvegardé et répliqué ; passage à Kubernetes léger (k3s) seulement si nécessaire.

- Infrastructure décrite en code (Terraform et/ou Ansible) ; environnements de développement, de préproduction et de production séparés.

- Observabilité : OpenTelemetry, Prometheus, Grafana, Loki ; remontée des plantages mobiles (Sentry ou équivalent, avec données minimisées).

- Intégration continue : lint, tests unitaires et d'intégration, build de l'APK, tests sur émulateur, validation GTFS, analyse de sécurité des dépendances et des images (Trivy), analyse statique mobile (MobSF).

- Sauvegardes chiffrées quotidiennes, restauration testée chaque mois.

### 9.3 Budgets de performance (bloquants en intégration continue quand c'est mesurable)

| Indicateur                                     | Budget                                           |
|------------------------------------------------|--------------------------------------------------|
| Taille de téléchargement Android               | 20 Mo maximum, objectif 15 Mo                    |
| Démarrage à froid jusqu'à l'écran de recherche | 2,5 s maximum sur le téléphone de référence      |
| Mémoire en usage normal                        | 150 Mo maximum                                   |
| Du lancement à la première recommandation      | 10 s maximum                                     |
| Calcul d'itinéraire côté serveur               | 2 s au 95e centile                               |
| Calcul d'itinéraire hors ligne                 | 3 s maximum                                      |
| Data par recherche d'itinéraire                | 30 Ko maximum                                    |
| Data par minute de carte active                | 150 Ko maximum                                   |
| Batterie pendant un trajet suivi               | 4 % par heure maximum                            |
| Sessions sans plantage                         | 99,5 % minimum                                   |
| Disponibilité mensuelle de l'API               | 99,5 % minimum, 99,9 % visé aux heures de pointe |

### 9.4 Dimensionnement

- Pointes de 6 h à 9 h et de 16 h 30 à 20 h, plus des pics brutaux pendant les pluies et les grandes perturbations.

- Prévois pour la deuxième année : 300 000 utilisateurs actifs par jour à Abidjan, 50 000 connectés simultanément en pointe, 2 000 événements entrants par seconde, 200 calculs d'itinéraire par seconde. Fournis des tests de charge qui le prouvent (k6 ou équivalent).

- Estime le coût mensuel d'infrastructure par palier d'utilisateurs et garde-le dans docs/COUTS.md.

### 9.5 Hors ligne

- **Pack ville versionné** : réseau, repères, profils d'attente et de prix historiques, fond de carte léger optionnel.

- **Mises à jour différentielles** quotidiennes (différences par enregistrement, compressées).

- **File d'envoi** des contributions avec clés d'idempotence, horodatage local, renvoi automatique au retour du réseau.

- **Cohérence** : le serveur fait foi ; en cas de conflit, la donnée la plus récente et la plus fiable l'emporte selon les règles de la partie 7.

### 9.6 API

- REST versionné, OpenAPI 3.1, réponses compressées (Brotli), ETags, pagination, limites de débit par appareil et par compte, clés d'idempotence pour toutes les écritures.

- Points d'accès principaux à concevoir : recherche de lieux, calcul d'itinéraire, détail de gare, état en direct par zone, contributions, incidents, packs hors ligne, compte, récompenses, back-office, flux partenaires (GTFS, GTFS-Realtime et extension).

- Contrats testés automatiquement entre l'appli, l'API et le moteur d'itinéraires.

### 9.7 Organisation du dépôt (monorepo)

apps/mobile appli Flutter (usagers et mode Pro)  
apps/admin back-office web  
apps/web-lite pages légères partageables (itinéraire, suivi de trajet)  
services/api API principale  
services/routing moteur d'itinéraires  
services/ml modèles d'attente, de prix, de détection  
services/channels WhatsApp, SMS, USSD, serveur vocal  
packages/proto schémas Protocol Buffers partagés  
data/pipelines import OSM et GTFS, génération des tuiles et des packs  
data/fixtures_fictives jeux de test fictifs  
infra Docker, Terraform, Ansible  
docs documentation vivante et ADR

## Partie 10 — Expérience utilisateur, langues, voix, accessibilité

### 10.1 Méthode

- Avant de coder les écrans, teste les parcours avec des maquettes cliquables et un prototype « magicien d'Oz » sur WhatsApp (un humain répond derrière) auprès de vrais usagers, dans les gares.

- Chaque itération est testée avec 5 à 8 personnes, dont au moins 2 qui lisent difficilement et 1 personne âgée. Consigne les résultats dans docs/UX/tests-AAAA-MM-JJ.md.

- Test de compréhension des icônes : chaque icône de mode et d'action doit être reconnue sans légende par au moins 85 % de 20 personnes.

### 10.2 Architecture de l'information

- Trois onglets au maximum : **Trajet**, **Carte**, **Moi** ; un bouton flottant **Signaler** toujours visible.

- **Écran d'accueil** : grand champ « Tu vas où ? » avec micro ; raccourcis Maison, Boulot, École ; trajets récents ; bloc « Autour de moi » avec les gares proches, leur état de file et les lignes qui y passent.

- **Écran de résultats** : une carte par option, avec étiquette (Moins cher, Plus rapide, Plus simple), pictogrammes des modes dans l'ordre, durée en fourchette, prix en fourchette, attente, changements, marche, fraîcheur de la donnée. Liste d'abord, carte ensuite : on doit pouvoir décider sans lire une carte.

- **Écran pas à pas** : grandes étapes, photo de repère, bouton audio sur chaque étape, bouton « Je pars ».

- **Feuille « Pourquoi cette estimation ? »** : d'où vient le chiffre, quand, combien de personnes l'ont confirmé.

### 10.3 Langage visuel

- Contraste élevé, lisible en plein soleil ; mode sombre pour économiser la batterie.

- Zones tactiles d'au moins 48 dp ; texte courant d'au moins 16 sp ; utilisable d'une seule main.

- Chaque mode a une icône, une forme et une couleur ; jamais la couleur seule (daltonisme). Les illustrations de véhicules reprennent les codes réels : gbaka, wôrô-wôrô aux couleurs de sa commune, bus SOTRA, bateau-bus.

- Badges standard : fraîcheur (« il y a 3 min »), confiance (plein, moyen, faible), source (usagers, chef de gare, GPS, historique).

- Système de design avec jetons (couleurs, espacements, typographie) et composants réutilisables : bouton, carte d'option, puce de mode, badge d'attente, fourchette de prix, étiquette de fraîcheur, étape, feuille de signalement.

### 10.4 Ton et microcopie

- Français simple, phrases de 12 mots maximum, verbes d'action, aucun jargon (« itinéraire multimodal » devient « ton trajet »).

- Vocabulaire local : gare, gbaka, wôrô-wôrô, apprenti, terminus, descente, monnaie. Une touche de nouchi est possible si elle est validée par des locaux, jamais caricaturale.

- Tutoiement chaleureux par défaut, à valider en tests utilisateurs.

- Formats : « 300 F » pour les prix, « 6 h 30 » pour les heures, « 10 à 20 min » pour les durées.

- Les messages d'erreur disent quoi faire : « Pas de réseau. Ton trajet enregistré reste disponible. »

### 10.5 Voix et langues

- Lecture vocale de chaque étape en français ; annonces à bord (« Prochain arrêt : … ») ; enregistrements faits par des voix ivoiriennes pour les phrases clés, plus rassurants qu'une synthèse vocale standard.

- Langues : français de Côte d'Ivoire au MVP ; dioula en V2 (au moins audio et menus vocaux) ; baoulé et d'autres langues en V3 selon la demande mesurée.

- Internationalisation dès le premier jour : clés de traduction, règles de pluriel ICU, aucune chaîne en dur.

### 10.6 Accessibilité

- Compatibilité TalkBack ; agrandissement du texte jusqu'à 200 % sans casse ; retours haptiques ; aucune action limitée dans le temps.

- Profil mobilité réduite (F-16) ; descriptions des gares (marches, passerelles, distance de marche).

### 10.7 Premier lancement et permissions

- Pas d'inscription obligatoire ; trois écrans d'accueil au maximum, avec « Passer ».

- Permissions demandées au moment où elles servent, avec une phrase d'explication : localisation à la première recherche, localisation en arrière-plan seulement au premier « Je pars », notifications au premier trajet régulier.

- Proposition du pack hors ligne quand le téléphone est en Wi-Fi.

## Partie 11 — Canaux sans smartphone et sans appli

Environ 60 % de la population n'a pas d'accès à internet ou pas de smartphone. Sans ces canaux, la solution exclut ceux qui en ont le plus besoin.

### 11.1 Un moteur de conversation commun

- Un seul moteur indépendant du canal : il comprend l'origine et la destination (texte ou voix transcrite), lève les ambiguïtés par des choix numérotés (« 1. Siporex Yopougon 2. Siporex autre »), appelle le même RoutingEngine que l'appli et met en forme la réponse selon les contraintes du canal.

- Mémoire de session courte (dernière requête, lieux favoris si l'usager le souhaite).

- Les mêmes estimations, avec la même fraîcheur et la même honnêteté que dans l'appli.

### 11.2 WhatsApp (prototype humain au MVP, automatisé en V2)

- L'usager écrit « Yop Siporex → Plateau », partage sa position ou envoie une note vocale.

- Réponse : les deux meilleures options en quelques lignes avec émojis de mode, prix et attente ; « Réponds 1 ou 2 pour le détail ».

- Abonnements : « Préviens-moi chaque jour à 6 h 30 pour Siporex → Plateau », avec consentement explicite.

- Utilise l'API WhatsApp Business officielle ; vérifie la grille tarifaire en vigueur au moment de l'implémentation, car les conversations initiées par l'entreprise sont facturées différemment de celles initiées par l'usager.

### 11.3 SMS (V2)

- Numéro court ; syntaxe tolérante : « Siporex Plateau » ou « DE Siporex A Plateau ».

- Réponse en 2 SMS maximum, en caractères GSM 7 bits (pas d'émojis), avec abréviations claires.

- Aussi utilisé pour les codes de connexion et les alertes d'urgence du partage de trajet.

### 11.4 USSD (V2 ou V3 selon les accords opérateurs)

- Nécessite un accord avec Orange, MTN et Moov, ou un agrégateur agréé ; prévois les coûts et délais dans le plan.

- Arbre de menus de 5 écrans maximum : 1 Trajet → commune de départ → gare ou repère de départ (les 8 plus fréquents + « Autre ») → commune d'arrivée → destination → résultat, avec « Recevoir par SMS ».

- Écrans courts (environ 180 caractères), listes mises en cache, gestion de l'expiration de session, choix de la langue.

### 11.5 Serveur vocal (V3)

- L'usager appelle, dit sa destination (reconnaissance vocale en français, puis en dioula) ou navigue au clavier ; la réponse est lue par une voix ivoirienne et peut être envoyée par SMS.

- Étudie un numéro gratuit ou à coût réduit avec un opérateur partenaire.

### 11.6 Pages web légères

- Liens partageables pour un itinéraire ou un trajet suivi en direct ; pages rendues côté serveur de moins de 100 Ko, lisibles sur les navigateurs légers et les téléphones à fonctions avancées.

### 11.7 Critères

- Une même requête donne la même recommandation sur tous les canaux (tests automatiques croisés).

- Temps de réponse inférieur à 5 s sur WhatsApp et SMS, hors délais de l'opérateur.

- Coût unitaire par requête et par canal suivi dans docs/COUTS.md.

## Partie 12 — Vie privée, sécurité, cadre légal et sûreté

Tu n'es pas juriste : signale clairement ce qui doit être validé par un avocat ivoirien ou par l'ARTCI, mais conçois dès le départ un système qui facilite cette validation.

### 12.1 Conformité à la loi n°2013-450

- **Avant toute collecte réelle** : préparer le dossier de déclaration ou de demande d'autorisation auprès de l'ARTCI (finalités, catégories de données, durées de conservation, mesures de sécurité, géolocalisation, éventuels transferts hors du pays) ; prévoir la désignation d'un correspondant à la protection des données.

- Produire dans docs/PRIVACY.md le registre des traitements et une analyse d'impact pour la géolocalisation.

- Politique de confidentialité et conditions d'utilisation en français simple, avec une version audio courte.

- Droits des personnes accessibles dans l'appli : consulter, rectifier, exporter, supprimer son compte et ses données, retirer un consentement.

- Loi n°2013-451 sur la cybercriminalité : à prendre en compte pour la sécurité et la gestion des incidents.

### 12.2 Minimisation et anonymisation

- Aucune donnée personnelle nécessaire pour chercher un itinéraire.

- Identifiants pseudonymes par appareil, renouvelés régulièrement pour les données de mobilité ; numéro de téléphone stocké seulement s'il y a un compte, haché pour les recherches et chiffré au repos.

- Traces GPS : traitement sur le téléphone autant que possible ; envoi de segments tronqués de 300 m au début et à la fin ; séparation stricte entre identité et traces ; agrégation avant toute analyse.

- **Durées de conservation** proposées (à valider) : positions brutes 30 jours au maximum ; observations brutes 12 mois ; agrégats anonymes sans limite ; journaux techniques 90 jours.

- Publications et exports : seuil d'anonymat k ≥ 20 personnes distinctes par cellule, bruit ajouté si nécessaire.

- Aucune vente de données personnelles. Les partenaires n'ont accès qu'à des agrégats.

### 12.3 Sécurité applicative

- Référentiels OWASP MASVS pour le mobile et ASVS pour l'API ; modélisation des menaces documentée.

- TLS partout, épinglage de certificat sur l'appli ; chiffrement au repos ; secrets hors du code (gestionnaire de secrets) ; principe du moindre privilège.

- Authentification forte et à deux facteurs pour le back-office ; journal d'audit inviolable.

- Attestation d'intégrité de l'appli, limitation de débit, protection contre l'injection de fausses positions et les robots.

- Dépendances surveillées, images scannées, tests d'intrusion avant le lancement public et chaque année.

- Plan de réponse aux incidents, avec notification des personnes concernées et des autorités si nécessaire.

### 12.4 Sûreté des personnes

- Aucune interaction possible pour le conducteur d'un véhicule en mouvement.

- Jamais de position d'une personne identifiable visible par d'autres ; les véhicules apparaissent de façon anonyme.

- Pas de signalement de contrôles de police, pas de nom ni de plaque de chauffeur publiés.

- Signalements de harcèlement : anonymes, agrégés par zone et tranche horaire, sans désignation de personne ; orientation vers les numéros d'urgence et les structures d'aide reconnues.

- Bouton d'urgence et partage de trajet (F-11) testés en conditions réelles, y compris sans data (repli SMS).

- Pendant les inondations, ne jamais recommander un itinéraire qui traverse une zone signalée comme submergée.

### 12.5 Mineurs

- Si des élèves utilisent l'appli, ne collecte aucune donnée d'âge non nécessaire et applique les mêmes protections renforcées à tous par défaut.

## Partie 13 — Modèle économique et partenariats

Tu n'as pas à coder le modèle économique, mais l'architecture doit le rendre possible sans refonte, et tes choix techniques doivent tenir compte du coût par usager.

### 13.1 Principe

Le service de base reste **gratuit pour les usagers**, sans publicité intrusive et sans vente de données personnelles. Les revenus viennent d'acteurs qui ont intérêt à une mobilité plus fluide.

### 13.2 Sources de revenus envisagées

| Source                              | Description                                                                                                                  | Prérequis techniques                                                               |
|-------------------------------------|------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| Données agrégées pour les autorités | Tableaux de bord et exports pour l'AMUGA, les communes, le ministère, les bailleurs (Banque mondiale, AFD)                   | Portail partenaires, seuils d'anonymat, API                                        |
| Opérateurs de transport             | Information voyageur pour SOTRA, opérateurs lagunaires, compagnies interurbaines ; plus tard vente de titres avec commission | Connecteurs GTFS-Realtime, module de paiement découplé                             |
| Opérateurs télécoms                 | Gratuité de la data de l'appli (accès « zero-rating ») sponsorisée, distribution, récompenses en data                        | Domaines et flux réseau bien identifiés                                            |
| Mobile money                        | Paiement des titres et, à terme, des trajets artisanaux volontaires                                                          | Intégration Wave, Orange Money, MTN MoMo, Moov Money derrière une interface unique |
| Employeurs                          | Programmes de déplacement domicile-travail pour leurs salariés                                                               | Comptes entreprise, rapports agrégés                                               |
| Publicité locale contextuelle       | Annonces non intrusives liées à un lieu (gare, quartier), jamais à un profil personnel                                       | Emplacements limités, contrôle qualité                                             |

### 13.3 Partenariats à préparer

- **AMUGA** : convention de partage de données, alignement avec ses projets d'information voyageur, présence dans les groupes de travail communaux.

- **SOTRA et opérateurs lagunaires** : flux GTFS et positions en temps réel.

- **Faîtières du transport artisanal, syndicats, chefs de gare** : co-construction du mode Pro et de la console de gare.

- **Universités** : recrutement des Éclaireurs, projets de recherche, validation des modèles.

- **Opérateurs télécoms et mobile money** : data gratuite, USSD, SMS, récompenses.

- **Communauté OpenStreetMap de Côte d'Ivoire** : amélioration continue de la carte.

### 13.4 Ce que tu dois produire

- Dans docs/COUTS.md : coût d'infrastructure et de canaux (SMS, WhatsApp, USSD) par utilisateur actif et par requête, par palier de croissance.

- Une architecture où le paiement, la publicité et le portail partenaires sont des modules séparés, désactivables par configuration.

## Partie 14 — Qualité, tests et indicateurs de succès

### 14.1 Stratégie de test

- **Tests unitaires** : au moins 80 % de couverture sur le domaine critique (calcul d'itinéraire, modèles d'attente et de prix, agrégation et réputation, géocodage).

- **Tests par propriétés** sur le moteur d'itinéraires : aucune option dominée dans le résultat, cohérence quand on ajoute une ligne, symétrie raisonnable aller et retour.

- **Suite de 200 trajets de référence** définie avec des Abidjanais en phase 0 (origine, destination, heure, réponses jugées acceptables) ; exécutée à chaque modification du moteur ou des données ; toute régression bloque la publication.

- **Tests d'intégration et de contrat** entre appli, API, moteur, apprentissage automatique et canaux.

- **Tests de bout en bout** de l'appli sur émulateur, et tests visuels de référence des écrans clés.

- **Simulateur** : un simulateur par agents d'un corridor (passagers, véhicules, gares, signalements bruités, tentatives de fraude, pluie) pour tester l'agrégation, les estimations et la charge avant d'avoir des données terrain, puis pour reproduire les incidents.

- **Parc de téléphones réels** représentatifs du marché ivoirien (entrées de gamme Tecno, Itel, Infinix, Samsung série A), profils réseau 2G, 3G et coupures, mesure de la batterie et de la data.

- **Tests terrain** : pilote fermé avec au moins 50 usagers sur le corridor pendant 2 semaines avant toute ouverture publique.

- **Tests d'accessibilité** (TalkBack, agrandissement du texte) et **tests avec des usagers peu alphabétisés**.

- **Tests de sécurité** (analyse statique et dynamique, tests d'intrusion) et **tests de résilience** (perte du bus d'événements, bascule de la base de données).

- **Validation des données** : validateur GTFS, contrôles de schéma, détection d'anomalies à chaque import.

### 14.2 Indicateurs

Les cibles ci-dessous sont des propositions pour le pilote de 3 mois ; recalibre-les après la phase 0 avec des mesures de référence.

| Indicateur                                   | Définition                                                                                          | Cible proposée                                                    |
|----------------------------------------------|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| Minutes d'attente évitées (indicateur phare) | Attente médiane historique du trajet moins attente réelle déclarée sur l'option suivie, par semaine | En hausse chaque mois                                             |
| Précision de l'attente                       | Erreur absolue médiane entre attente prévue et attente réelle                                       | 5 min maximum avec données en direct, 10 min avec historique seul |
| Calibration                                  | Part des attentes réelles sous le 80e centile annoncé                                               | Entre 78 % et 82 %                                                |
| Justesse des prix                            | Part des prix payés déclarés dans la fourchette annoncée                                            | 80 % minimum                                                      |
| Réalisme des itinéraires                     | Part des options jugées réalistes sur la suite de référence                                         | 85 % minimum                                                      |
| Fraîcheur                                    | Part des gares du corridor avec une information de moins de 15 min en pointe                        | 70 % minimum                                                      |
| Couverture                                   | Part des 50 trajets les plus demandés avec un itinéraire valide                                     | 80 % minimum                                                      |
| Rétention                                    | Utilisateurs encore actifs 30 jours après la première utilisation                                   | 25 % minimum                                                      |
| Contribution                                 | Part des utilisateurs actifs qui contribuent chaque semaine ; part des contributions rejetées       | 15 % minimum ; moins de 10 % rejetées                             |
| Inclusion                                    | Part des requêtes par WhatsApp, SMS ou USSD ; part des usagers sur téléphones de 2 Go ou moins      | Suivies et en hausse                                              |
| Technique                                    | Sessions sans plantage ; latence ; data par session                                                 | Budgets de la partie 9                                            |
| Chauffeurs (V2)                              | Temps moyen de remplissage en gare ; kilomètres à vide estimés                                      | En baisse pour les chauffeurs Pro                                 |

### 14.3 Observabilité et objectifs de service

- Objectifs de service écrits pour l'API, le moteur, la fraîcheur des données et les canaux, avec alertes et astreinte.

- Tableaux de bord produit (sans données personnelles) et tableaux de bord techniques séparés.

## Partie 15 — Feuille de route, ordre de construction, livrables

Les durées sont indicatives pour une petite équipe ; ajuste-les selon les moyens que je t'indiquerai.

### 15.1 Phase 0 — Fondations (4 à 6 semaines)

Livrables attendus de ta part :

1.  Documents : ARCHITECTURE.md, premiers ADR (stack mobile, langage de l'API, option A ou B du moteur après spike, hébergement et transfert de données), HYPOTHESES.md, DATA.md, PRIVACY.md (registre des traitements, brouillon du dossier ARTCI), COUTS.md v0.

2.  Monorepo initialisé selon la partie 9, intégration continue au vert, environnement de développement lancé par une seule commande (docker compose up).

3.  Schéma de base de données complet (migrations) et spécification OpenAPI v0.

4.  Pipelines d'import : OpenStreetMap Côte d'Ivoire, GTFS « Abidjan 2023 », génération des tuiles ; rapport de validation GTFS et rapport d'écarts avec OSM.

5.  Jeu fixtures_fictives et simulateur par agents v0.

6.  Moteur d'itinéraires utilisable en ligne de commande sur les données importées.

7.  Prototype cliquable des parcours clés (écrans Flutter sur données fictives) et protocole de test utilisateur ; protocole du prototype WhatsApp « magicien d'Oz ».

8.  Kit de la campagne terrain : spécification du mode « relevé », fiches de collecte, protocole qualité, gabarit des 200 trajets de référence.

**Terminé quand** : un itinéraire réel est calculé de bout en bout sur les données importées, l'intégration continue est au vert et chaque décision structurante a son ADR.

### 15.2 Phase 1 — MVP sur le corridor pilote (10 à 12 semaines)

- Fonctionnalités : F-01, F-02, F-03, F-04, F-05 (gares et incidents), F-06, F-07, F-08 pour les trajets suivis, F-11 (partage et urgence), F-12, F-13.

- Back-office : éditeur de réseau versionné, modération, gestion des incidents, tableaux de bord qualité.

- Modèles v1 : attente (régimes A, B et C, mise à jour bayésienne sur a priori historiques), prix, géocodeur.

- Pack hors ligne, pages web légères de partage, mode « relevé » pour les Éclaireurs.

- Socle de sécurité, télémétrie respectueuse de la vie privée, budgets de performance contrôlés.

- Pilote fermé de 50 usagers, puis bêta ouverte sur le corridor.

**Ordre de construction en tranches verticales** :

1.  Données et modèle de réseau, puis moteur d'itinéraires.

2.  API d'itinéraire, puis écrans recherche, résultats et pas à pas dans l'appli, avec pack hors ligne.

3.  Fiche gare, contributions, agrégation et état des files.

4.  Suivi de trajet et alertes de descente.

5.  Back-office : édition et modération.

6.  Sûreté : partage de trajet et bouton d'urgence.

7.  Durcissement : performance, sécurité, accessibilité.

8.  Pilote terrain et corrections.

**Terminé quand** : tous les critères d'acceptation des fonctionnalités MVP sont vérifiés sur le téléphone de référence, la suite de trajets de référence atteint 85 %, la déclaration ARTCI est déposée avant toute collecte réelle, et le rapport de pilote est rédigé.

### 15.3 Phase 2 — Tout Abidjan et le temps réel (4 à 6 mois)

- Extension commune par commune selon les seuils de densité de la partie 7.

- Carte des véhicules en temps réel (F-05 complet), mode Pro (6.1), console de gare (6.2), capteur passif et inférence des véhicules (8.5, 8.6).

- Modèle d'attente par apprentissage automatique, F-09, F-10, F-14, F-16.

- WhatsApp automatisé, SMS, USSD si les accords opérateurs sont signés ; audio en dioula.

- Flux temps réel SOTRA et lagunaires si les conventions sont signées.

### 15.4 Phase 3 — Intérieur du pays, interurbain, intégrations (6 à 12 mois)

- Bouaké, Yamoussoukro, San-Pédro et Korhogo, avec les motos-taxis modélisés par zones (GTFS-Flex).

- Interurbain (F-15) depuis Adjamé et les autres gares routières.

- Serveur vocal, portail partenaires (6.4), publication d'un GTFS ouvert, paiement mobile money si partenariats, baoulé.

- Intégration du métro et du BRT dès la publication de leurs données, avec simulation de la restructuration du réseau de rabattement.

### 15.5 Définition de « terminé » pour chaque incrément

- Code relu avec une liste de contrôle, tests écrits et au vert, documentation à jour.

- Textes en clés de traduction, accessibilité vérifiée, budgets de performance respectés.

- Contrôle vie privée : toute nouvelle donnée collectée est ajoutée au registre.

- Fonctionnalité derrière un interrupteur de configuration ; événements de télémétrie définis.

- Démo reproductible en moins de 5 minutes, limites connues listées.

### 15.6 Ce que tu dois me signaler plutôt que décider seul

Nom et identité de marque ; choix du corridor pilote ; budget mensuel d'infrastructure et de canaux ; signature de partenariats (AMUGA, SOTRA, opérateurs télécoms, syndicats) ; hébergement et transferts de données ; validation juridique ; toute fonctionnalité qui pourrait mettre en danger un usager ou nuire aux transporteurs.

## Partie 16 — Glossaire et références

### 16.1 Glossaire du terrain

| Terme                          | Sens                                                                                                           |
|--------------------------------|----------------------------------------------------------------------------------------------------------------|
| Gbaka                          | Minibus de transport en commun de 18 à 32 places, souvent sur une ligne entre deux gares                       |
| Wôrô-wôrô                      | Taxi collectif de 4 passagers à itinéraire et prix forfaitaires ; communal (dans une commune) ou intercommunal |
| Taxi-compteur                  | Taxi individuel, rouge orangé à Abidjan, au compteur ou au prix négocié                                        |
| Badjan                         | Ancien véhicule de transport encore en service sur certaines lignes                                            |
| Moto-taxi, tricycle            | Transport à la demande en périphérie d'Abidjan et dans des villes comme Bouaké et Korhogo                      |
| Bateau-bus, pinasse            | Transport lagunaire, conventionné (SOTRA, STL, CITRANS) ou artisanal                                           |
| Apprenti                       | Assistant du chauffeur de gbaka : il appelle les passagers, annonce destination et prix, encaisse              |
| Coxer, chargeur                | Personne qui rabat les passagers vers un véhicule en gare contre rémunération                                  |
| Chef de gare                   | Responsable de l'ordre de chargement dans une gare artisanale                                                  |
| Gare                           | Lieu de chargement d'une ou plusieurs lignes artisanales, souvent informel                                     |
| Gare routière                  | Gare des compagnies interurbaines, par exemple à Adjamé                                                        |
| Terminus                       | Fin de ligne ; aussi nom d'arrêts SOTRA                                                                        |
| Recette                        | Somme que le chauffeur doit reverser chaque jour au propriétaire du véhicule                                   |
| Remonter à la gare             | Marcher vers la tête de ligne pour trouver une place quand les véhicules passent pleins                        |
| Monbus, Express, Monbato       | Services de bus et de bateau-bus de la SOTRA                                                                   |
| MonPass                        | Carte de transport sans contact de la SOTRA                                                                    |
| AMUGA                          | Autorité de la Mobilité Urbaine dans le Grand Abidjan, autorité organisatrice des 19 communes                  |
| ARTI                           | Autorité de Régulation du Transport Intérieur                                                                  |
| ARTCI                          | Autorité de régulation des télécommunications, aussi autorité de protection des données personnelles           |
| GTM                            | Groupe de travail de la mobilité, un par commune, animé par l'AMUGA                                            |
| PMUA                           | Projet de mobilité urbaine d'Abidjan, qui porte le BRT                                                         |
| AIM                            | Projet Abidjan Intermodalité : 32 pôles d'échanges et 180 points d'arrêt                                       |
| SMIG                           | Salaire minimum, 75 000 FCFA par mois depuis 2023                                                              |
| Nouchi                         | Argot urbain ivoirien                                                                                          |
| Dioula                         | Principale langue véhiculaire du pays                                                                          |
| GTFS, GTFS-Realtime, GTFS-Flex | Formats standard de description des réseaux, du temps réel et des services à la demande                        |
| RAPTOR, McRAPTOR               | Algorithmes de calcul d'itinéraire en transport en commun, simple ou multicritère                              |
| ADR                            | Architecture Decision Record : une décision d'architecture documentée                                          |

### 16.2 Sources de données et documents de référence

- GTFS « Abidjan 2023 » de DigitalTransport4Africa : [TUMI Data Hub](https://hub.tumidata.org/dataset/gtfs/resource/350ab9ce-73af-4033-a47c-0a0d0fee0015) et [Transitland](https://www.transit.land/places/Ivory%20Coast/Lagunes/Abidjan).

- OpenStreetMap : extrait Côte d'Ivoire (Geofabrik) et relations de lignes cartographiées par Jungle Bus.

- Gouvernance et chiffres de la mobilité : [CODATU, mandat de l'AMUGA, mars 2026](https://www.codatu.org/wp-content/uploads/2026/03/codatuabidjan-gouvernancemobilitega-vf.pdf) ; [AMUGA, services de transport](https://amuga.ci/services-de-transport/).

- Coût et pratiques de mobilité : [Banque mondiale 2019, synthèse WATHI](https://www.wathi.org/que-la-route-soit-bonne-ameliorer-la-mobilite-urbaine-a-abidjan-groupe-de-la-banque-mondiale-2019/).

- Cadre légal : [loi n°2013-450 sur les données personnelles](https://natlex.ilo.org/dyn/natlex2/r/natlex/fe/details?p3_isn=104182).

- Outil de validation : validateur GTFS canonique de MobilityData.

**Commence maintenant par ton premier message, tel que défini en 1.4 : reformulation, questions bloquantes, hypothèses par défaut et plan détaillé de la phase 0.**
