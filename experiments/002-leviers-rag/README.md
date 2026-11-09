# 002 — Notre RAG répond mal : quels sont les plus gros leviers ?

> **Statut :** étapes 1 à 5 conclues ; run consolidé sur le golden set v4 en cadrage
> **Domaines :** [`droit-consommation`](../../domains/droit-consommation/README.md)
> **Spec de notation :** [`rag-qa/v1`](../../evals/spec/rag-qa/v1/SPEC.md) (publiée)

Une seule expérience, découpée en étapes (règle 1 du lab). Chaque étape juge un levier contre une baseline gelée, avec son propre protocole, son commit de gel et un seul run final. L'expérience conclut par le tableau des deltas de tous les leviers.

Jusqu'au 2026-11-09, ces étapes étaient présentées comme cinq expériences d'une « série ». Leurs dossiers et leurs rapports gardent leurs numéros (002 à 006), qui servent d'identifiants d'étape : rien n'est renommé, et les rapports publiés restent tels quels.

## Question

Sur des questions de consommateurs portant sur le Code de la consommation, quels leviers font gagner le plus de réponses justes (`correct`) à un RAG, et à quel coût (réponses inventées, tokens, latence) ?

## Étapes

Toutes les étapes ont tourné sur les trois mêmes générateurs : `mistral-small-2603`, `ministral-14b-2512` et `gemini-3.5-flash-lite`, avec k = 3 répétitions. Un verdict par modèle.

| Étape | Levier | Baseline (A) | Golden set | Verdict au run final |
|---|---|---|---|---|
| 1 — [002](../002-rag-naif-vs-modele-seul/README.md) | RAG naïf (5 passages) | modèle seul | v1, `test` 150 | **+37 à +44 pts** de `correct`, les trois modèles |
| 2 — [003](../003-reformulation-de-requete/README.md) | reformulation de la question | RAG naïf | v1, `test` 150 | non concluant (−0,7 à −0,9 pt) |
| 3 — [004](../004-top-k-20/README.md) | 20 passages au lieu de 5 | RAG naïf | v1, `test` 150 | +7,3 et +8,0 pts (Ministral, Gemini) ; non concluant avec Mistral Small (+4,0) |
| 4 — [005](../005-reclassement/README.md) | reclassement Cohere, 50 candidats vers 5 | RAG à 20 passages | v1, `test` 150 | non concluant (−0,4 à −2,0 pts), 2,6 fois moins de tokens |
| 5 — [006](../006-consigne-abstention/README.md) | consigne d'abstention plus exigeante | RAG à 20 passages | v3, `test` 190 | moins de réponses inventées avec Mistral Small (−9,2 pts) ; non concluant avec Ministral ; plus d'abstentions à tort avec Gemini (+8,7 pts) |

Les étapes 4 et 5 ont pris pour baseline la meilleure configuration du moment (20 passages) : l'expérience mêle donc des deltas isolés (contre le RAG naïf) et des deltas cumulés (contre 20 passages).

## Run consolidé sur le golden set v4 (en cadrage)

**But.** Mesurer plus finement le gain de chaque levier, sur un même golden set et dans un même run. Le golden set v4 a 234 items `test` valides, au lieu de 138 en v1. Il ajoute trois modes (`comparison`, `set`, `false_premise`) et 51 questions sans réponse valides, au lieu de 11. Les verdicts des étapes restent ceux de leurs runs finaux ; le run consolidé les complète, il ne les remplace pas.

**Principes retenus** (propriétaire, 2026-11-09) :
- les configurations gelées de chaque étape tournent telles quelles, **sans aucune nouvelle itération** sur le `dev`. Chaque levier a déjà reçu ses cycles ;
- deux lectures du même run : **chaque levier contre la même baseline** (le RAG naïf), et **une échelle cumulative** (naïf, puis 20 passages, puis reclassement, puis consigne d'abstention). Les deux tableaux sont corrigés pour comparaisons multiples (Holm) ;
- un seul run final, à modèle constant, sur les trois générateurs ;
- deltas globaux et par mode, métriques d'abstention calculées sans les items fautifs de l'audit.

**Reste à fixer avant d'écrire le protocole** : le coût estimé à partir des runs précédents (6 configurations × 3 modèles × k répétitions × 246 items) ; la version gelée de la consigne d'abstention, puisque l'étape 5 conclut qu'elle se règle par modèle ; le nombre de répétitions.

## Verdict

À écrire après le run consolidé. En attendant, voir le verdict de chaque étape.

## Limites

Celles de chaque étape, plus une : les étapes 1 à 4 ont tourné sur la v1, dont 12 questions sans réponse du `test` ont en fait une réponse (audit du 2026-11-09). Leurs métriques d'abstention en sont biaisées en faveur de l'abstention.
