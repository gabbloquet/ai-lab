# 005 — Reclasser 50 candidats pour n'en envoyer que 5 ?

> **Statut :** terminée le 2026-11-09 ([rapport](results/2026-11-09-run-final-test.md))
> **Domaines :** [`droit-consommation`](../../domains/droit-consommation/README.md)
> **Spec de notation :** [`rag-qa/v1`](../../evals/spec/rag-qa/v1/SPEC.md) (publiée)

Quatrième expérience de la série « notre RAG répond mal, quels sont les plus gros leviers ? ». La [004](../004-top-k-20/README.md) a montré que les articles manqués par le RAG naïf sont classés entre la 6e et la 20e place : envoyer 20 passages au lieu de 5 fait gagner 7 à 8 points de `correct` à deux générateurs sur trois, mais triple les tokens et fait inventer davantage sur les questions sans réponse. La 005 teste l'autre façon de récupérer ces articles : un modèle de reclassement qui les remonte dans un contexte de 5 passages.

Le duel : A, le RAG à 20 passages de la 004 (gelé) ; B, les 50 premiers passages denses reclassés par Cohere, réduits à 5.

## Pré-étude : choisir le modèle de reclassement (`dev` seulement)

Protocole et règle de choix écrits le 2026-11-08, avant toute mesure.

**Ce qu'on mesure.** La récupération seule, sans générateur, sur les 44 items `dev` qui ont une réponse : la recherche dense (`mistral-embed`, cosinus exact, texte seul indexé) propose 50 passages, le modèle de reclassement les note, et on garde les 5 mieux notés. Chaque candidat est présenté au modèle comme le générateur le lira : « Article <numéro> », puis le texte (`ailab_rag.reranking.document`). Mesures : `evidence_recall@5` et `all_evidence@5` de la spec, et le temps de reclassement par question (médiane et pire cas, appels hors cache).

**Candidats**, chacun dans sa configuration par défaut, sans réglage :

| Candidat | Accès | Révision ou version | Licence |
|---|---|---|---|
| `BAAI/bge-reranker-v2-m3` | local, `sentence-transformers` 6.2.0, `CrossEncoder` | poids `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` | Apache-2.0 |
| `Qwen/Qwen3-Reranker-0.6B` | local, `sentence-transformers` 6.2.0, `CrossEncoder`, instruction par défaut | poids `e61197ed45024b0ed8a2d74b80b4d909f1255473` | Apache-2.0 |
| Cohere `rerank-v5.0-pro` | API `POST /v2/rerank`, clé d'essai | version servie le jour de la mesure | propriétaire |

Modèles locaux : Mac M3 Pro (18 Go), GPU via MPS, float32. Cohere : appelé depuis la même machine, temps réseau compris, attente imposée par la limite de la clé d'essai (10 requêtes par minute) exclue. `Qwen3-Reranker-4B` a été écarté avant toute mesure de qualité : environ 300 s par question sur cette machine (mesure du 2026-11-08, 5 questions), soit plus de 12 h pour le `test`.

**Repères**, mesurés le 2026-11-08 sur les mêmes 44 items : dense top-5, rappel 0,73 ; dense top-20 (le A prévu), 0,92 ; dense top-50, plafond du reclassement, 0,95.

**Règle de choix**, fixée avant la mesure :

1. **Seuil d'intérêt.** Un candidat n'est retenu que s'il dépasse le dense top-5 d'au moins 3 items sur 44 (+0,07 de rappel au top-5). Si aucun ne le fait, le levier est abandonné avant tout run avec générateur.
2. **Qualité d'abord.** Parmi les candidats retenus, on prend celui qui a le meilleur rappel au top-5.
3. **Puis le temps.** Si un candidat retenu est au moins deux fois plus rapide (temps médian) et à 2 items ou moins du meilleur, on prend le plus rapide.

**Limite connue avant la mesure :** choisir le meilleur de trois candidats sur 44 items rend le gain mesuré en partie optimiste (leçon de la 003).

**Résultats** (2026-11-08 et 2026-11-09, 44 items `dev` avec réponse, 50 candidats reclassés en 5) :

| Configuration | Rappel top-5 | Tous les articles (top-5) | Rang 1 | Temps médian par question (pire cas) |
|---|---|---|---|---|
| Dense top-5, sans reclassement | 0,73 | 0,70 | 0,45 | — |
| **Cohere `rerank-v5.0-pro`** | **0,91** | **0,89** | **0,69** | **0,45 s** (0,59 s) |
| `bge-reranker-v2-m3` | 0,84 | 0,80 | 0,65 | 2,75 s (10,5 s) |
| `Qwen3-Reranker-0.6B` | 0,83 | 0,77 | 0,57 | 7,21 s (21,4 s) |
| Dense top-20 (le A prévu) | 0,92 | 0,91 | — | — |

| Mode (items) | Dense top-5 | Cohere | bge | Qwen 0,6B |
|---|---|---|---|---|
| `direct` (11) | 0,91 | 1,00 | 1,00 | 0,91 |
| `reference` (8) | 0,75 | 1,00 | 1,00 | 1,00 |
| `paraphrase` (10) | 0,50 | 0,70 | 0,50 | 0,60 |
| `multi_article` (8) | 0,62 | 0,88 | 0,75 | 0,69 |
| `lost_context` (7) | 0,86 | 1,00 | 1,00 | 1,00 |

**Application de la règle :**
1. **Seuil d'intérêt** (rappel top-5 ≥ 0,795, soit 3 items de plus que le dense top-5) : les trois candidats le franchissent.
2. **Qualité** : Cohere est le meilleur, à 0,91, avec 3 items d'avance sur bge et 3,5 sur Qwen.
3. **Temps** : aucun candidat retenu n'est plus rapide que Cohere.

**Modèle retenu** (décision du 2026-11-09) : **Cohere `rerank-v5.0-pro`**. Avec 5 passages, il retrouve presque autant d'articles attendus que la recherche dense avec 20 (0,91 contre 0,92), en 0,45 s par question. Les deux modèles locaux gagnent aussi, mais moins, et ajoutent 3 à 7 s par question sur cette machine.

**Incidents de mesure**, sans effet sur les rappels :
- **Taille des lots.** La première mesure de bge utilisait le défaut de `sentence-transformers`, 32 paires par lot : les annexes longues faisaient déborder la mémoire, à 66 s par question en médiane. `CrossEncoderReranker` envoie désormais 8 paires par lot. Les deux mesures de bge donnent le même rappel (0,841), ce qui confirme que la taille des lots ne change pas les notes ; le temps du tableau est celui des lots de 8.
- **Mesure de Qwen interrompue puis relancée.** Une première mesure a été arrêtée faute de mémoire sur la machine ; la mesure publiée a tourné seule, avec 83 % de mémoire libre au départ.
- **Instruction de Qwen.** `sentence-transformers` applique l'instruction par défaut du modèle (« query ») ; aucune n'a été écrite pour le Code de la consommation.

Les sections Question, Hypothèse, Protocole, Discipline d'itération et Mesures sont écrites après la pré-étude, avant le premier run avec générateur.

## Question

Sur le Code de la consommation, **reclasser les 50 premiers passages denses avec Cohere `rerank-v5.0-pro` et n'en envoyer que 5** donne-t-il au moins autant de réponses justes (`correct`, spec `rag-qa/v1`) qu'**envoyer les 20 premiers passages denses**, à générateur constant ?

## Hypothèse

- **H1 :** le RAG reclassé à 5 passages (B) ne répond pas moins juste que le RAG à 20 passages (A) de plus de 3 points, avec trois fois moins de tokens d'entrée. Sur les questions sans réponse, B invente moins : il envoie moins d'articles voisins.
- **H0 :** B répond moins juste que A de plus de 3 points.
- **Plus petit écart qui compte en pratique : 3 points de `correct`**, dans les deux sens : un gain de B sous 3 points ne justifie pas un fournisseur de plus, une perte sous 3 points vaut d'être échangée contre deux tiers de tokens en moins.

**Attentes secondaires**, qui ne portent pas le verdict : `hallucination` plus basse en B, surtout pour Mistral Small et Gemini Flash-Lite, que les 20 passages faisaient inventer dans la 004 ; `retrieval_miss` un peu plus haut en B (rappel de 0,91 contre 0,92 au `dev`) ; paraphrase toujours faible.

## Protocole

| Élément | Valeur |
|---|---|
| Baseline (A) | Le **RAG à 20 passages de la 004**, gelé : un passage par article, texte seul indexé, `mistral-embed`, cosinus exact, top-k = 20, prompts du gel de la 002 |
| Variante (B) | Les **50 premiers passages denses reclassés par Cohere `rerank-v5.0-pro`**, les 5 mieux notés envoyés au générateur (`ailab_rag.reranking.RerankingRetriever`, `POOL = 50`, k = 5). Chaque candidat est noté tel que le générateur le lira : « Article <numéro> », puis le texte |
| Ce qui change entre A et B | Les passages envoyés : les 20 premiers du classement dense pour A, les 5 premiers du classement reclassé pour B |
| Ce qui est fixé | Le générateur, les prompts de génération, le format de sortie, la température (0), l'index, la requête de recherche (la question seule), les données (`data/v1`) |
| Reclassement | Une note par candidat et par question, calculée avant la campagne et gardée en cache (`.cache/ailab_rag/rerank`) : les répétitions et les trois générateurs voient le même classement. Clé d'essai Cohere, 10 requêtes par minute ; un appel par question, soit 50 pour le `dev` et 150 pour le `test` |
| Générateurs | Un verdict par modèle : `mistral:mistral-small-2603`, `mistral:ministral-14b-2512`, `google:gemini-3.5-flash-lite`, ceux des 002 à 004. Identifiants vérifiés le 2026-11-09 (API Mistral `/v1/models`, API Google `v1beta/models`) |
| Golden set | `domains/droit-consommation/golden/rag-qa/v1` (publié) : n_dev = 50, n_test = 150. Le même `test` que les 002 à 004 |
| Répétitions | k = 3 |
| Implémentation | `python/`, sur les briques partagées `ailab_rag` |

**Deux comparaisons en une.** A et B diffèrent par l'ordre des passages (reclassement) et par leur nombre (20 contre 5). C'est voulu : la question posée est de savoir si un reclassement remplace la profondeur. La comparaison « reclassé à 5 contre dense à 5 » n'est pas mesurée sur la génération ; la pré-étude en donne la récupération (0,91 contre 0,73 au top-5).

**Trois fournisseurs dans B** pour Gemini Flash-Lite (Mistral pour les embeddings, Cohere, Google), deux pour les générateurs Mistral. La comparaison reste à générateur constant.

**Coût.** B ajoute un appel à Cohere par question (0,45 s en médiane au `dev`, clé d'essai) et retire 15 passages du prompt (environ 2 700 tokens d'entrée, d'après la 004). Le prix de l'API payante n'est pas publié sur la page des tarifs de Cohere (vérifié le 2026-11-08).

**Taille de l'échantillon.** Au run final de la 004, sur ce même `test`, s_d valait 0,31 à 0,35. Avec s_d = 0,33, le MDE sur 150 items vaut (1,976 + 0,844) × 0,33 / √150 ≈ **7,6 points**, et la demi-largeur de l'IC à 95 % environ **5,3 points**. Pour conclure à la non-infériorité (borne basse au-dessus de −3 points), il faut donc observer un delta d'au moins +2,3 points environ : **si les deux variantes se valent vraiment, l'expérience a peu de chances de le montrer** (de l'ordre d'une chance sur cinq). Écrit avant le premier run.

**Lancer un run** (depuis `python/`) :

```sh
uv run --env-file ../../../.env python -m exp005_rag.campaign \
    --split dev --model mistral:mistral-small-2603 --k 3 --run-dir ../runs/<nom>
```

La campagne reclasse d'abord toutes les questions du split (un appel à Cohere par question absente du cache, un toutes les 6 s) ; elle refuse de partir sans `COHERE_API_KEY`. Le run final ajoute `--split test --final --langfuse` et refuse de partir si l'arbre git n'est pas propre. Le `summary.json` est écrit avant l'envoi des traces à Langfuse, abandonné après 120 s.

## Discipline d'itération

1. **Même effort pour chaque variante.** A est le RAG à 20 passages de la 004 : il a reçu deux cycles de mise au point dans la 002 (consigne d'abstention, phrase d'ancrage) et aucun dans la 004. B a droit au même nombre de cycles sur le `dev`. A ne change pas.
2. **Gel avant le run final**, puis **un seul run sur le `test`**. Un run raté pour une raison technique se relance en entier, et l'incident est noté dans les Limites.

**Budget d'itération :** A, 2 cycles reçus, gelé ; B, N = 2 cycles sur le `dev`, avec Mistral Small. Le modèle de reclassement, la taille du lot (50) et le nombre de passages envoyés (5) sont fixés par la pré-étude et ne changent pas ; les cycles portent sur le prompt de génération.

**Journal d'itération**, sur le `dev` uniquement (Mistral Small, k = 3) :

| # | Date | Variante | Modification | Motif | `correct` dev |
|---|---|---|---|---|---|
| 0 | 2026-11-09 | A et B | aucune : mesure de départ (commit `3947d71`, sans Langfuse : serveur arrêté) | vérifier la chaîne, estimer s_d | A 0,873 · B 0,827 ; delta −0,047 [−0,113 ; +0,020]. Items avec réponse 0,894 → 0,871 ; `hallucination` 0,28 → **0,50** (6 items sans réponse : 5 exécutions sur 18 → 9) ; `retrieval_miss` 0,02 → 0,05 ; rappel au rang 1 0,45 → 0,69 ; tokens 4 234 → 1 508. Items B > A : 2, B < A : 4. Sur rq-146 (sans réponse), le reclassement place en tête des articles qui ressemblent à une réponse (un plafond d'amende voisin), et le modèle les reprend. s_d = 0,233 |

**Commit de gel :** le commit « Geler la 005 avant le run final sur le test » (2026-11-09). Son hash est enregistré dans le `summary.json` de chaque run (`run.commit`).

**Configuration gelée :** A, le RAG à 20 passages de la 004, inchangé ; B, les 50 premiers passages denses reclassés par Cohere `rerank-v5.0-pro`, 5 envoyés. Prompts de génération du gel de la 002 pour les deux variantes. **Budget utilisé : 0 cycle sur 2 pour B.** Au run 0, B perdait surtout sur les questions sans réponse (2 items sur 6) ; un cycle sur la consigne d'abstention aurait mêlé à cette expérience le levier « consigne d'abstention », prévu ensuite, et ajusté B sur 6 items du `dev`.
**Run final sur le `test` :** le 2026-11-09, [rapport](results/2026-11-09-run-final-test.md)

## Mesures

- **Métrique principale, qui porte le verdict :** `correct`, spec `rag-qa/v1` (§ 5).
- **Métriques secondaires, publiées sans porter le verdict :** répartition de `failure` (dont `retrieval_miss` et `generation_miss`), `evidence_recall@k` (k ∈ {1, 3, 5, 10}), `correct` par mode, `hallucination`, `false_abstention`, précision et rappel des citations, tokens du générateur par exécution, et **temps de réponse** :
  - **génération** : durée de l'appel au générateur, par exécution (`latency.generation_s`, champ hors spec ignoré par le scorer), en moyenne, médiane et 90e centile par variante ; les deux variantes tournent en parallèle dans la même campagne (4 exécutions à la fois) ;
  - **reclassement** (B seulement) : durée de chaque appel à Cohere pendant le reclassement d'avance des 150 questions du `test`, sans l'attente imposée par la clé d'essai (`run.rerank_s`) ;
  - la recherche dense n'est pas comptée : elle coûte le même appel d'embedding à A et à B.

  Ajouté le 2026-11-09, avant le gel et avant tout run sur le `test`, à la demande du propriétaire : un gain de 20 passages ne vaut que si le temps de réponse reste acceptable. Le run 0 du `dev` a tourné avant cet ajout et n'a pas de temps de génération.
- **Règle de verdict :** celle de la spec (§ 8) : B meilleure, B moins bonne ou non concluant.
- **Lecture de non-infériorité**, fixée avant le run et qui ne remplace pas le verdict : si la borne basse de l'IC à 95 % du delta est au-dessus de −0,03, « B ne fait pas moins bien que A de plus de 3 points » ; si la borne haute est sous −0,03, « B fait moins bien de plus de 3 points ».

## Résultats

Run final du 2026-11-09 sur les 150 items `test`, k = 3, 900 exécutions par générateur, aucune erreur. Détail dans le [rapport](results/2026-11-09-run-final-test.md).

| Générateur | `correct` A | `correct` B | Delta B − A [IC 95 %] | Temps médian A → B | Tokens A → B |
|---|---|---|---|---|---|
| `mistral-small-2603` | 0,847 | 0,833 | −0,013 [−0,056 ; +0,029] | 0,84 → ≈ 1,24 s | 3 962 → 1 531 |
| `ministral-14b-2512` | 0,840 | 0,836 | −0,004 [−0,056 ; +0,047] | 1,50 → ≈ 1,77 s | 3 972 → 1 540 |
| `gemini-3.5-flash-lite` | 0,878 | 0,858 | −0,020 [−0,065 ; +0,025] | 0,77 → ≈ 1,19 s | 4 106 → 1 594 |

- **Jeu égal sur la qualité** : B est à 0,4 à 2 points de A, sans que l'écart soit établi dans un sens ou dans l'autre.
- **B coûte 2,6 fois moins de tokens, mais répond plus lentement** : l'appel à Cohere (0,46 s en médiane) coûte plus que ce que la génération gagne à lire 5 passages au lieu de 20 (0,04 à 0,19 s).
- **Pas moins de réponses inventées** sur les questions sans réponse (0,49 → 0,46 pour Mistral Small, inchangées pour les deux autres).
- **A reproduit la 004** à 1,4 point près.

## Verdict

**Non concluant pour les trois générateurs**, deltas de −0,4 à −2,0 points. La non-infériorité à −3 points n'est établie pour aucun ; une perte de plus de 3 points ne l'est pas non plus. Pour Gemini Flash-Lite, un gain utile de B est exclu (borne haute +2,5 points).

Reclasser 50 candidats en 5 donne à peu près la même qualité qu'envoyer 20 passages : c'est un échange entre tokens (2,6 fois moins) et latence (+0,3 à 0,4 s par question, un fournisseur de plus), pas un gain de qualité. Aucun des deux ne fait moins inventer sur les questions sans réponse : c'est le levier suivant de la série.

## Limites

- **Audit du golden set (ajouté le 2026-11-09, après le run final).** Une relecture plus poussée des questions sans réponse de la v1 ([audit](../../domains/droit-consommation/golden/rag-qa/README.md#audit-des-questions-sans-réponse-de-la-v1-2026-11-09)) montre que 12 des 23 questions « sans réponse » du `test` ont en fait une réponse dans le code (valeur, renvoi à un autre texte ou classe d'amende). Sur ces items, un modèle qui donne la réponse du code est compté comme ayant inventé. Recalculés sans ces 12 items (138 items), les trois verdicts restent non concluants : −0,014 [−0,061 ; +0,032] (Mistral Small), +0,010 [−0,039 ; +0,058] (Ministral 14B), −0,022 [−0,068 ; +0,024] (Gemini Flash-Lite). Sur les 11 questions sans réponse valides, les réponses inventées A → B valent 0,30 → 0,24 (Mistral Small), 0,27 → 0,09 (Ministral 14B), 0,09 → 0,09 (Gemini Flash-Lite) : l'hypothèse « B invente moins » y trouve un indice, sur 11 items seulement, sans valeur de preuve.

- **Ministral 14B et Gemini Flash-Lite sans Langfuse** : deux échecs au démarrage, avant toute exécution, faute de mémoire dans la machine virtuelle de Docker (2,35 Go) ; relancés sans Langfuse sur le même commit, à la décision du propriétaire. Journaux dans `runs/incident-2026-11-09/`. Les JSONL font foi.
- **Docker redémarré avant le run** : deux conteneurs d'un autre projet occupaient les ports de Langfuse ; ils ont été arrêtés et la pile Langfuse recréée en gardant ses volumes.
- **Temps de réponse mesurés depuis un seul poste**, sous la charge des API ce jour-là.

Déjà connues avant le run :
- **B moins travaillée que A** : A a reçu deux cycles dans la 002, B aucun (gel au run 0).
- **Run 0 sans Langfuse** : le serveur était arrêté ; les JSONL du `dev` font foi.
- **Modèle de reclassement choisi sur le `dev`**, parmi trois candidats : son avance de la pré-étude est en partie optimiste.
- **Puissance faible pour la non-infériorité** (voir Taille de l'échantillon).
- **Clé d'essai Cohere** : ses conditions d'usage commercial ne sont pas vérifiées ; le modèle servi peut changer côté Cohere, mais les notes de l'expérience sont figées dans le cache.
- **Les limites de la 002 s'appliquent** : un seul corpus, questions rédigées par un LLM, golden set relu avec l'aide d'un LLM.
