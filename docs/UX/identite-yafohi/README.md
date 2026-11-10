# Charte de yafohi

Statut : version 1 du 2026-11-10. **Identité choisie par le porteur** parmi les trois propositions de la [maquette](../maquette-identites/README.md). Le nom reste à vérifier (voir la dernière partie).

## Le nom

- **yafohi**, toujours en minuscules, en un seul mot. Il vient de « y'a fohi » : « y'a pas de souci », en nouchi, de « foyi », rien, en dioula. Se dit « ya-fo-hi ».
- **Promesse** : « Bouge tranquille. »
- **Personnalité** : simple, chaleureux, rassurant.
- **Esprit** : la simplicité de Wave. Un écran, une action, de gros boutons, zéro jargon. On s'inspire de cet esprit, jamais du logo, des couleurs ou des éléments de marque d'une autre appli.
- **Dans le code**, le nom de code technique reste `nemesis` (H-003). Le nom public passe par la clé de traduction `app.name` (`appName` dans l'appli).

## Le logo

| Fichier | Usage |
|---------|-------|
| [yafohi-mot.svg](logo/yafohi-mot.svg) | Le mot, sur fond clair (crème ou blanc) |
| [yafohi-mot-clair.svg](logo/yafohi-mot-clair.svg) | Le mot, sur fond encre ou sombre |
| [yafohi-mot-sur-mangue.svg](logo/yafohi-mot-sur-mangue.svg) | Le mot, sur fond mangue |
| [yafohi-icone.svg](logo/yafohi-icone.svg) et [PNG 512 px](logo/yafohi-icone-512.png) | **Icône de l'appli** : fond encre, « y » mangue, point blanc |
| [yafohi-icone-carree.svg](logo/yafohi-icone-carree.svg) et [PNG 512 px](logo/yafohi-icone-carree-512.png) | Icône sans coins arrondis, pour les magasins qui arrondissent eux-mêmes (Play Store) |
| [yafohi-icone-mangue.svg](logo/yafohi-icone-mangue.svg) | Variante claire : fond mangue, « y » encre |

- **L'idée** : la queue du « y » est une route qui mène à un point d'arrivée. Dans le mot, le point du « i » est un soleil mangue.
- **Le mot** est dessiné en Baloo 2 ExtraBold, vectorisé : il s'affiche à l'identique sans la police.
- **Zone de protection** : laisser autour du logo un vide au moins égal à la hauteur du point du « i ».
- **Taille minimale** : 24 px de haut pour le mot, 28 px de côté pour l'icône.
- **À ne pas faire** : déformer, incliner ou recolorer le logo hors des trois versions, ajouter une ombre, le poser sur une photo chargée.

## Les couleurs

| Nom | Code | Rôle | Contraste |
|-----|------|------|-----------|
| Mangue | `#FFC21A` | Marque, bouton Signaler, surfaces mises en avant | encre sur mangue : 11,5:1 |
| Encre | `#16130F` | Boutons principaux, texte principal | blanc sur encre : 18,5:1 |
| Crème | `#FFF9EE` | Fond de l'appli | encre sur crème : 17,7:1 |
| Sable | `#FFF2D9` | Champs, cartes secondaires | encre sur sable : 16,7:1 |
| Terre | `#5E574C` | Texte secondaire | 7,1:1 sur blanc |
| Feuille | `#1F7A47` | Fluide, confirmé, en direct | 5,1:1 sur crème |

- **Affluence** : toujours avec un mot et une à trois barres, jamais par la couleur seule. Fluide : `#1F7A47`. Ça remplit : `#A35A00`. Ça déborde : `#C2332B`.
- **Modes** : chaque mode a sa couleur, son icône et son nom. Le texte blanc posé dessus atteint au moins 4,5:1. Gbaka : `#13855A`. Wôrô-wôrô : `#BF5A00`. Bus : `#2B59C3`. Bateau-bus : `#077B99`. À pied : `#6B655A`.
- **Le mangue ne porte jamais de texte blanc** : il porte de l'encre.

Tous les codes sont dans [tokens.json](tokens.json), qui servira de source aux jetons de l'appli.

## La typographie

- **Baloo 2 ExtraBold** pour les titres et les gros chiffres. Elle est ronde et généreuse, chaleureuse sans être enfantine.
- **Nunito** (SemiBold à ExtraBold) pour le texte. Ses chiffres sont très lisibles.
- **Tailles** : titre d'écran 23, titre de feuille 20, texte 16, petit texte 13 ; jamais moins de 12. La partie 10.3 demande 16 sp pour le texte courant.
- **Licence** : les deux polices sont sous licence SIL Open Font License, gratuites, et s'embarquent dans l'appli.

## Les formes

- **Arrondis généreux** : cartes 20, feuilles 30 ; boutons, champs et puces en pilule.
- **Zones tactiles** : 48 dp au moins, et tout se fait d'une main.
- **Ombres** : une seule ombre, douce, pour ce qui flotte au-dessus de la carte.
- **Carte** : fond crème, eau menthe, très peu de détails. Seulement ce qui aide à se repérer : grands axes, lagune, quartiers, gares.

## Le ton

Chaleureux et rassurant, en phrases très courtes. On tutoie et on parle comme un voisin serviable.

| On écrit | On évite |
|----------|----------|
| On y va ! | Lancer la navigation |
| Ton gbaka arrive. Y'a fohi. | Véhicule en approche |
| Descends au prochain arrêt. | Préparez-vous à descendre à l'arrêt suivant |
| Pas d'info récente ici : temps habituel. | Données indisponibles |
| Merci, c'est noté ! | Votre signalement a été enregistré avec succès |

Le ton ne cache jamais une incertitude. Chaque attente et chaque prix montrent leur fraîcheur, leur source et leur confiance.

## Avant de figer : à vérifier

Ces vérifications reviennent au porteur ou à un juriste ; je ne peux pas les faire d'ici.

1. **Le sens et l'usage** : faire lire le nom et la promesse à quelques Abidjanais de différents âges, et noter les réactions (protocole de tests de maquettes).
2. **La marque** : chercher « yafohi » et ses variantes (« y'a fohi », « yafoi ») dans les marques déposées. En Côte d'Ivoire, le dépôt passe par l'OAPI.
3. **Les noms de domaine** : `yafohi.ci`, `yafohi.com`, `yafohi.app`.
4. **Les magasins d'applis** : vérifier qu'aucune appli ne porte déjà ce nom sur le Play Store et l'App Store.
5. **Les réseaux sociaux** : réserver les comptes `@yafohi`.
