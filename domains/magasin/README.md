# Domaine `magasin`

Un catalogue de produits vendus dans cinq magasins, avec un stock par magasin. Ce domaine sert aux expériences sur les outils d'agents (première : [001](../../experiments/001-mcp-outils-par-intention/README.md)).

**Tout est synthétique.** Produits, marques, magasins et stocks sont produits par un générateur seedé et versionné. Les noms de marques sont inventés ; aucune vérification n'a été faite auprès des registres de marques déposées. Aucune enseigne, aucun client et aucune donnée réelle.

## Entités

### Produit

| Champ | Type | Exemple | Rôle |
|---|---|---|---|
| `sku` | chaîne | `P-15695` | Identifiant unique et opaque, tiré au hasard : il ne révèle ni le type ni la marque |
| `name` | chaîne | `Veldric Casque K8` | Nom commercial |
| `brand` | chaîne | `Veldric` | Marque fictive |
| `department` | chaîne | `Audio` | Rayon : recherche et navigation |
| `type` | chaîne | `Casque` | Type de produit : base de la règle d'alternative |
| `price` | décimal, 2 chiffres, en euros | `79.90` | Prix de vente |

### Magasin

| Champ | Type | Exemple |
|---|---|---|
| `storeId` | chaîne | `S01` |
| `name` | chaîne | `Magasin Lyon` |
| `city` | chaîne | `Lyon` |

Les cinq magasins : S01 Lyon, S02 Nantes, S03 Lille, S04 Bordeaux, S05 Strasbourg.

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

**Alternative en stock.** Pour un produit P de prix p, demandé dans un magasin M, un produit Q est une alternative si toutes ces conditions sont réunies :
1. Q a le même `type` que P ;
2. Q est différent de P ;
3. le prix de Q est compris dans [0,8 × p ; 1,2 × p], bornes incluses ;
4. Q est en stock dans M.

Les alternatives sont triées par écart de prix croissant (|prix de Q − p|), puis par `sku` en cas d'égalité. On garde les **3 premières**. S'il n'y en a aucune, le résultat est une liste vide.

**Magasins qui ont le produit.** Tous les magasins où le produit est en stock, triés par `storeId`.

L'implémentation de référence de ces règles est `magasin_rules.py`, testée dans `tests/test_magasin_rules.py`. C'est elle qui calcule les réponses attendues du golden set, et elle sert d'oracle aux implémentations des expériences.

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
| Golden set sélection d'outils | `golden/tool-selection/v1/` | à générer |

Un jeu publié ne change plus ; une correction donne une `v2`.
