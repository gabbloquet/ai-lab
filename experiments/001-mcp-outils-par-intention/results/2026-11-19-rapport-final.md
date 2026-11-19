# 001 — Rapport final (2026-11-19)

> Synthèse de l'expérience, sans nouveau run. Les chiffres viennent du [run final](2026-11-04-run-final-test.md) : golden set `magasin/tool-selection` v2 (`items.jsonl` sha256 `a8055fa7cd20e62d4e5002fe71912f8adc578342c060204f4ee6bd2344ede11e`), spec `tool-selection/v1`, 100 items `test`, k = 5, commit de gel `092a894`. Les lockfiles (`uv.lock`, `gradle/libs.versions.toml`) sont cités dans ce rapport.

**Question** : un serveur MCP dont les outils correspondent à des intentions métier (B, par exemple `find_in_stock_alternative`) fait-il faire au modèle plus souvent les bons appels qu'un serveur qui reproduit les endpoints d'une API REST (A) ?

**Réponse** : oui pour le modèle qui enchaîne mal les appels, avec +24,6 points pour Mistral Small. Pour les deux autres, le résultat n'est pas concluant : les deux variantes sont au plafond, et les IC excluent le gain de 10 points qui justifierait de réécrire un serveur. Pour les trois modèles, B demande moins d'appels.

## Résultats

| Modèle | `success` A | `success` B | Delta [IC 95 %] | Verdict | Appels par question, A → B |
|---|---|---|---|---|---|
| `mistral-small-2603` | 0,742 | 0,988 | **+24,6** [+16,0 ; +33,2] | **B meilleure** | 2,97 → 1,95 |
| `gemini-3.5-flash-lite` | 0,994 | 1,000 | +0,6 [−0,6 ; +1,8] | non concluant, gain de 10 points exclu | 3,31 → 1,77 |
| `claude-haiku-5-5` | 0,996 | 1,000 | +0,4 [−0,2 ; +1,0] | non concluant, gain de 10 points exclu | 3,33 → 1,70 |

## À retenir

1. **Des outils par intention servent de filet aux modèles qui enchaînent mal les appels.** Tout l'écart de Mistral Small vient des intentions qui demandent plusieurs appels en A : trouver une alternative en stock, ou les magasins qui ont le produit.
2. **Avec des modèles qui enchaînent bien**, sur un serveur de 5 outils, le découpage ne change pas le taux de réussite. Il retire en revanche 1,5 à 1,6 appel par question, soit à peu près la moitié des allers-retours.
3. **La recommandation des praticiens** (Anthropic, Philipp Schmid) est donc confirmée pour le petit modèle seulement. Pour les autres, son intérêt porte sur le nombre d'appels, pas sur la justesse.

## Limites

- **Plafond** : le golden set (5 outils, 5 magasins, 50 produits) ne départage pas les modèles qui enchaînent bien. Il faudrait un domaine plus large ou des chaînes plus longues.
- **Un domaine synthétique**, en français, avec 5 outils par variante, mis au point avec un seul modèle et une seule boucle d'agent (Pydantic AI). Le résultat ne se généralise pas tel quel.
- **Puissance** : le plus petit effet détectable était de 10,6 points au run 0, un peu au-dessus des 10 visés.
- **Température.** Claude tourne avec ses réglages par défaut, puisqu'il refuse le paramètre. Pour Gemini 3.5 Flash-Lite, la 002 a établi le 2026-11-12 que Google ignore `temperature` à partir de ce modèle. Le run de la 001 a donc tourné à la température par défaut de Gemini, et non à 0 comme l'écrit son rapport. Le verdict n'en dépend pas, puisque A et B ont les mêmes réglages. La correction est écrite, datée, dans le [README de la 001](../README.md#limites).
- **Sécurité du serveur de laboratoire** : il n'a ni authentification ni limitation du débit des appels ([bonnes pratiques MCP](../../../docs/mcp-bonnes-pratiques.md)).
