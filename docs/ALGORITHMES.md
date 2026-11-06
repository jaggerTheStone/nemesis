# Algorithmes

Version 0 du 2026-11-04 (incrément I0.3). Formules, hypothèses et paramètres des algorithmes de la partie 8. La méthode est celle de la partie 8 : une version de base simple et testée, mesurée contre la vérité terrain, puis améliorée.

Les paramètres marqués **à calibrer** ont une valeur de départ raisonnable, mais aucune mesure ne la confirme encore.

## Notations

- Les durées sont en minutes, les débits en événements par minute.
- p50 et p80 : 50e et 80e centiles.
- Gamma(*k*, λ) : loi Gamma de forme *k* et de taux λ. Pour *k* entier, c'est la durée d'attente de *k* événements d'un processus de Poisson de débit λ ; sa moyenne vaut *k*/λ.
- Les centiles de Gamma(*k*, 1) se divisent par λ pour obtenir ceux de Gamma(*k*, λ). Deux valeurs utiles :
  - Gamma(3, 1) : p50 = 2,674 et p80 = 4,279 ;
  - Gamma(5, 1) : p50 = 4,671 et p80 = 6,721.

## 1. Estimation de l'attente (8.2)

### 1.1 Choisir le régime

Pour chaque triplet arrêt, ligne et sens, et pour chaque tranche de 15 minutes :

| Régime | Quand | Exemple |
|--------|-------|---------|
| A | L'arrêt est la tête de ligne et `departs_when_full` = 1 | Gare de gbakas, tête de ligne de wôrô-wôrôs |
| C | Une part suffisante des véhicules de la ligne est suivie par GPS (SOTRA, BRT, métro, véhicules Pro), avec une position de moins de 2 min | Bus SOTRA suivi |
| B | Tous les autres cas | Arrêt informel en milieu de ligne |

Seuil proposé pour C : au moins 50 % des passages de la tranche observés par GPS. **À calibrer.**

### 1.2 Régime A : tête de ligne, départ au remplissage

**État** :
- *P* : passagers dans la file ;
- *V* : véhicules en chargement ;
- *C* : places par véhicule ;
- *r* : places libres dans le véhicule en chargement ;
- λp, λv : débits d'arrivée des passagers et des véhicules ;
- *d*₀ : délai entre le remplissage et le départ (**à calibrer**, proposition 1 min) ;
- *T*max : attente maximale observée avant un départ, même si le véhicule n'est pas plein.

**Cas 1 : des véhicules attendent des passagers** (*V* ≥ 1, *r* ≥ 1). Le nouveau passager monte tout de suite. Le véhicule part quand les *r* − 1 places restantes sont prises :

$$W \sim \min\big(\text{Gamma}(r-1,\ \lambda_p) + d_0,\ T_{\max}\big)$$

Si *r* = 1, *W* = *d*₀. La partie 8.2 donne l'ordre de grandeur (places restantes / λp) ; la loi Gamma précise la moyenne, (*r* − 1) / λp, et fournit en plus les centiles.

*Exemple* : *r* = 6, λp = 1,5 passager par minute. *W* − *d*₀ suit Gamma(5, 1,5) : p50 = 3,1 min, p80 = 4,5 min.

**Cas 2 : des passagers attendent des véhicules.** Soit *L* le nombre de places libres dans les véhicules présents. Il faut :

$$n = \left\lceil \frac{P + 1 - L}{C} \right\rceil \quad\text{véhicules supplémentaires,}\qquad W \sim \text{Gamma}(n,\ \lambda_v) + d_0$$

*Exemple* : *P* = 40, *L* = 0, *C* = 18, donc *n* = 3. Avec λv = 0,2 véhicule par minute (un toutes les 5 min), *W* − *d*₀ a pour p50 13,4 min, pour p80 21,4 min et pour moyenne 15 min.

**Hypothèse à vérifier** : les véhicules arrivent selon un processus de Poisson. S'ils arrivent plus régulièrement, la loi Gamma surestime la dispersion. Le simulateur (I0.10) et les comptages des Éclaireurs trancheront.

**Estimation des débits** (modèle conjugué Gamma-Poisson) :
- *a priori* tiré de l'historique de la tranche : λ ~ Gamma(α₀, β₀), avec α₀ = λhist · β₀. β₀ est une « exposition équivalente » ; proposition : 30 min, **à calibrer** ;
- après *k* événements observés pendant *t* minutes, la loi devient Gamma(α₀ + *k*, β₀ + *t*), de moyenne (α₀ + *k*) / (β₀ + *t*) ;
- oubli progressif : avant chaque mise à jour, *k* et *t* accumulés sont multipliés par e^(−Δt/τ), avec τ = la demi-vie du type d'information divisée par ln 2 ([DATA.md](DATA.md)).

**Lien avec les signalements** : les catégories de file se traduisent en fourchettes de *P*, tirées uniformément dans le calcul de Monte-Carlo :

| Catégorie signalée | *P* | Statut |
|--------------------|-----|--------|
| peu | 0 à 5 | **À calibrer** avec les comptages des Éclaireurs |
| moyen | 6 à 20 | idem |
| beaucoup | 21 à 50 | idem |
| très long | plus de 50 | idem |

Pour les véhicules présents : « aucun » donne *V* = 0, « 1 à 2 » donne *V* ∈ {1, 2}, « 3 et plus » donne *V* ≥ 3.

### 1.3 Régime B : bord de route

Les véhicules de la ligne passent au débit λpassage, avec une probabilité *q* d'avoir une place libre. Le débit utile vaut λ = λpassage × *q*. Si l'on suppose les passages aléatoires, l'attente suit une loi exponentielle :

$$p_{50} = \frac{\ln 2}{\lambda}, \qquad p_{80} = \frac{\ln 5}{\lambda}$$

En effet, 1 − e^(−λw) = 0,8 donne λw = ln 5.

*Exemple* : 12 véhicules par heure et *q* = 0,25, donc λ = 3 par heure. On obtient p50 = 13,9 min, p80 = 32,2 min, moyenne 20 min.

**Passages réguliers.** Si les intervalles entre véhicules ont pour moyenne *H* et pour coefficient de variation *CV*, l'attente moyenne vaut :

$$E[W] = \frac{H}{2}\,(1 + CV^2)$$

Le cas exponentiel correspond à *CV* = 1, et donne E[W] = *H*. Tant que *CV* n'est pas mesuré, on garde le cas exponentiel, plus prudent. Ensuite, on ajuste une loi Gamma aux intervalles.

**Estimation de *q*.** On la tire des signalements « véhicule plein » et des montées observées, rapportés aux passages. *q* baisse avec la distance à la tête de ligne et en pointe : on l'estime par tronçon et par tranche.

### 1.4 Régime C : lignes suivies par GPS

*W* est l'heure d'arrivée prévue du premier véhicule qui a de la place, calculée à partir des positions et du modèle de vitesse par tronçon (section 6). On tire les temps de parcours par tronçon d'une loi log-normale ajustée sur l'historique. Si l'occupation est inconnue, on applique *q*.

### 1.5 Couche d'apprentissage automatique (V2)

Régression par quantiles par gradient boosting (par exemple LightGBM), qui prédit le p50 et le p80 de l'attente et les débits.

- **Variables** (8.2) :
  - gare, ligne, sens, tranche de 15 min ;
  - type de jour, avec indicateurs de vacances scolaires et de fin de mois ;
  - pluie actuelle et de la dernière heure ;
  - événements, incidents ;
  - signalements récents, débit GPS récent.
- **Démarrage à froid** : a priori hiérarchiques (commune, puis mode) avec mise en commun partielle.
- **Réentraînement** : quotidien.
- **Mise en service** : le modèle ne remplace les formules d'un régime que s'il fait mieux qu'elles sur les données passées (section 8), et s'il reste calibré.

### 1.6 Poids et fusion des observations (7.5)

**Poids d'une observation** :

$$w = \underbrace{\frac{a}{a+b}}_{\text{réputation}} \times s_{\text{source}} \times 2^{-\text{âge}/h} \times \text{plausibilité}$$

| Terme | Définition | Valeur de départ |
|-------|------------|------------------|
| Réputation | Loi Bêta(*a*, *b*) par contributeur. Un nouveau compte part de Bêta(1, 3), soit un poids de 0,25. +1 sur *a* si l'observation concorde avec le consensus ou la vérité terrain, +1 sur *b* sinon | **À calibrer** |
| *s*source | Usager : 1 ; chef de gare vérifié et Éclaireur : 3 ; GPS du mode Pro : 2 | **À calibrer** |
| *h* | Demi-vie du type d'information ([DATA.md](DATA.md)) | 10 min pour une file en pointe |
| Plausibilité | 0 (observation rejetée) si l'appareil est à plus de 150 m de la gare, en cas de vitesse impossible ou de téléportation. Sinon 1, ou moins pour une valeur atypique | 150 m (7.4) |

**Fusion des catégories de file** (modèle de Dirichlet et multinomial) :

$$\alpha_c = \alpha_c^{\text{hist}} + \sum_i w_i\,\mathbb{1}[\text{catégorie}_i = c]$$

- *a priori* : la distribution historique des catégories de la tranche, avec une concentration totale de 2 (**à calibrer**) ;
- état publié : la catégorie la plus probable ;
- confiance : dérivée de la concentration totale et de la part de la catégorie publiée ([DATA.md](DATA.md), section « Confiance »).

### 1.7 Conseil « remonter à la gare », corrigé

La partie 8.2 propose de conseiller de remonter à la gare quand « marche jusqu'à la tête de ligne + attente en gare » est inférieure de plus de 5 min à l'attente au bord de la route.

**Correction signalée (règle 1.3.8).** Cette comparaison oublie le trajet en véhicule entre la tête de ligne et le point où l'on se trouve. Après être monté en gare, on repasse par ce point. La comparaison juste porte sur l'**heure de passage au point de départ** :

$$\text{marche} + W_{\text{gare}} + \text{trajet}(\text{gare} \to \text{point}) \;<\; W_{\text{bord de route}} - 5\ \text{min}$$

Les deux côtés sont comparés au p50, et on vérifie aussi que le p80 n'est pas pire.

Dans les faits, le moteur d'itinéraires fait cette comparaison de lui-même : « marcher jusqu'à la gare » est simplement une option de plus dans le front de Pareto. Le conseil explicite n'est qu'une façon de présenter cette option quand elle gagne.

### 1.8 Calibration surveillée

**Objectif (8.2)** : la vraie attente est inférieure au p80 annoncé dans 78 à 82 % des cas.

**La taille d'échantillon compte.** Avec *n* attentes déclarées, l'intervalle de confiance à 95 % d'une proportion proche de 0,8 a une demi-largeur de 1,96 × √(0,16 / *n*) :
- pour *n* = 400, cela fait ±3,9 points : on ne peut pas trancher entre 78 % et 82 % ;
- pour une précision de ±2 points, il faut environ **1 540 attentes** par fenêtre d'évaluation.

**Règle d'alerte proposée** :
- calcul de la couverture sur une fenêtre glissante, par régime ;
- alerte seulement quand l'intervalle de Wilson à 95 % est **entièrement** hors de la bande [78 %, 82 %] ;
- tant que *n* est faible, on publie la couverture avec son intervalle, sans alerte.

## 2. Calcul d'itinéraire (8.1)

### 2.1 Critères et algorithme

**Critères** (8.1) :
- temps total au p80 ;
- temps total au p50 ;
- coût au p50 ;
- nombre de changements ;
- minutes de marche ;
- la nuit (V2), une pénalité de sûreté : arrêts non éclairés, incidents récents.

**Algorithme : McRAPTOR sur un réseau à fréquences** (ADR-003).
- **Coût de montée** : la loi d'attente de la section 1 à l'arrêt, au moment estimé du passage.
- **Montée et descente continues** : points de montée virtuels tous les 150 à 300 m le long du tracé, placés là où l'on monte réellement (relevés des Éclaireurs, contributions).
- **Marche** : graphe piéton OSM.
  - Vitesse par défaut 4,5 km/h, 3 km/h pour le profil mobilité réduite (**à calibrer**).
  - Pénalité pour les traversées dangereuses (phase 1).
  - **Exclusion stricte** des zones signalées comme inondées (12.4).
- **Temps à bord** : vitesses par tronçon et par tranche de 15 min (section 6), plus un temps d'arrêt par type de véhicule.

**Mise en œuvre v0 (I0.9, `services/routing`).**
- Quatre critères dans la recherche : arrivée calculée avec les attentes médianes, prix p50, mètres de marche, nombre de véhicules. Les p50 et p80 du temps total viennent ensuite du Monte-Carlo (section 2.2).
- La marche est comparée par tranches de 250 m, soit environ 3 min (**à calibrer**, H-032). Sans ces tranches, le front gardait des trajets à quatre correspondances pour économiser 50 m de marche, et la requête médiane passait de 49 à 404 ms sur le GTFS 2023.
- Un prix inconnu sur une étape rend le prix du trajet inconnu ; il n'est alors comparé à aucun autre, pour ne jamais masquer un prix connu.
- Chaque arrêt tient deux ensembles de Pareto : les arrivées en véhicule, qui peuvent rejoindre la destination ou continuer à pied, et toutes les étiquettes qui peuvent monter à cet arrêt. Une arrivée à pied ne peut donc pas éliminer une arrivée en véhicule (défaut trouvé par le test de symétrie).
- Une correspondance à pied ne part que d'une arrivée en véhicule : jamais deux marches à la suite.
- Bornes de marche : 1,5 km pour l'accès et la sortie, 500 m pour une correspondance, 2 km pour un trajet tout à pied ; Dijkstra sur le graphe du pack, rattachement des points à moins de 200 m, sinon ligne droite × 1,3 (l'étape l'indique).
- Attente : régime A quand un profil existe pour l'arrêt, la ligne, le sens, le type de jour et le créneau de 15 min ; sinon régime B depuis l'intervalle du GTFS. En v0, le régime A est une loi log-normale ajustée sur le p50 et le p80 du profil, en attendant la loi Gamma de la section 1.2.

### 2.2 Incertitude par Monte-Carlo

**Principe.** Pour chaque option candidate, 500 tirages de la somme marche + attentes + temps à bord donnent le p50 et le p80.

**Erreur d'estimation.** L'erreur type sur le rang du p80 vaut √(0,8 × 0,2 / 500) ≈ 0,018, soit environ ±1,8 point de centile : c'est suffisant.

**Indépendance.** Les tirages des différentes étapes sont supposés indépendants. C'est une simplification, car un embouteillage rallonge à la fois l'attente et le trajet. On la vérifie en comparant la couverture du p80 des itinéraires complets (section 8).

**Déterminisme.** La graine vaut hachage(requête, version du réseau, version de l'état en direct). Ainsi le serveur et le téléphone produisent les mêmes centiles pour les mêmes données (parité, [ARCHITECTURE.md](ARCHITECTURE.md)).

### 2.3 Choisir les options étiquetées

1. **Front de Pareto** : on garde les options non dominées.
2. **Quasi-doublons** : on écarte une option qui reprend la même suite de lignes qu'une autre et la vaut à 2 min et 50 F près (**à calibrer**).
3. **Étiquettes** :
   - « Le moins cher » : coût p50 minimal, puis temps p80 ;
   - « Le plus rapide » : temps p80 minimal ;
   - « Le plus simple » : changements minimaux, puis marche ;
   - « Le plus sûr » le soir (V2).
4. Une même option peut porter plusieurs étiquettes. On affiche au moins trois options distinctes quand elles existent.

**Mise en œuvre v0.** Le Pareto des options simulées porte sur p80, p50, prix, véhicules et marche par tranches de 250 m. « Le plus simple » compte la marche par tranches de 375 m (5 min) après le nombre de véhicules, puis le p80. Une option sans étiquette n'est montrée que si son p80 reste sous 1,5 × le meilleur p80 + 15 min, et au plus cinq options sont affichées (**à calibrer**, H-032). La graine est un hachage FNV-1a de la requête et de la version du réseau (pas encore d'état en direct).

### 2.4 Tests par propriétés (14.1)

- Aucune option affichée n'est dominée.
- Ajouter une ligne ne dégrade jamais la meilleure valeur d'aucun critère.
- Aller et retour restent raisonnablement symétriques, hors sens uniques et lignes à sens unique.
- Le même calcul donne les mêmes résultats sur le serveur et sur le téléphone.

## 3. Prix (8.3)

- **Estimation** par ligne, zone d'origine, zone de destination et condition (pointe, pluie, nuit, fête) : centiles pondérés p10, p50 et p90 des prix observés, avec les poids de la section 1.6 et une demi-vie de 30 jours.
- **Multiplicateurs de condition** : *m*c = médiane(prix | *c*) / médiane(prix | normale), estimés globalement puis par ligne quand les données suffisent. Ils servent quand une condition manque d'observations.
- **Rupture de niveau** (hausse du carburant, réorganisation) : CUSUM sur les écarts au p50 courant.
  - *S*t = max(0, *S*t−1 + (*x*t − μ₀ − *k*)), avec *k* = 0,5 σ ;
  - alarme quand *S*t > *h*, avec *h* = 5 σ (**à calibrer**) ;
  - à l'alarme, les anciennes observations vieillissent plus vite (demi-vie divisée par 4) pour adopter le nouveau niveau.
- **Affichage** : fourchette du p10 arrondi à 50 F en dessous au p90 arrondi à 50 F au-dessus (« 300 à 400 F »). « Prix inconnu » s'il n'y a pas d'observation (H-018). La règle de l'avertissement « prépare la monnaie » est à définir avec les retours du terrain.
- **Comparaison avec le VTC et le taxi-compteur** : estimation par distance et par durée, à partir de grilles observées, présentée comme indicative.

## 4. Géocodage par repères (8.4)

1. **Normalisation** :
   - mettre en minuscules et retirer les accents (« wôrô » devient « woro ») ;
   - retirer la ponctuation et les mots vides (« le », « la », « de ») ;
   - développer les abréviations (« Yop », « Adj », « Koum », « Sipo »), à partir du dictionnaire construit sur le jeu de développement des requêtes réelles (H-026).
2. **Candidats** : similarité par trigrammes (pg_trgm sur le serveur ; FTS5 et index de trigrammes sur le téléphone), clé phonétique, synonymes.
3. **Clé phonétique adaptée au français parlé en Côte d'Ivoire** : à concevoir et à tester sur le jeu de développement, jamais sur le jeu de test (H-026).
4. **Classement** : score = *a* · similarité + *b* · popularité + *c* · proximité. Poids **à calibrer** sur le jeu de développement.
5. **Expressions relatives** (« derrière », « en face de », « après le carrefour ») : le résultat est un point d'ancrage plus une zone d'incertitude. Proposition : un rayon de 150 m, orienté quand l'expression le permet.
6. **Mesure** : réussite au premier essai sur le jeu de test de 300 requêtes ; objectif 90 % (F-01).

## 5. Détection de la montée, du mode et de la descente, sur le téléphone (8.5)

- **Modèle de Markov caché** :
  - états : à pied, en attente à un arrêt, à bord de la ligne *r* (un état par ligne proche), autre véhicule ;
  - observations : vitesse et précision GPS, reconnaissance d'activité du système, distance aux tracés et aux arrêts, profil d'arrêts et de redémarrages, présence sur l'eau près d'un embarcadère ;
  - décodage par l'algorithme de Viterbi sur une fenêtre glissante.
- **Montée** : passage de « à pied » ou « en attente » à « à bord », près d'un arrêt ou d'un point de montée. **Descente** : l'inverse.
- **Batterie** : échantillonnage toutes les 5 à 15 s à bord, toutes les 30 s à l'arrêt ; localisation fusionnée en mode économe ; géorepérage pour l'alerte de descente, déclenchée deux arrêts avant.
- **Critères (F-04)** : alerte au bon arrêt dans au moins 95 % des cas ; moins de 4 % de batterie par heure.

## 6. Position des véhicules et congestion (8.6)

- **Regroupement** : les usagers d'une même ligne dont les positions et les vitesses sont proches forment un véhicule inféré.
- **Fusion** avec les positions du mode Pro et des partenaires, lissage par filtre de Kalman le long du tracé, extrapolation quand la donnée vieillit, disparition après le délai de la catégorie ([DATA.md](DATA.md)).
- **Vitesses** par tronçon OSM et par tranche de 15 min, comparées à la vitesse libre (couche congestion), avec une loi log-normale des temps de parcours pour le Monte-Carlo.

## 7. Carte de la demande pour les chauffeurs (8.7)

Par gare et par arrêt : le nombre de personnes en attente, en catégories arrondies, et une prévision à 30 min (historique, signalements récents, pluie). **Jamais un point qui représente une personne.** On n'affiche pas de catégorie tant qu'elle ne repose pas sur au moins 3 signalements distincts (**à calibrer**), pour qu'on ne puisse pas deviner un signalement isolé.

## 8. Évaluation (8.8)

| Mesure | Définition | Cible (14.2) |
|--------|------------|--------------|
| Erreur absolue médiane de l'attente | médiane de \|attente prévue (p50) − attente réelle\| | 5 min au plus avec données en direct, 10 min avec l'historique seul |
| Calibration | part des attentes réelles sous le p80 annoncé, avec son intervalle de Wilson (section 1.8) | 78 % à 82 % |
| Justesse des prix | part des prix payés dans la fourchette p10 à p90 | 80 % au moins |
| Réalisme des itinéraires | règle de notation de la suite de référence ([protocole](TERRAIN/PROTOCOLE-TRAJETS-REFERENCE.md)) | 85 % au moins |
| Géocodage | réussite au premier essai sur le jeu de test | 90 % au moins |

- **Rétro-tests** sur les données passées, à chaque modification d'un modèle.
- **Tests A/B** des règles de tri des options.
- **Simulateur** (I0.10) : il confronte les formules des régimes A et B à une vérité simulée avant d'avoir des données de terrain.

## Paramètres de départ

| Paramètre | Valeur | Statut |
|-----------|--------|--------|
| *d*₀, délai entre le remplissage et le départ | 1 min | À calibrer |
| β₀, exposition équivalente de l'a priori | 30 min | À calibrer |
| Fourchettes de *P* par catégorie de file | 0 à 5, 6 à 20, 21 à 50, plus de 50 | À calibrer (Éclaireurs) |
| Seuil GPS pour le régime C | 50 % des passages | À calibrer |
| Réputation initiale | Bêta(1, 3) | À calibrer |
| Poids des sources | usager 1, Pro 2, chef de gare et Éclaireur 3 | À calibrer |
| Concentration de l'a priori des catégories | 2 | À calibrer |
| Distance maximale d'un signalement | 150 m | Partie 7.4, ajustable |
| Tirages de Monte-Carlo | 500 | Partie 8.1 |
| Vitesse de marche | 4,5 km/h ; 3 km/h en mobilité réduite | À calibrer |
| Tolérance des quasi-doublons | 2 min, 50 F | À calibrer |
| Tranche de comparaison de la marche (recherche et Pareto) | 250 m | À calibrer (H-032) |
| Options sans étiquette | p80 ≤ 1,5 × meilleur p80 + 15 min ; 5 options au plus | À calibrer (H-032) |
| Marche : accès et sortie, correspondance, tout à pied | 1,5 km, 500 m, 2 km | À calibrer (H-032) |
| Rattachement au graphe piéton | 200 m | À calibrer (H-032) |
| Facteur de détour hors graphe | 1,3 | À calibrer |
| CUSUM des prix | *k* = 0,5 σ, *h* = 5 σ | À calibrer |
| Rayon des expressions relatives | 150 m | À calibrer |
| Signalements minimaux pour la carte de la demande | 3 | À calibrer |
