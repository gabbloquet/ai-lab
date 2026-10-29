# Golden set `tool-selection` du domaine magasin

Questions posées à un modèle équipé d'un serveur MCP, avec les appels d'outils attendus. Il sert à l'expérience [001](../../../../experiments/001-mcp-outils-par-intention/README.md), qui compare deux jeux d'outils : `intent` (par intention métier) et `rest` (miroir d'une API REST). Le format d'un item et les règles de notation sont dans la spec [`tool-selection/v1`](../../../../evals/spec/tool-selection/v1/SPEC.md).

Les items sont générés par `magasin_golden_tool_selection.py`, seedé et testé. Les appels attendus sont calculés par l'oracle `magasin_rules.py` à partir des données, jamais écrits à la main.

```bash
uv run python domains/magasin/magasin_golden_tool_selection.py --seed 42 --version v1 --data-version v1
```

## Versions

| Version | Données | Seed | Spec | Statut |
|---|---|---|---|---|
| `v1` | `data/v1` | 42 | `tool-selection/v1` | générée le 2026-10-29, pas encore citée par un résultat |

## Composition de la v1

130 items, 26 par intention. Dans chaque intention, 6 items `dev` et 20 `test`. Les identifiants (`ts-001` à `ts-130`) sont mélangés : ils ne révèlent pas l'intention.

Hors recherche, la moitié des questions désigne le produit par son **SKU** (« la référence P-38657 »), l'autre moitié par son **nom** (« l'enceinte Quellan K2 »). Le tag `ref:sku` ou `ref:name` le signale, et le split est équilibré sur ce tag : 3 + 3 en `dev`, 10 + 10 en `test`. Le verdict porte sur l'ensemble ; les résultats par tag sont secondaires.

Toutes les questions portent sur le **magasin courant**, donné dans `context.storeId`.

| Intention | Cas couverts | `intent` requiert | `rest` requiert |
|---|---|---|---|
| Disponibilité | 17 produits en stock, 9 sans unité disponible (dont un stock entièrement réservé) | `check_availability(sku, storeId)` | `get_stock(sku, storeId)` |
| Alternative en stock | produit en rupture dans le magasin : 18 avec une alternative en stock, 8 sans | `find_in_stock_alternative(sku, storeId)` | `get_similar(sku)`, puis un `get_stock(storeId)` sur **l'une** des alternatives que renverrait `intent` ; s'il n'y en a aucune, un `get_stock` sur **chaque** produit similaire, car il faut tous les vérifier pour conclure |
| Magasins qui ont le produit | 26 produits distincts, dont un en rupture partout | `find_stores_with_stock(sku)` | un `get_stock(sku, storeId)` pour chacun des 5 magasins |
| Fiche produit | 26 produits distincts | `get_product_details(sku)` | `get_product(sku)` |
| Recherche | 8 par type, 14 par marque et type, 4 sur des produits que le catalogue ne vend pas | `search_catalog` | `list_products` |

Pour la recherche, la requête est exigée mais non contrainte (`{"any": true}`), et la catégorie est facultative : si elle est donnée, ce doit être le rayon des produits cherchés. Pour un produit absent du catalogue, toute catégorie est acceptée.

**Appels tolérés** (ni exigés, ni comptés en trop) :
- la fiche du produit visé (`get_product_details` ou `get_product`), sauf pour l'intention « fiche produit », où elle est requise ;
- la recherche (`search_catalog` ou `list_products`, avec n'importe quels arguments), seulement quand la question donne le nom du produit : il faut alors trouver son SKU ;
- `list_stores` en `rest`, pour l'intention « magasins qui ont le produit ».

Un appel non toléré qui ne correspond à aucun motif requis compte comme appel en trop. C'est le cas, par exemple, d'un `get_stock` sur le produit en rupture lui-même dans l'intention « alternative ». Un appel en trop ne fait pas échouer `success`, seulement `strict_success`.

## Garanties vérifiées par les tests

- chaque item est valide selon `golden.schema.json` ;
- aucun outil n'est à la fois requis et toléré dans un même item (règle que JSON Schema ne peut pas exprimer) ;
- aucun item n'exige plus de 10 appels, le plafond de la 001 ;
- les questions sont toutes différentes ; une question `ref:name` ne montre jamais le SKU ;
- une question d'alternative ne porte que sur un produit réellement en rupture dans le magasin ;
- les scénarios du domaine (`data/v1/scenarios.json`) sont présents ;
- la même seed produit le même golden set.
