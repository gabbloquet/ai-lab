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

DeepEval envoie de la télémétrie par défaut : `DEEPEVAL_TELEMETRY_OPT_OUT=1` la désactive (voir `.env.example`). Les tests la désactivent d'office.

```bash
uv run pytest evals
```
