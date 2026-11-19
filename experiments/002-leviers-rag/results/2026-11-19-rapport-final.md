# 002 — Rapport final (2026-11-19)

> Synthèse de l'expérience, sans nouveau run. Les verdicts viennent du [run consolidé 2](2026-11-15-run-consolide-2-test.md) : golden set `droit-consommation/rag-qa` v5 (`items.jsonl` sha256 `9677d85172341b31ec5f71e030bda87ebe17a531126df63c5b0c22fca1426d53`), spec `rag-qa/v2`, 234 items `test`, k = 3. Ce rapport donne aussi les deux pré-études du `dev` faites après la clôture. Les lockfiles sont cités dans chaque rapport source.

**Question** : sur des questions de consommateurs portant sur le Code de la consommation, quels leviers font gagner le plus de réponses justes (`correct`) à un RAG, et à quel coût ?

**Réponse** : le RAG lui-même d'abord, avec +28 à +44 points. Viennent ensuite trois leviers du même ordre, quelques points chacun : 20 passages au lieu de 5, le générateur et le RAG agentique. Le générateur est le seul qui fasse presque disparaître les réponses inventées.

## Les leviers

Delta de `correct` en points, IC à 95 % apparié. En gras : concluant après Holm.

| Levier, à générateur constant | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| RAG naïf contre modèle seul | **+35,9** | **+44,0** | **+27,6** |
| 20 passages au lieu de 5 | +5,4 [+0,7 ; +10,1] | +4,4 [−0,2 ; +9,0] | **+9,4** |
| Reformulation de la question | −0,1, ni gain ni perte de 5 points | +0,3, ni gain ni perte de 5 points | +1,4, gain de 5 points non exclu |
| Reclassement contre 20 passages | −1,6, gain de 3 points exclu | +0,3, rien d'exclu | −1,1, gain de 3 points exclu |
| Consigne d'abstention (réponses inventées) | **−8,5**, contre +3,8 d'abstentions à tort | **−4,6** | 0, contre +14,2 d'abstentions à tort |

| Générateur, avec 20 passages, contre Mistral Small (0,815 ; 24,8 % de réponses inventées) | `correct` | Réponses inventées | Coût par question |
|---|---|---|---|
| Mistral Large 4 | **+5,6** | **−23,5** | 0,0032 $ |
| Gemini 4 Carbon | **+7,1** | **−24,8** | 0,0092 $ |

| RAG agentique sur MCP, contre le RAG à 20 passages du même générateur | `correct` | Coût ; latence médiane |
|---|---|---|
| Mistral Large 4 (verdict de l'étape) | 0,870 → 0,899, +2,8 : perte de 3 points exclue, pas un gain | 0,0032 → 0,0071 $ ; 4,5 → 8,5 s |
| Gemini 4 Carbon (secondaire, déclarée d'avance) | 0,886 → **0,953**, **+6,7** | 0,0092 → 0,0248 $ ; 5,5 → 20,9 s |

**Après la clôture** ([README](../README.md), pré-études du 2026-11-17, `dev` seulement, sans verdict) :
- **À requête inchangée, la récupération a presque tout donné** : avec 50 passages, on gagne 2 items sur les 9 qui restent incomplets à 20 passages. Le reclassement de 50 vers 20 en gagne 2 et en perd 2.
- **Un autre embedding change peu à 20 passages** : `gemini-embedding-2` et `embed-v5.0-pro` atteignent 0,922, contre 0,900 pour `mistral-embed`. Avec 10 passages, `gemini-embedding-2` fait presque aussi bien que `mistral-embed` avec 20 (0,889).

## À retenir

1. **Le RAG est le premier levier.** Le reste se joue à quelques points.
2. **Les réponses inventées dépendent surtout du modèle.**
   - La récupération les fait à peine bouger.
   - La consigne d'abstention les baisse avec les deux Mistral, mais coûte des abstentions à tort à Mistral Small et fait trop s'abstenir Gemini.
   - Changer de générateur les fait presque disparaître.
3. **Une fois 20 passages en place, ce qui reste à gagner tient à la façon de chercher.** Le RAG agentique donne un gain net avec Carbon. Avec Large 4, il n'est pas concluant, et un gain n'est pas exclu. Il multiplie le coût par 2 à 3, et la latence par 2 à 4.
4. **Le meilleur compromis mesuré : Mistral Large 4 avec 20 passages.** Il obtient 0,870 de `correct` et 1,3 % de réponses inventées, pour 0,003 $ et 4,5 s par question. C'est 8 fois moins cher que Carbon agentique, pour 8 points de moins.

## Limites

- **Un seul corpus**, sans questions multi-hop. Il ne permet pas non plus de construire un `test` neuf : celui de la v5 a été lu trois fois en agrégat.
- **Plus petit effet détectable** : 6 à 8 points sur `correct`, 12 à 19 sur les réponses inventées. Plusieurs écarts utiles (3 et 5 points) sont en dessous.
- **Coûts au barème du jour**, pas sur facture. Les embeddings des requêtes ne sont pas comptés.
- **Corrections datées dans le README** : la saturation de la récupération, des « n'apporte rien » que l'IC ne permettait pas, et la température ignorée par Gemini Flash-Lite.

**Pistes ouvertes** : [`docs/pistes.md`](../../../docs/pistes.md). Les plus solides demandent un nouveau corpus de plusieurs codes reliés par des renvois.
