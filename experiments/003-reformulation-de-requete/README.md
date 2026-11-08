# 003 — Reformuler la question avant la recherche ?

> **Statut :** cadrage
> **Domaines :** [`droit-consommation`](../../domains/droit-consommation/README.md)
> **Spec de notation :** [`rag-qa/v1`](../../evals/spec/rag-qa/v1/SPEC.md) (publiée)

Deuxième expérience de la série « notre RAG répond mal, quels sont les plus gros leviers ? ». La [002](../002-rag-naif-vs-modele-seul/README.md) a établi le RAG naïf et montré que sa récupération est le premier goulot : sur le `test`, 15 à 21 % d'échecs viennent d'un article attendu absent du contexte, contre 2 à 3 % de la génération. La 003 teste un levier de récupération contre ce RAG naïf, choisi par une pré-étude sur le `dev`.

Les sections Question, Hypothèse, Protocole, Discipline d'itération et Mesures sont écrites avant le premier run.

## Pré-étude : choisir le levier (2026-11-07, `dev` seulement)

Quatre leviers ont été mesurés sur la **récupération seule**, sans faire répondre de modèle, sur les 44 items `dev` qui ont une réponse : en-tête contextuel (numéro et plan dans le texte indexé), recherche hybride (BM25 + dense, fusion RRF k = 60), réécriture de requête (reformulation et HyDE) et top-k = 10. Mesure : `evidence_recall@k` de la spec, calculée par le banc `ailab_rag.bench`. Le `test` de la v1, qui resservira à la 003, n'a pas été analysé item par item.

| Configuration | Rang 1 | **Top-5** | Top-10 | Paraphrase (top-5) | Référence (top-5) | Plusieurs articles, tous (top-5) |
|---|---|---|---|---|---|---|
| Dense, baseline de la 002 | 0,45 | **0,73** | 0,81 | 0,50 | 0,75 | 0,50 |
| En-tête contextuel | 0,48 | 0,70 | 0,84 | 0,50 | 0,88 | 0,38 |
| Hybride, texte seul | 0,48 | 0,65 | 0,80 | 0,20 | 0,88 | 0,38 |
| Hybride + en-tête | 0,50 | 0,77 | 0,82 | 0,40 | 1,00 | 0,38 |
| Reformulation par Mistral Small | 0,49 | 0,73 | 0,83 | 0,70 | 0,62 | 0,25 |
| HyDE par Mistral Small | 0,33 | 0,69 | 0,73 | 0,50 | 0,75 | 0,38 |
| **Reformulation par Gemini 3.8 Flash** | 0,52 | **0,77** | 0,82 | **0,80** | 0,75 | 0,25 |
| HyDE par Gemini 3.8 Flash | 0,55 | 0,75 | 0,83 | 0,80 | 0,38 | 0,25 |

- **La paraphrase est le plus gros trou de la baseline** (0,50 au top-5) et aucun levier lexical ne la corrige : BM25 seul n'en retrouve aucune.
- **La reformulation par Gemini 3.8 Flash est le meilleur levier seul** : +4 points au top-5, +30 en paraphrase, sans perte sur la référence. Mistral Small reformule moins bien : il répond souvent à la question au lieu de la reformuler, en inventant un numéro d'article ou un montant.
- **Elle dégrade les questions sur plusieurs articles** (0,50 → 0,25) : en une phrase, la reformulation perd souvent l'un des deux sujets.
- **Tous ces écarts portent sur 44 items** : 4 points, ce sont 2 items.

**Levier retenu** (décision du 2026-11-07) : la reformulation de la question par Gemini 3.8 Flash. Le top-k = 10 (+8 points de rappel au top-10, sans appel supplémentaire) est gardé pour une expérience suivante.

## Question

Sur le Code de la consommation, **reformuler la question dans la langue du code avant la recherche** augmente-t-il le taux de réponses justes (`correct`, spec `rag-qa/v1`) d'un RAG naïf, à générateur constant ?

## Hypothèse

- **H1 :** le RAG avec reformulation (B) répond juste plus souvent que le RAG naïf (A), surtout sur les questions en paraphrase.
- **H0 :** pas de différence mesurable entre A et B.
- **Plus petit écart qui compte en pratique : 5 points de `correct`.** Un levier de récupération ajoute un appel par question ; en dessous de 5 points, il ne vaut pas sa latence ni son coût.

**Attentes secondaires**, qui ne portent pas le verdict : moins de `retrieval_miss` en B ; une baisse possible en mode `multi_article`.

## Protocole

| Élément | Valeur |
|---|---|
| Baseline (A) | Le **RAG naïf de la 002**, gelé : un passage par article, texte seul indexé, `mistral-embed`, cosinus exact, top-k = 5, prompts du gel de la 002 |
| Variante (B) | A, avec la question **reformulée par `google:gemini-3.8-flash`** avant la recherche. Le texte embarqué pour la recherche est la reformulation ; le générateur reçoit la question d'origine et les extraits trouvés |
| Ce qui change entre A et B | Le texte de la requête de recherche, et lui seul |
| Ce qui est fixé | Le générateur, les prompts de génération, le format de sortie, la température (0), l'index, le top-k, les données (`data/v1`) |
| Prompt de reformulation | « Réécris cette question d'un particulier avec le vocabulaire juridique du Code de la consommation français, en une seule phrase, sans y répondre. » (`ailab_rag.rewriting.REFORMULATE`, validé le 2026-11-07), température 0, réécritures en cache : une seule par question |
| Générateurs | Un verdict par modèle : `mistral:mistral-small-2603`, `mistral:ministral-14b-2512` et `google:gemini-3.5-flash-lite`, les trois modèles du run final de la 002. Identifiants à revérifier avant le run final |
| Golden set | `domains/droit-consommation/golden/rag-qa/v1` (publié) : n_dev = 50, n_test = 150. Le même `test` que la 002 |
| Répétitions | k = 3 |
| Implémentation | `python/`, sur les briques partagées `ailab_rag` |

**Deux modèles dans B.** La reformulation est faite par Gemini 3.8 Flash quel que soit le générateur. Pour le générateur Gemini Flash-Lite, les deux modèles sont du même fournisseur ; pour les générateurs Mistral, non. La comparaison reste à générateur constant, comme le veut la règle du lab.

**Taille de l'échantillon.** Au run 0 du `dev`, s_d = 0,417 : le MDE sur 150 items vaut (1,976 + 0,844) × 0,417 / √150 ≈ **9,6 points**, au-dessus des 5 points qui comptent. **L'expérience manque de puissance pour un gain de 5 points** : un résultat non concluant ne prouvera pas l'absence d'effet. Écrit avant le run final.

**Lancer un run :** commande à écrire avec l'implémentation.

## Discipline d'itération

1. **Même effort pour chaque variante.** A est le RAG naïf gelé de la 002, qui y a reçu deux cycles de mise au point (consigne d'abstention, phrase d'ancrage). B a droit au même nombre de cycles sur le `dev`, pour mettre au point sa reformulation. A ne change pas.
2. **Gel avant le run final**, puis **un seul run sur le `test`**.

**Budget d'itération :** A, 2 cycles reçus dans la 002, gelé ; B, N = 2 cycles sur le `dev`, avec Mistral Small.

**Écart au protocole d'origine (2026-11-08).** Le cadrage prévoyait aucun cycle pour B. C'était traiter B moins bien que A, qui a reçu deux cycles dans la 002. Le budget a été porté à deux cycles pour B après le run 0 du `dev` et avant tout run sur le `test` ; la règle est désormais écrite dans le `CLAUDE.md` du dépôt.

**Journal d'itération**, sur le `dev` uniquement (Mistral Small, k = 3) :

| # | Date | Variante | Modification | Motif | `correct` dev |
|---|---|---|---|---|---|
| 0 | 2026-11-07 | A et B | aucune : mesure de départ | vérifier la chaîne, estimer s_d | A 0,74 · B 0,72 ; delta −0,02 [−0,14 ; +0,10]. B : rang 1 0,45 → 0,52, top-5 0,73 → 0,77 ; paraphrase 0,73 → 0,80, référence 0,88 → 0,75, plusieurs articles 0,50 → 0,38. s_d = 0,417 |
| 1 | 2026-11-08 | B seulement (prompt de reformulation) ; A garde ses exécutions du run 0 | « … Garde tel quel tout numéro d'article cité, et garde tous les sujets de la question. » (`REFORMULATE_KEEP`, commit `75654d5`) | Au run 0, la reformulation perdait le numéro cité et l'un des sujets des questions sur plusieurs articles | A 0,74 · B 0,707 ; delta −0,03 [−0,15 ; +0,08]. Les reformulations gardent désormais numéros et sujets ; top-5 0,77 → 0,80, mais `generation_miss` 0,07 → 0,08 et référence toujours à 0,75. s_d = 0,411 |
| 2 | 2026-11-08 | B seulement (recherche) ; A garde ses exécutions du run 0 | Recherche avec la question **et** sa reformulation (prompt du cycle 1), classements fusionnés par RRF (k = 60, 50 passages par classement) (commit `30c8a04`) | Au cycle 1, la reformulation seule faisait perdre des modes que la question d'origine réussissait | A 0,74 · **B 0,76** ; delta +0,02 [−0,08 ; +0,12]. B sur les items avec réponse 0,79 (A 0,76) ; `retrieval_miss` 0,20 → 0,14 ; plusieurs articles 0,50 → 0,71 ; référence 0,88 = A ; paraphrase 0,70 (A 0,73) ; hallucination 0,39 → 0,44 |

**Run exploratoire, hors budget** : Ministral 14B comme générateur, prompt du cycle 1, 2026-11-08 : A 0,713 · B 0,733, delta +0,02 [−0,12 ; +0,16] ; paraphrase 0,60 → 0,90, référence 0,75 → 0,88, contexte perdu 0,86 → 0,57 ; aucune erreur de format, comme Mistral Small.

**Commit de gel :** à venir
**Run final sur le `test` :** à venir

## Mesures

- **Métrique principale, qui porte le verdict :** `correct`, spec `rag-qa/v1` (§ 5).
- **Métriques secondaires, publiées sans porter le verdict :** répartition de `failure` (dont `retrieval_miss`), `evidence_recall@k` (k ∈ {1, 3, 5}), `correct` par mode, `hallucination`, `false_abstention`, citations, tokens du générateur, et le coût de la reformulation (tokens et latence de Gemini 3.8 Flash).
- **Règle de verdict :** celle de la spec (§ 8).

## Résultats

À venir.

## Verdict

À venir.

## Limites

À compléter. Déjà connues :
- **Levier choisi sur le `dev`**, parmi huit configurations : le gain de la pré-étude est en partie optimiste (sélection du meilleur sur 44 items).
- **Deux fournisseurs dans B** pour les générateurs Mistral.
- **Les limites de la 002 s'appliquent** : un seul corpus, questions rédigées par un LLM, golden set relu avec l'aide d'un LLM.
