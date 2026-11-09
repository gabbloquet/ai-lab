# 005 — Reclasser 50 candidats pour n'en envoyer que 5 ?

> **Statut :** cadrage (pré-étude conclue le 2026-11-09)
> **Domaines :** [`droit-consommation`](../../domains/droit-consommation/README.md)
> **Spec de notation :** [`rag-qa/v1`](../../evals/spec/rag-qa/v1/SPEC.md) (publiée)

Quatrième expérience de la série « notre RAG répond mal, quels sont les plus gros leviers ? ». La [004](../004-top-k-20/README.md) a montré que les articles manqués par le RAG naïf sont classés entre la 6e et la 20e place : envoyer 20 passages au lieu de 5 fait gagner 7 à 8 points de `correct` à deux générateurs sur trois, mais triple les tokens et fait inventer davantage sur les questions sans réponse. La 005 teste l'autre façon de récupérer ces articles : un modèle de reclassement qui les remonte dans un contexte de 5 passages.

Le duel prévu, à confirmer après la pré-étude : A, le RAG à 20 passages de la 004 (gelé) ; B, les 50 premiers passages denses reclassés, réduits à 5.

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

Les sections Question, Hypothèse, Protocole, Discipline d'itération et Mesures seront écrites après la pré-étude, avant le premier run avec générateur.
