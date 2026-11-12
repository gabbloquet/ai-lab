# Scorers Python

Implémentation Python des specs d'évaluation partagées (`evals/spec/`). Chaque scorer doit passer tous les vecteurs de conformance de sa spec, comme son équivalent Java.

## `tool-selection` v1

- `ailab_evals.tool_selection` : le cœur de notation, sans DeepEval. `score_execution` note une exécution (SPEC.md § 6), `aggregate` calcule le delta apparié, l'IC à 95 % et le verdict sur les seuls items `test` (§ 7).
- `ailab_evals.tool_selection_metric.ToolSelectionMetric` : la métrique DeepEval personnalisée qui l'enveloppe. Le score vaut 1.0 si `success`, 0.0 sinon ; toutes les métriques de la spec sont dans `score_breakdown`. On n'utilise pas `ToolCorrectnessMetric`, dont les règles diffèrent de la spec.

Un `LLMTestCase` porte les appels émis dans `tools_called`, et dans `metadata` l'attente de l'item pour la variante notée (`expected`) ainsi que l'erreur d'exécution (`error`, ou `None`) :

```python
from deepeval import evaluate
from deepeval.test_case import LLMTestCase, ToolCall
from ailab_evals.tool_selection_metric import ToolSelectionMetric

test_case = LLMTestCase(
    input=item["question"],
    actual_output=answer,
    tools_called=[ToolCall(name=c["tool"], input_parameters=c["args"]) for c in calls],
    metadata={"expected": item["expected"]["rest"], "error": None},
)
evaluate(test_cases=[test_case], metrics=[ToolSelectionMetric()])
```

## `rag-qa` v1

- `ailab_evals.rag_qa` : le cœur de notation, sans DeepEval ni juge LLM. `score_execution(item, execution)` note une exécution sous sa forme canonique (SPEC.md § 3.2 et § 6) : réponse juste, faits retrouvés, abstention, contexte (`evidence_recall@k`), diagnostic `failure` et citations. `normalize` et `normalize_citation` sont les fonctions N et C de la spec.
- `ailab_evals.rag_qa_metric.RagQaMetric` : la métrique DeepEval qui l'enveloppe. Le score vaut 1.0 si `correct`, 0.0 sinon, et toutes les métriques sont dans `score_breakdown`. On n'utilise pas les métriques RAG de DeepEval : elles reposent sur un juge LLM.

```python
test_case = LLMTestCase(
    input=item["question"],
    actual_output=execution["answer"],
    metadata={"item": item, "execution": execution},
)
evaluate(test_cases=[test_case], metrics=[RagQaMetric()])
```

## Commun

`ailab_evals.paired` : la comparaison appariée de deux variantes (delta, IC de Student à 95 %, verdict), sur les seuls items `test`. Les deux specs partagent cette règle.

DeepEval envoie de la télémétrie par défaut : `DEEPEVAL_TELEMETRY_OPT_OUT=1` la désactive (voir `.env.example`). Les tests la désactivent d'office.

```bash
uv run pytest evals
```

## `rag-qa` v2

- `ailab_evals.rag_qa_v2` : le cœur de notation de la v2, dans un module à part (le module v1 reste tel quel, puisque des rapports publiés le citent).
  - `score_execution(item, execution)` donne les métriques du § 6, dont `facts_attached`, `premise` et `all_evidence`.
  - `variant_aggregates` calcule les agrégats du § 7.
  - `compare` fait la comparaison appariée sur une métrique, avec son sens (§ 8.1).
  - `joint_comparison` rend le verdict à deux critères (§ 8.2).
  - `holm_family` calcule les p-values ajustées et le verdict corrigé (§ 8.3).
  - Les items exclus (§ 8.4) se passent en argument `excluded`.
- `ailab_evals.rag_qa_v2_metric.RagQaV2Metric` : la métrique DeepEval qui l'enveloppe, sur le modèle de `RagQaMetric`.

Les exécutions doivent suivre `evals/spec/rag-qa/v2/execution.schema.json`.
