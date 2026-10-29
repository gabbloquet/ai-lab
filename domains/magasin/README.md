# Domaine `magasin`

Un catalogue de produits vendus dans cinq magasins, avec un stock par magasin. Ce domaine sert aux expériences sur les outils d'agents (première : [001](../../experiments/001-mcp-outils-par-intention/README.md)).

**Tout est synthétique.** Produits, marques, magasins et stocks sont produits par un générateur seedé et versionné. Les noms de marques sont inventés ; aucune vérification n'a été faite auprès des registres de marques déposées. Aucune enseigne, aucun client et aucune donnée réelle.

## Entités

### Produit

| Champ | Type | Exemple | Rôle |
|---|---|---|---|
| `sku` | chaîne : `P-` suivi de 5 chiffres | `P-15695` | Identifiant unique et opaque, tiré au hasard : il ne révèle ni le type ni la marque |
| `name` | chaîne | `Veldric Casque K8` | Nom commercial |
| `brand` | chaîne | `Veldric` | Marque fictive |
| `department` | chaîne | `Audio` | Rayon : recherche et navigation |
| `type` | chaîne | `Casque` | Type de produit : base de la règle d'alternative |
| `price` | décimal, 2 chiffres, en euros | `79.90` | Prix de vente |

**Format du SKU.** C'est une règle du domaine : un SKU qui ne suit pas le format est refusé comme mal formé, avant toute recherche du produit. La casse et les espaces autour sont normalisés d'abord, donc ` p-15695 ` est accepté et vaut `P-15695`.

### Magasin

| Champ | Type | Exemple |
|---|---|---|
| `storeId` | chaîne : `S` suivi de 2 chiffres | `S01` |
| `name` | chaîne | `Magasin Lyon` |
| `city` | chaîne | `Lyon` |

Les cinq magasins : S01 Lyon, S02 Nantes, S03 Lille, S04 Bordeaux, S05 Strasbourg.

Le format de `storeId` est celui des données, mais il n'est pas validé : un identifiant hors format, comme un nom de ville, est simplement un magasin inconnu. La casse et les espaces autour sont normalisés.

### Stock

Une ligne par couple produit × magasin.

| Champ | Type | Rôle |
|---|---|---|
| `sku` | chaîne | Produit |
| `storeId` | chaîne | Magasin |
| `onHand` | entier ≥ 0 | Stock physique présent en magasin |
| `reserved` | entier, 0 ≤ `reserved` ≤ `onHand` | Unités déjà promises à des commandes |

## Règles métier

**Disponible.** `available = onHand − reserved`. Un produit est **en stock** dans un magasin si `available > 0`.

**Produits similaires.** Pour un produit P de prix p, un produit Q est similaire si toutes ces conditions sont réunies :
1. Q a le même `type` que P ;
2. Q est différent de P ;
3. le prix de Q est compris dans [0,8 × p ; 1,2 × p], bornes incluses.

Le stock n'intervient pas. Les produits similaires sont triés par écart de prix croissant (|prix de Q − p|), puis par `sku` en cas d'égalité, sans limite de nombre. Un produit inconnu n'a aucun produit similaire.

**Alternative en stock.** Pour un produit P demandé dans un magasin M, les alternatives sont les produits similaires à P qui sont **en stock dans M**, dans le même ordre. On garde les **3 premières**. S'il n'y en a aucune, le résultat est une liste vide.

**Magasins qui ont le produit.** Tous les magasins où le produit est en stock, triés par `storeId`.

L'implémentation de référence de ces quatre règles est `magasin_rules.py`, testée dans `tests/test_magasin_rules.py`. C'est elle qui calcule les réponses attendues du golden set, et elle sert d'oracle aux implémentations des expériences.

**Recherche dans le catalogue.** Une requête et, en option, un rayon :
1. la requête est obligatoire : vide ou faite d'espaces, elle est refusée ;
2. la requête est découpée en mots sur les espaces ; un produit correspond si **chaque mot** figure dans son nom, sa marque ou son type. Le rayon n'est pas cherché dans la requête, et aucun caractère joker n'est interprété ;
3. la comparaison ignore la casse et les accents (`cafetiere` trouve `Cafetière`) ;
4. un rayon renseigné filtre les produits, avec la même normalisation. Un rayon qui n'existe dans aucun produit est refusé. Un rayon vide équivaut à aucun filtre ;
5. les résultats sont triés par nom, puis par `sku` en cas d'égalité.

**Parcours d'un rayon.** Un rayon en option, sans requête : les produits du rayon, ou tout le catalogue si le rayon est absent ou vide. Le rayon suit les mêmes règles que dans la recherche (normalisation, refus d'un rayon inconnu), et les produits sont triés par nom, puis par `sku`. Une recherche est donc un parcours du rayon, filtré par les mots de la requête.

Le nombre de résultats renvoyés et la manière de signaler une recherche sans résultat relèvent des expériences, pas du domaine. La recherche et le parcours n'ont ni implémentation de référence en Python ni réponses d'oracle : le golden set ne contraint pas la requête de recherche (argument non contraint, `{"any": true}` dans la spec `tool-selection/v1`), donc la notation ne dépend pas de ses résultats.

## Volumétrie et cas à garantir

- 50 produits, répartis en 4 rayons (Audio, Informatique, Maison, Sport) et 11 types : 9 types de 5 produits, 1 de 4, et 1 de 1.
- 5 magasins, soit 250 lignes de stock.
- Le générateur garantit la présence des cas dont le golden set a besoin. Chaque cas est listé, avec son produit et son magasin, dans `scenarios.json` :
  - un produit en rupture dans un magasin, avec au moins une alternative en stock ;
  - un produit en rupture, sans aucune alternative en stock ;
  - un produit en rupture dans tous les magasins ;
  - un type qui ne compte qu'un seul produit, et qui n'a donc jamais d'alternative ;
  - des alternatives exactement à la limite de la fourchette de prix (−20 % et +20 %), et un produit 1 centime sous la borne basse ;
  - un produit dont tout le stock physique est réservé (`onHand > 0` mais rien de disponible).

## Générer

```bash
uv run python domains/magasin/magasin_generator.py --seed 42 --version v1
```

Le générateur refuse d'écrire dans une version existante. `MANIFEST.json` enregistre la seed et l'empreinte SHA-256 de chaque fichier.

## Versions

| Jeu | Chemin | Statut |
|---|---|---|
| Données | `data/v1/` | générées (seed 42), pas encore citées par un résultat |
| Réponses de l'oracle | `oracle/v1/` | dérivées de `data/v1` par `magasin_oracle_export.py --version v1` : disponibilité et alternatives pour chaque couple produit × magasin, magasins en stock pour chaque produit. Les implémentations des expériences les rejouent pour prouver qu'elles appliquent les mêmes règles. |
| Golden set sélection d'outils | `golden/tool-selection/v1/` | généré (seed 42, `data/v1`) par `magasin_golden_tool_selection.py`, pas encore cité par un résultat. Règles et composition : [`golden/tool-selection/README.md`](golden/tool-selection/README.md) |

Un jeu publié ne change plus ; une correction donne une `v2`.
