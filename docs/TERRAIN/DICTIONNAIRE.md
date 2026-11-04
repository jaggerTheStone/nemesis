# Dictionnaire des données de terrain

<!-- Fichier généré par `uv run nemesis-terrain generer` à partir des schémas de
     data/pipelines/src/nemesis_pipelines/terrain/schemas/ : ne pas le modifier à la main. -->

Règles communes à tous les fichiers :

- CSV en UTF-8, séparateur « ; » (celui des modèles) ou « , ».
- Saisir les **codes** (sans accent), jamais les libellés ; le validateur propose le bon code en cas d'erreur.
- Plusieurs valeurs dans une cellule : séparées par « + ».
- Dates au format AAAA-MM-JJ, heures au format HH:MM.
- Colonne facultative `is_fictional` : `true` uniquement dans `data/fixtures_fictives`.
- Un fichier par jeu et par lot est permis : `requetes-2026-11-20-E01.csv` appartient au jeu `requetes`.
- Colonne « Saisie » : *terrain* = noté sur la fiche papier ; *bureau* = ajouté à la saisie.

Vérification : `uv run nemesis-terrain valider data/terrain/collecte`.

## Requêtes réelles de destination (`requetes.csv`)

Jeu d'évaluation du géocodage (F-01) : au moins 90 % de réussite au premier essai sur 300 requêtes réelles.

- Protocole : [PROTOCOLE-REQUETES.md](../../docs/TERRAIN/PROTOCOLE-REQUETES.md)
- Fiches papier : [fiche-requetes.html](../../docs/TERRAIN/fiches/fiche-requetes.html)
- Modèle : [requetes.csv](../../data/terrain/modeles/requetes.csv)
- Identifiant unique : `id`

| Colonne | Libellé | Type | Obligatoire | Saisie | Contraintes | Aide |
|---------|---------|------|-------------|--------|-------------|------|
| `id` | Identifiant | code | oui | bureau | format `RQ-[0-9]{4}` | Attribué à la saisie, unique dans tout le jeu : RQ-0001, RQ-0002… |
| `date` | Date de l'enquête | date AAAA-MM-JJ | oui | terrain |  |  |
| `heure` | Heure | heure HH:MM | non | terrain |  |  |
| `enqueteur` | Code enquêteur | code | oui | terrain | format `E[0-9]{2}` | Code attribué à l'enquêteur (E01, E02…), jamais son nom. |
| `lieu_enquete` | Lieu de l'enquête | texte | oui | terrain | 120 caractères au plus | Gare, marché ou arrêt où l'enquête a lieu. |
| `commune_enquete` | Commune du lieu de l'enquête | valeur de liste | oui | terrain | codes : [communes](#referentiel-communes) |  |
| `formulation` | Formulation exacte | texte | oui | terrain | 200 caractères au plus | Mot pour mot, sans corriger l'orthographe ni ajouter d'accents : « Adj Liberté », « derrière pharmacie Sipo ». |
| `mode_saisie` | Dit ou écrit | valeur de liste | oui | terrain | codes : [modes_saisie](#referentiel-modes_saisie) |  |
| `langue` | Langue | valeur de liste | oui | terrain | codes : [langues_requete](#referentiel-langues_requete) |  |
| `type_lieu` | Type de lieu visé | valeur de liste | oui | terrain | codes : [types_lieu](#referentiel-types_lieu) |  |
| `expression_relative` | Expression relative | valeur de liste | oui | terrain | codes : [expressions_relatives](#referentiel-expressions_relatives) | « derrière », « en face de »… ; « aucune » sinon. |
| `lieu_compris` | Lieu visé, confirmé avec la personne | texte | oui | terrain | 200 caractères au plus | Ce que la personne voulait dire, vérifié avec elle (« Vous voulez dire… ? »). Jamais une adresse privée : le repère public le plus proche. |
| `commune_visee` | Commune du lieu visé | valeur de liste | oui | terrain | codes : [communes](#referentiel-communes) ; ou `inconnue` |  |
| `latitude` | Latitude du lieu visé | nombre décimal | non | bureau | de 4.3 à 10.8 | Ajoutée au bureau à partir d'une carte, en degrés décimaux (WGS 84). |
| `longitude` | Longitude du lieu visé | nombre décimal | non | bureau | de -8.7 à -2.4 |  |
| `remarques` | Remarques | texte | non | terrain | 300 caractères au plus |  |

Règles :

- Renseigner ensemble ou laisser vides : `latitude`, `longitude`.

## Trajets de référence (`trajets.csv`)

Suite de non-régression du moteur d'itinéraires (partie 14.1) : au moins 85 % des options proposées jugées réalistes.

- Protocole : [PROTOCOLE-TRAJETS-REFERENCE.md](../../docs/TERRAIN/PROTOCOLE-TRAJETS-REFERENCE.md)
- Fiches papier : [fiche-trajet-reference.html](../../docs/TERRAIN/fiches/fiche-trajet-reference.html)
- Modèle : [trajets.csv](../../data/terrain/modeles/trajets.csv)
- Identifiant unique : `id`

| Colonne | Libellé | Type | Obligatoire | Saisie | Contraintes | Aide |
|---------|---------|------|-------------|--------|-------------|------|
| `id` | Identifiant du trajet | code | oui | bureau | format `TR-[0-9]{3}` | TR-001 à TR-200. Un identifiant n'est jamais réutilisé. |
| `origine` | Départ | texte | oui | terrain | 160 caractères au plus | Repère public tel qu'on le dit à Abidjan. |
| `origine_commune` | Commune de départ | valeur de liste | oui | terrain | codes : [communes](#referentiel-communes) |  |
| `origine_latitude` | Latitude du départ | nombre décimal | non | bureau | de 4.3 à 10.8 |  |
| `origine_longitude` | Longitude du départ | nombre décimal | non | bureau | de -8.7 à -2.4 |  |
| `destination` | Arrivée | texte | oui | terrain | 160 caractères au plus |  |
| `destination_commune` | Commune d'arrivée | valeur de liste | oui | terrain | codes : [communes](#referentiel-communes) |  |
| `destination_latitude` | Latitude de l'arrivée | nombre décimal | non | bureau | de 4.3 à 10.8 |  |
| `destination_longitude` | Longitude de l'arrivée | nombre décimal | non | bureau | de -8.7 à -2.4 |  |
| `heure_depart` | Heure de départ | heure HH:MM | oui | terrain |  |  |
| `type_jour` | Type de jour | valeur de liste | oui | terrain | codes : [types_jour](#referentiel-types_jour) |  |
| `conditions` | Conditions particulières | liste séparée par « + » | non | terrain | codes : [conditions](#referentiel-conditions) | Plusieurs valeurs séparées par « + » : pluie+fin_de_mois. |
| `profil` | Profil de l'usager | valeur de liste | oui | terrain | codes : [profils](#referentiel-profils) |  |
| `validateurs` | Codes des validateurs | liste séparée par « + » | oui | terrain | format `V[0-9]{2}` ; au moins 2 éléments ; éléments distincts | Au moins deux personnes qui font ce trajet, codes séparés par « + » : V01+V07. |
| `date_validation` | Date de validation | date AAAA-MM-JJ | oui | terrain |  |  |
| `remarques` | Remarques | texte | non | terrain | 300 caractères au plus |  |

Règles :

- Renseigner ensemble ou laisser vides : `origine_latitude`, `origine_longitude`.
- Renseigner ensemble ou laisser vides : `destination_latitude`, `destination_longitude`.
- Chaque trajet doit avoir au moins une réponse acceptable dans reponses.csv.

## Réponses des trajets de référence (`reponses.csv`)

Réponses jugées acceptables par des habitants, et pièges à ne jamais proposer, pour chaque trajet de référence.

- Protocole : [PROTOCOLE-TRAJETS-REFERENCE.md](../../docs/TERRAIN/PROTOCOLE-TRAJETS-REFERENCE.md)
- Fiches papier : [fiche-trajet-reference.html](../../docs/TERRAIN/fiches/fiche-trajet-reference.html)
- Modèle : [reponses.csv](../../data/terrain/modeles/reponses.csv)
- Identifiant unique : `trajet_id` + `reponse_no`
- `trajet_id` doit exister dans `trajets.csv`, dans le même dossier

| Colonne | Libellé | Type | Obligatoire | Saisie | Contraintes | Aide |
|---------|---------|------|-------------|--------|-------------|------|
| `trajet_id` | Identifiant du trajet | code | oui | bureau | format `TR-[0-9]{3}` |  |
| `reponse_no` | Numéro de la réponse | nombre entier | oui | bureau | de 1 à 9 | Numéro du bloc sur la fiche (1, 2, 3…). |
| `statut` | Statut | valeur de liste | oui | terrain | codes : [statuts_reponse](#referentiel-statuts_reponse) | « piege » : réponse plausible mais fausse (ligne supprimée, accès interdit…) que le moteur ne doit jamais proposer. |
| `categories` | Étiquettes visées | liste séparée par « + » | non | terrain | codes : [categories_reponse](#referentiel-categories_reponse) | Étiquettes auxquelles cette réponse correspond : moins_cher+plus_simple. |
| `etape1_mode` | Étape 1 : véhicule | valeur de liste | non | terrain | codes : [modes](#referentiel-modes) |  |
| `etape1_montee` | Étape 1 : où monter | texte | non | terrain | 120 caractères au plus |  |
| `etape1_ligne` | Étape 1 : ligne ou destination annoncée | texte | non | terrain | 120 caractères au plus | Comme on la dit ou comme l'apprenti la crie. |
| `etape1_descente` | Étape 1 : où descendre | texte | non | terrain | 120 caractères au plus |  |
| `etape2_mode` | Étape 2 : véhicule | valeur de liste | non | terrain | codes : [modes](#referentiel-modes) |  |
| `etape2_montee` | Étape 2 : où monter | texte | non | terrain | 120 caractères au plus |  |
| `etape2_ligne` | Étape 2 : ligne ou destination annoncée | texte | non | terrain | 120 caractères au plus | Comme on la dit ou comme l'apprenti la crie. |
| `etape2_descente` | Étape 2 : où descendre | texte | non | terrain | 120 caractères au plus |  |
| `etape3_mode` | Étape 3 : véhicule | valeur de liste | non | terrain | codes : [modes](#referentiel-modes) |  |
| `etape3_montee` | Étape 3 : où monter | texte | non | terrain | 120 caractères au plus |  |
| `etape3_ligne` | Étape 3 : ligne ou destination annoncée | texte | non | terrain | 120 caractères au plus | Comme on la dit ou comme l'apprenti la crie. |
| `etape3_descente` | Étape 3 : où descendre | texte | non | terrain | 120 caractères au plus |  |
| `etape4_mode` | Étape 4 : véhicule | valeur de liste | non | terrain | codes : [modes](#referentiel-modes) |  |
| `etape4_montee` | Étape 4 : où monter | texte | non | terrain | 120 caractères au plus |  |
| `etape4_ligne` | Étape 4 : ligne ou destination annoncée | texte | non | terrain | 120 caractères au plus | Comme on la dit ou comme l'apprenti la crie. |
| `etape4_descente` | Étape 4 : où descendre | texte | non | terrain | 120 caractères au plus |  |
| `duree_min_minutes` | Durée totale minimale (min) | nombre entier | non | terrain | de 1 à 300 | Porte à porte, attente comprise. |
| `duree_max_minutes` | Durée totale maximale (min) | nombre entier | non | terrain | de 1 à 300 |  |
| `prix_min_fcfa` | Prix total minimal (FCFA) | nombre entier | non | terrain | de 0 à 20000 |  |
| `prix_max_fcfa` | Prix total maximal (FCFA) | nombre entier | non | terrain | de 0 à 20000 |  |
| `marche_max_minutes` | Marche totale maximale (min) | nombre entier | non | terrain | de 0 à 120 |  |
| `justification` | Justification | texte | oui | terrain | 400 caractères au plus | Pourquoi cette réponse est acceptable, ou pourquoi c'est un piège. |

Règles :

- Étapes `etape1` à `etape4` : la première est obligatoire, elles se suivent sans trou, et chaque étape remplie a mode, montee, descente.
- `duree_min_minutes`, `duree_max_minutes`, `prix_min_fcfa`, `prix_max_fcfa` obligatoires quand `statut` = `acceptable`.
- `duree_min_minutes` ≤ `duree_max_minutes`.
- `prix_min_fcfa` ≤ `prix_max_fcfa`.

## Participants aux tests utilisateurs (`participants.csv`)

Profil anonyme des participants (partie 10.1) : vérifier la composition des groupes (au moins 2 personnes qui lisent difficilement et 1 personne âgée par tour).

- Protocole : [PROTOCOLE-TESTS-MAQUETTES.md](../../docs/UX/PROTOCOLE-TESTS-MAQUETTES.md)
- Fiches papier : [fiche-test-maquettes.html](../../docs/TERRAIN/fiches/fiche-test-maquettes.html), [fiche-test-icones.html](../../docs/TERRAIN/fiches/fiche-test-icones.html)
- Modèle : [participants.csv](../../data/terrain/modeles/participants.csv)
- Identifiant unique : `session` + `participant`

| Colonne | Libellé | Type | Obligatoire | Saisie | Contraintes | Aide |
|---------|---------|------|-------------|--------|-------------|------|
| `session` | Code de session | code | oui | terrain | format `S[0-9]{8}-[0-9]{2}` | S + date AAAAMMJJ + numéro : S20261120-01. |
| `participant` | Code participant | code | oui | terrain | format `P[0-9]{2}` | P01, P02… dans la session. Aucune table ne relie ce code à une identité. |
| `consentement_oral` | Consentement oral recueilli | valeur de liste | oui | terrain | codes : [oui_non](#referentiel-oui_non) |  |
| `tranche_age` | Tranche d'âge | valeur de liste | oui | terrain | codes : [tranches_age](#referentiel-tranches_age) |  |
| `lecture` | Lecture (déclarée) | valeur de liste | oui | terrain | codes : [lectures](#referentiel-lectures) |  |
| `telephone` | Téléphone utilisé | valeur de liste | oui | terrain | codes : [telephones](#referentiel-telephones) |  |
| `langue_preferee` | Langue préférée | valeur de liste | oui | terrain | codes : [langues](#referentiel-langues) |  |
| `lieu_session` | Lieu de la session | texte | oui | terrain | 120 caractères au plus |  |
| `enqueteur` | Code de l'animateur | code | oui | terrain | format `E[0-9]{2}` |  |

Règles :

- `consentement_oral` doit valoir `oui` : sans consentement, aucune donnée ne doit être saisie : supprimer la ligne.

## Observations du test de maquettes (`observations.csv`)

Réussite des tâches tirées des parcours clés (partie 4.2) sur le prototype.

- Protocole : [PROTOCOLE-TESTS-MAQUETTES.md](../../docs/UX/PROTOCOLE-TESTS-MAQUETTES.md)
- Fiches papier : [fiche-test-maquettes.html](../../docs/TERRAIN/fiches/fiche-test-maquettes.html)
- Modèle : [observations.csv](../../data/terrain/modeles/observations.csv)
- Identifiant unique : `session` + `participant` + `tache`
- `session` + `participant` doit exister dans `participants.csv`, dans le même dossier

| Colonne | Libellé | Type | Obligatoire | Saisie | Contraintes | Aide |
|---------|---------|------|-------------|--------|-------------|------|
| `session` | Code de session | code | oui | terrain | format `S[0-9]{8}-[0-9]{2}` |  |
| `participant` | Code participant | code | oui | terrain | format `P[0-9]{2}` |  |
| `tache` | Tâche | valeur de liste | oui | terrain | codes : [taches](#referentiel-taches) |  |
| `reussite` | Résultat | valeur de liste | oui | terrain | codes : [reussites](#referentiel-reussites) |  |
| `duree_secondes` | Durée (secondes) | nombre entier | non | terrain | de 0 à 3600 |  |
| `pressions` | Nombre de pressions | nombre entier | non | terrain | de 0 à 200 | Surtout pour T4 : la contribution doit tenir en deux pressions (F-07). |
| `aide_donnee` | Aide donnée | texte | non | terrain | 300 caractères au plus |  |
| `notes` | Observations | texte | non | terrain | 600 caractères au plus | Hésitations, erreurs, phrases dites par la personne (sans élément d'identité). |
| `observateur` | Code de l'observateur | code | oui | terrain | format `E[0-9]{2}` |  |

## Test de reconnaissance des icônes (`icones.csv`)

Chaque icône de mode et d'action doit être reconnue sans légende par au moins 85 % de 20 personnes (partie 10.1).

- Protocole : [PROTOCOLE-TESTS-MAQUETTES.md](../../docs/UX/PROTOCOLE-TESTS-MAQUETTES.md)
- Fiches papier : [fiche-test-icones.html](../../docs/TERRAIN/fiches/fiche-test-icones.html)
- Modèle : [icones.csv](../../data/terrain/modeles/icones.csv)
- Identifiant unique : `session` + `participant` + `icone` + `version_icone`
- `session` + `participant` doit exister dans `participants.csv`, dans le même dossier

| Colonne | Libellé | Type | Obligatoire | Saisie | Contraintes | Aide |
|---------|---------|------|-------------|--------|-------------|------|
| `session` | Code de session | code | oui | terrain | format `S[0-9]{8}-[0-9]{2}` |  |
| `participant` | Code participant | code | oui | terrain | format `P[0-9]{2}` |  |
| `icone` | Icône | valeur de liste | oui | terrain | codes : [icones](#referentiel-icones) |  |
| `version_icone` | Version du jeu d'icônes | code | oui | terrain | format `v[0-9]+` |  |
| `reponse` | Réponse mot pour mot | texte | oui | terrain | 200 caractères au plus |  |
| `reconnue` | Codage | valeur de liste | oui | terrain | codes : [reconnaissances](#referentiel-reconnaissances) | Selon le guide de codage du protocole ; en cas de doute, « partiel » et second codeur. |
| `codeur` | Code du codeur | code | oui | terrain | format `E[0-9]{2}` |  |

## Référentiels

<a id="referentiel-communes"></a>

### communes

| Code | Libellé |
|------|---------|
| `abobo` | Abobo |
| `adjame` | Adjamé |
| `anyama` | Anyama |
| `attecoube` | Attécoubé |
| `bingerville` | Bingerville |
| `cocody` | Cocody |
| `koumassi` | Koumassi |
| `marcory` | Marcory |
| `plateau` | Plateau |
| `port_bouet` | Port-Bouët |
| `songon` | Songon |
| `treichville` | Treichville |
| `yopougon` | Yopougon |
| `autre` | Autre (préciser en remarque) |

<a id="referentiel-modes"></a>

### modes

| Code | Libellé |
|------|---------|
| `bus_sotra` | Bus SOTRA |
| `bus_express` | Bus express |
| `bateau_bus` | Bateau-bus |
| `pinasse` | Pinasse |
| `gbaka` | Gbaka |
| `woro_communal` | Wôrô-wôrô communal |
| `woro_intercommunal` | Wôrô-wôrô intercommunal |
| `taxi_compteur` | Taxi-compteur |
| `moto_taxi` | Moto-taxi |
| `tricycle` | Tricycle |
| `metro` | Métro |
| `brt` | BRT |
| `car_interurbain` | Car interurbain |

<a id="referentiel-modes_saisie"></a>

### modes_saisie

| Code | Libellé |
|------|---------|
| `oral` | Dit à voix haute |
| `ecrit` | Écrit |

<a id="referentiel-langues_requete"></a>

### langues_requete

| Code | Libellé |
|------|---------|
| `francais` | Français |
| `francais_nouchi` | Français mêlé de nouchi |
| `dioula` | Dioula |
| `autre` | Autre |

<a id="referentiel-types_lieu"></a>

### types_lieu

| Code | Libellé |
|------|---------|
| `carrefour` | Carrefour |
| `pharmacie` | Pharmacie |
| `eglise` | Église |
| `mosquee` | Mosquée |
| `maquis` | Maquis |
| `marche` | Marché |
| `gare` | Gare |
| `terminus` | Terminus |
| `ecole` | École, université |
| `quartier` | Quartier |
| `commune` | Commune |
| `batiment_public` | Bâtiment public, hôpital |
| `entreprise` | Entreprise, bureau, boutique |
| `autre` | Autre |

<a id="referentiel-expressions_relatives"></a>

### expressions_relatives

| Code | Libellé |
|------|---------|
| `aucune` | Aucune |
| `derriere` | Derrière |
| `en_face` | En face de |
| `a_cote` | À côté de |
| `apres` | Après |
| `avant` | Avant |
| `autre` | Autre |

<a id="referentiel-types_jour"></a>

### types_jour

| Code | Libellé |
|------|---------|
| `ouvrable` | Jour ouvrable |
| `samedi` | Samedi |
| `dimanche` | Dimanche |
| `ferie` | Jour férié |

<a id="referentiel-conditions"></a>

### conditions

| Code | Libellé |
|------|---------|
| `pluie` | Pluie |
| `vacances_scolaires` | Vacances scolaires |
| `fin_de_mois` | Fin de mois |
| `fete_ou_evenement` | Fête ou grand événement |

<a id="referentiel-profils"></a>

### profils

| Code | Libellé |
|------|---------|
| `standard` | Standard |
| `mobilite_reduite` | Mobilité réduite |

<a id="referentiel-statuts_reponse"></a>

### statuts_reponse

| Code | Libellé |
|------|---------|
| `acceptable` | Acceptable |
| `piege` | Piège (à ne jamais proposer) |

<a id="referentiel-categories_reponse"></a>

### categories_reponse

| Code | Libellé |
|------|---------|
| `moins_cher` | Le moins cher |
| `plus_rapide` | Le plus rapide |
| `plus_simple` | Le plus simple |
| `plus_sur` | Le plus sûr |

<a id="referentiel-oui_non"></a>

### oui_non

| Code | Libellé |
|------|---------|
| `oui` | Oui |
| `non` | Non |

<a id="referentiel-tranches_age"></a>

### tranches_age

| Code | Libellé |
|------|---------|
| `moins_25` | Moins de 25 ans |
| `de_25_a_44` | 25 à 44 ans |
| `de_45_a_59` | 45 à 59 ans |
| `plus_60` | 60 ans et plus |

<a id="referentiel-lectures"></a>

### lectures

| Code | Libellé |
|------|---------|
| `facile` | Lit facilement |
| `difficile` | Lit difficilement |
| `ne_lit_pas` | Ne lit pas |

<a id="referentiel-telephones"></a>

### telephones

| Code | Libellé |
|------|---------|
| `smartphone_perso` | Smartphone personnel |
| `smartphone_partage` | Smartphone partagé |
| `basique` | Téléphone basique |
| `aucun` | Pas de téléphone |

<a id="referentiel-langues"></a>

### langues

| Code | Libellé |
|------|---------|
| `francais` | Français |
| `dioula` | Dioula |
| `autre` | Autre |

<a id="referentiel-taches"></a>

### taches

| Code | Libellé |
|------|---------|
| `T1` | T1 · Planifier le trajet du matin (parcours 1) |
| `T2` | T2 · Arrivée à une gare saturée (parcours 2) |
| `T3` | T3 · Attendre au bord de la route (parcours 3) |
| `T4` | T4 · Contribuer en deux pressions (parcours 5) |
| `T5` | T5 · Sans smartphone, menu USSD simulé (parcours 7) |

<a id="referentiel-reussites"></a>

### reussites

| Code | Libellé |
|------|---------|
| `seul` | Réussie sans aide |
| `avec_aide` | Réussie avec aide |
| `echec` | Échec |
| `abandon` | Abandon |
| `non_tentee` | Non tentée |

<a id="referentiel-reconnaissances"></a>

### reconnaissances

| Code | Libellé |
|------|---------|
| `oui` | Reconnue |
| `partiel` | Partiellement reconnue |
| `non` | Non reconnue |

<a id="referentiel-icones"></a>

### icones

| Code | Libellé |
|------|---------|
| `mode_bus_sotra` | Mode · bus SOTRA |
| `mode_bus_express` | Mode · bus express |
| `mode_bateau_bus` | Mode · bateau-bus |
| `mode_pinasse` | Mode · pinasse |
| `mode_gbaka` | Mode · gbaka |
| `mode_woro_communal` | Mode · wôrô-wôrô communal |
| `mode_woro_intercommunal` | Mode · wôrô-wôrô intercommunal |
| `mode_taxi_compteur` | Mode · taxi-compteur |
| `mode_moto_taxi` | Mode · moto-taxi |
| `mode_car_interurbain` | Mode · car interurbain |
| `action_signaler` | Action · signaler |
| `action_je_pars` | Action · je pars |
| `action_partager` | Action · partager le trajet |
| `action_urgence` | Action · urgence |
| `action_micro` | Action · dicter |
| `onglet_trajet` | Onglet · trajet |
| `onglet_carte` | Onglet · carte |
| `onglet_moi` | Onglet · moi |
| `file_peu` | État · peu de monde |
| `file_moyen` | État · moyen |
| `file_beaucoup` | État · beaucoup de monde |
| `file_tres_long` | État · file très longue |
