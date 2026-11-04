# 001 — Run final sur le split `test` (2026-11-04)

**Question :** des outils MCP par intention métier (B) font-ils faire au modèle plus souvent les bons appels que des outils miroir REST (A) ?

**Réponse :** oui pour `mistral-small-2603`, avec **+24,6 points de `success`** (IC 95 % [+16,0 ; +33,2]). Pour `gemini-3.5-flash-lite` et `claude-haiku-5-5`, le verdict est **non concluant** : les deux variantes sont au plafond (≥ 99,4 %). Leurs intervalles excluent toutefois un gain de 10 points, le plus petit écart qui compte selon le protocole. Pour les trois modèles, B demande environ **deux fois moins d'appels**.

## Provenance

| Élément | Valeur |
|---|---|
| Commit de gel | `092a894441be6bd27b9f5a42adaf4f9d494dc279`, dépôt propre au lancement (`git_dirty: false` dans chaque `run.json`) |
| Golden set | `domains/magasin/golden/tool-selection/v2`, `items.jsonl` sha256 `a8055fa7cd20e62d4e5002fe71912f8adc578342c060204f4ee6bd2344ede11e`, vérifié contre son MANIFEST par le lanceur |
| Spec de notation | `evals/spec/tool-selection/v1` |
| Lockfiles | `uv.lock` sha256 `8538b81292d4e82c837d2669fe3ebe9403d2b6f89412df8ddc415c173938bbef` ; Java : `gradle/libs.versions.toml` sha256 `227db65dbd549ccd3445ca889219684a55a910965fd90012fce7b01ecac5a4ac` |
| Prompt système | `python/prompts/system.md`, sha256 `23475ff723d0…` (complet dans `run.json`) |
| Serveurs | Java, Spring AI 2.0.1, SDK MCP Java 2.1.0, `--lab.variant=intent` sur `127.0.0.1:8082` et `--lab.variant=rest` sur `127.0.0.1:8083` |
| Boucle | Pydantic AI 2.65.0 ; plafond de 10 appels émis ; budget de correction 2 ; `tool_error_behavior='failed'` |
| Plan | 100 items `test` × 2 variantes × k = 5, soit 1 000 exécutions par modèle |
| Runs | `runs/final-test-mistral`, `runs/final-test-gemini`, `runs/final-test-claude`, lancés le 2026-11-04 à 11:02 UTC. Traces et scores dans Langfuse, sessions du même nom |
| Calcul | `python/agent/scripts/report_metrics.py runs/final-test-*` (tableaux ci-dessous) ; verdict de `ailab_evals.tool_selection.aggregate` |

| Modèle | Identifiant vérifié le 2026-11-04 | Réglages envoyés |
|---|---|---|
| Mistral | `mistral:mistral-small-2603` (API Mistral) | `temperature = 0` |
| Gemini | `google:gemini-3.5-flash-lite` (API Google) | `temperature = 0` |
| Claude | `anthropic:claude-haiku-5-5` (Models API d'Anthropic) | aucun : le paramètre `temperature` est refusé par les modèles Claude actuels |

## Verdict par modèle

La règle a été fixée avant le run : B est meilleure si la borne basse de l'IC à 95 % du delta apparié de `success` est au-dessus de 0.

| Modèle | `success` A | `success` B | Delta B − A | IC 95 % | Verdict |
|---|---|---|---|---|---|
| `mistral-small-2603` | 0,742 | 0,988 | **+0,246** | [+0,160 ; +0,332] | **B meilleure** |
| `gemini-3.5-flash-lite` | 0,994 | 1,000 | +0,006 | [−0,006 ; +0,018] | non concluant |
| `claude-haiku-5-5` | 0,996 | 1,000 | +0,004 | [−0,002 ; +0,010] | non concluant |

## Métriques secondaires

Elles suivent le même calcul de delta apparié et d'IC, mais ne portent pas le verdict. Les tokens se comparent entre variantes d'un même modèle, jamais d'un fournisseur à l'autre.

### `mistral-small-2603`

| Métrique | A | B | Delta B − A | IC 95 % |
|---|---|---|---|---|
| `strict_success` | 0,404 | 0,532 | +0,128 | [+0,048 ; +0,208] |
| `tool_recall` | 0,934 | 1,000 | +0,066 | [+0,032 ; +0,100] |
| `args_recall` | 0,871 | 1,000 | +0,129 | [+0,086 ; +0,173] |
| `n_calls` | 2,972 | 1,948 | −1,024 | [−1,459 ; −0,589] |
| `extra_calls` | 0,984 | 0,628 | −0,356 | [−0,643 ; −0,069] |
| tokens d'entrée | 2 592 | 2 841 | +249 | [+31 ; +467] |
| tokens de sortie | 121 | 97 | −23 | [−34 ; −13] |

Exécutions en erreur : A 2, B 6. Ce sont toutes des dépassements du plafond de 10 appels.

### `gemini-3.5-flash-lite`

| Métrique | A | B | Delta B − A | IC 95 % |
|---|---|---|---|---|
| `strict_success` | 0,730 | 0,782 | +0,052 | [−0,029 ; +0,133] |
| `tool_recall` | 1,000 | 1,000 | 0 | [0 ; 0] |
| `args_recall` | 1,000 | 1,000 | 0 | [0 ; 0] |
| `n_calls` | 3,308 | 1,770 | −1,538 | [−1,980 ; −1,096] |
| `extra_calls` | 0,580 | 0,394 | −0,186 | [−0,389 ; +0,017] |
| tokens d'entrée | 2 405 | 2 314 | −91 | [−273 ; +90] |
| tokens de sortie | 145 | 113 | −32 | [−45 ; −19] |

Exécutions en erreur : A 3, B 0. Ce sont toutes des dépassements du plafond de 10 appels.

### `claude-haiku-5-5`

| Métrique | A | B | Delta B − A | IC 95 % |
|---|---|---|---|---|
| `strict_success` | 0,740 | 0,818 | +0,078 | [+0,004 ; +0,152] |
| `tool_recall` | 1,000 | 1,000 | 0 | [0 ; 0] |
| `args_recall` | 0,999 | 1,000 | +0,001 | [−0,001 ; +0,003] |
| `n_calls` | 3,332 | 1,702 | −1,630 | [−2,105 ; −1,155] |
| `extra_calls` | 0,568 | 0,360 | −0,208 | [−0,443 ; +0,027] |
| tokens d'entrée | 4 253 | 3 675 | −578 | [−864 ; −292] |
| tokens de sortie | 385 | 247 | −138 | [−186 ; −91] |

Exécutions en erreur : A 1, B 0.

## Lecture

**`success` par intention (A / B)**, sur les 20 items `test` de chaque intention et les 5 répétitions :

| Intention | Mistral | Gemini | Claude |
|---|---|---|---|
| Disponibilité | 1,00 / 1,00 | 1,00 / 1,00 | 1,00 / 1,00 |
| Alternative en stock | **0,20** / 1,00 | 0,97 / 1,00 | 0,99 / 1,00 |
| Magasins qui ont le produit | **0,51** / 1,00 | 1,00 / 1,00 | 1,00 / 1,00 |
| Fiche produit | 1,00 / 1,00 | 1,00 / 1,00 | 1,00 / 1,00 |
| Recherche | 1,00 / **0,94** | 1,00 / 1,00 | 0,99 / 1,00 |

- **Tout l'écart de Mistral vient des intentions qui exigent un enchaînement en A.** Pour une alternative, il faut `get_similar` puis `get_stock` sur le bon produit. Pour les magasins qui ont le produit, il faut un `get_stock` par magasin. Le comportement du run 0 se retrouve sur le `test` : Mistral propose un produit similaire sans vérifier son stock, ou n'interroge qu'une partie des magasins. Sur les questions qui demandent un seul appel, A et B font jeu égal.
- **Gemini et Claude enchaînent sans difficulté.** Sur un serveur de 5 outils et un petit catalogue, le découpage ne change presque rien à leur taux de réussite. Il change en revanche le chemin : en A, ils font environ deux fois plus d'appels pour arriver au même résultat.
- **B a un défaut que A n'a pas.** Sur `ts-045`, qui cherche un produit que le catalogue ne vend pas (« des imprimantes »), Mistral répète `search_catalog` jusqu'au plafond dans les 5 répétitions de B. En A, `list_products` permet de parcourir le rayon sans requête : il conclut en 3 appels. `search_catalog` exige une requête par construction, et le `hint` d'une recherche vide n'a pas suffi à arrêter Mistral.
- **Coût.** B réduit les tokens de sortie pour les trois modèles. Les tokens d'entrée baissent nettement avec Claude, mais montent avec Mistral : les descriptions et les réponses de B sont plus riches, et ce surcoût n'est pas compensé quand le nombre d'appels baisse moins.

## Limites propres à ce run

- **Plafond.** Pour deux modèles sur trois, les deux variantes dépassent 99 % de `success`. Le golden set (5 outils, 5 magasins, 50 produits) ne départage pas des modèles qui enchaînent bien les appels. Un domaine plus large ou des chaînes plus longues seraient nécessaires pour mesurer un écart chez eux.
- **Un seul modèle par fournisseur, tous du palier « petit modèle ».** Rien ici ne dit ce que font des modèles plus grands. On peut supposer, sans l'avoir mesuré, qu'ils sont au plafond eux aussi.
- **Claude sans température fixée**, avec sa réflexion adaptative par défaut (voir le protocole).
- **Aucune itération.** Le budget de 3 cycles par variante n'a pas été utilisé : les variantes sont celles du run 0, et ne sont pas mises au point sur Mistral.
- **Golden set corrigé une fois après le run 0** (v2, règle commune à A et B, décidée sans lire le `test`).
- Les limites générales de l'expérience sont dans son [README](../README.md#limites).
