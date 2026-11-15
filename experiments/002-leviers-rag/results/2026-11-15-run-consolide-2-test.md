# 002 — Run consolidé 2 sur le `test` v5 (2026-11-15)

**Question** (protocole du README, « Run consolidé 2 ») : sur le `test` v5, notés par la spec `rag-qa/v2`, quels leviers des étapes 1 à 8 restent concluants ? Et quel est le tableau final des deltas de la 002, coût et latence compris ?

**Réponse.** Ce qui fait le plus de différence, c'est **le RAG lui-même**, puis **le générateur**. Les leviers de récupération et de consigne pèsent peu.
- **Le RAG** bat le modèle seul de 28 à 44 points de `correct`.
- **Changer de générateur** (étape 7) fait baisser les réponses inventées de 16 à 25 points, avec les quatre candidats. Il apporte aussi 5,6 points de `correct` avec Mistral Large 4, et 7,1 avec Gemini 4 Carbon.
- **20 passages au lieu de 5** ne restent concluants qu'avec Gemini Flash-Lite après la correction de Holm, et le reclassement n'apporte rien de plus.
- **La consigne d'abstention** fait moins inventer Ministral, échange des réponses inventées contre des abstentions à tort avec Mistral Small, et fait trop s'abstenir Gemini.
- **Le RAG agentique** (étape 8) n'est pas concluant avec Large 4 (+2,8 points). En revanche, la comparaison secondaire, déclarée d'avance, le confirme avec Carbon : +6,7 points, pour la meilleure configuration de la série (0,953). C'est aussi la plus chère (0,025 $ et 21 s par question).

## Provenance

| Élément | Valeur |
|---|---|
| Commit de gel | « Geler le run consolidé 2 de la 002 avant le test v5 » (`5aa5eae`), dépôt propre, `--final`. Il est enregistré dans chaque `summary.json` (`run.commit`) |
| Golden set | `domains/droit-consommation/golden/rag-qa/v5`, `items.jsonl` sha256 `9677d85172341b31ec5f71e030bda87ebe17a531126df63c5b0c22fca1426d53` ; 234 items `test` valides, dont 51 sans réponse, et 12 écartés par l'audit de la v1 (`audit/v1-unanswerable.jsonl`) |
| Données | `domains/droit-consommation/data/v1` |
| Spec de notation | `evals/spec/rag-qa/v2`, `SPEC.md` sha256 `332b854924a7fc025b7deb33d876e4d800cc3554c899f471cb8b7f5c83a334e6` ; scorer `ailab_evals.rag_qa_v2`, conforme aux 84 vecteurs, comme son jumeau Java |
| Lockfile | `uv.lock` sha256 `b507149987dd9c34e6fd1d1d58a5dd2606e3fd21f8be076bd015c3a2a405818f` (Pydantic AI 2.65.0, `mcp` 2.3.0, `mistralai` 3.7.0) |
| Lanceur | `exp002_leviers/consolidated2.py` sha256 `a5a23d5f15826ec5a5d4743bcd6be6b787d91ad7a5787b84f1529795ce759dcc` ; blocs A, B et C lancés en parallèle, puis `report`, le 2026-11-15. Sorties : `runs/consolidated2-test/` |
| Barème | celui de l'étape 7, relevé le 2026-11-12 sur [docs.mistral.ai/inference/pricing](https://docs.mistral.ai/inference/pricing) et [aistudio.google.com/docs/pricing](https://aistudio.google.com/docs/pricing). Le tarif de Carbon est celui du jour du run (2 / 10 $ par million de tokens), avant son passage à 4 / 20 $ le 1ᵉʳ décembre |
| Répétitions | k = 3 pour chaque configuration |

**Contrôle de reproduction** : il est passé avant tout appel payant pour les trois générateurs du bloc A.

**Incidents d'infrastructure** (rien n'a été réglé) :
- Dans le bloc C', 20 recherches ont échoué sur une erreur passagère de l'API d'embeddings de Mistral (19 fois le statut 503, une fois le 502), sur environ 2 200 appels d'outil. Le serveur MCP les a rendues au modèle comme une erreur interne à relancer, et ces relances comptent dans le plafond de 6 appels. Aucune exécution n'est en erreur.
- Mistral Small avec raisonnement a 9 sorties invalides sur 702 (1,3 %), comptées comme réponses fausses.

## Bloc A — étapes 1 à 6 (spec v2, § 8.1 à 8.3)

`correct`, delta [IC 95 %], et verdict corrigé par Holm sur les 6 comparaisons de chaque générateur :

| Comparaison | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| 1. `naive_rag` − `closed_book` | 0,402 → 0,761, **+0,359** [+0,288 ; +0,430], **meilleure** | 0,321 → 0,761, **+0,440** [+0,372 ; +0,508], **meilleure** | 0,434 → 0,711, **+0,276** [+0,206 ; +0,347], **meilleure** |
| 2. `query_rewrite` − `naive_rag` | −0,001 [−0,037 ; +0,034], non concluant | +0,003 [−0,033 ; +0,039], non concluant | +0,014 [−0,023 ; +0,052], non concluant |
| 3. `top_k_20` − `naive_rag` | +0,054 [+0,007 ; +0,101], non concluant après Holm (p_holm = 0,124) | +0,044 [−0,002 ; +0,090], non concluant | **+0,094** [+0,053 ; +0,135], **meilleure** |
| 4. `rerank_cohere` − `top_k_20` | −0,016 [−0,059 ; +0,027], non concluant | +0,003 [−0,034 ; +0,040], non concluant | −0,011 [−0,052 ; +0,029], non concluant |
| 4. `rerank_cohere` − `naive_rag` | +0,038 [−0,005 ; +0,082], non concluant | +0,047 [−0,002 ; +0,096], non concluant | **+0,083** [+0,036 ; +0,130], **meilleure** |
| 5. `abstain_strict` − `top_k_20` | −0,004 [−0,034 ; +0,026], non concluant | +0,037 [+0,008 ; +0,066], non concluant après Holm (p_holm = 0,060) | **−0,087** [−0,128 ; −0,045], **moins bonne** |

**Verdicts à deux critères** (§ 8.2). Critère principal : réponses inventées, sur 51 items. Garde : abstentions à tort, sur 183 items, avec une marge de 0,03.

| Étape | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| 5. Consigne d'abstention | inventées −0,085 [−0,155 ; −0,015] ; garde +0,038 [+0,011 ; +0,066] → **compromis** (`tradeoff`) | inventées −0,046 [−0,088 ; −0,004] ; garde +0,004 [−0,008 ; +0,015] → **meilleure** | inventées 0 ; garde +0,142 [+0,087 ; +0,197] → **moins bonne** |
| 6. Seuil Cohere | inventées −0,039 [−0,094 ; +0,016] ; garde +0,005 → non concluant | inventées −0,039 [−0,094 ; +0,016] ; garde +0,005 → non concluant | inventées 0 ; garde 0 → non concluant |

Pour l'étape 6, les deltas sont identiques entre les deux Mistral, et un recalcul indépendant à partir des exécutions le confirme. Le seuil écarte les mêmes 17 questions pour les trois générateurs, puisqu'il ne dépend que de la question, et chacun des deux Mistral y inventait 6 réponses sur 51 exécutions.

## Bloc B — étape 7, le générateur

A = `top_k_20` avec Mistral Small : `correct` = 0,815, réponses inventées = 0,248, 0,0006 $ et 0,8 s par question. Chaque critère a sa famille de Holm sur les 4 candidats.

| Candidat (réflexion) | `correct` | Delta [IC 95 %], Holm | Inventées | Delta [IC 95 %], Holm | Abstentions à tort | Coût par question | Latence médiane |
|---|---|---|---|---|---|---|---|
| Mistral Large 4 (`low`) | 0,870 | **+0,056** [+0,014 ; +0,097], **meilleure** | 0,013 | **−0,235** [−0,351 ; −0,119], **meilleure** | 0,097 | 0,0032 $ | 4,5 s |
| Gemini 4 Carbon (`low`) | 0,886 | **+0,071** [+0,025 ; +0,117], **meilleure** | 0,000 | **−0,248** [−0,365 ; −0,132], **meilleure** | 0,115 | 0,0092 $ | 5,5 s |
| Gemma 4 31B (`minimal`) | 0,859 | +0,044 [−0,002 ; +0,091], non concluant | 0,000 | **−0,248** [−0,365 ; −0,132], **meilleure** | 0,060 | — (palier gratuit) | 2,9 s |
| Mistral Small en raisonnement | 0,813 | −0,001 [−0,044 ; +0,041], non concluant | 0,085 | **−0,163** [−0,263 ; −0,064], **meilleure** | 0,093 | 0,0008 $ | 2,2 s |

La règle de choix de l'étape 8, appliquée cette fois au `test`, retiendrait aussi Mistral Large 4. Carbon est à moins de 2 points, mais il est plus cher. Le choix fait sur le `dev` tient donc.

## Bloc C — étape 8, le RAG agentique

| | `top_k_20` | `agentic_rag` (cycle 2 gelé) | Delta [IC 95 %] |
|---|---|---|---|
| **Large 4 (C, verdict de l'étape)** | 0,870 | 0,899 | +0,028 [−0,005 ; +0,062], **non concluant** |
| Réponses inventées / abstentions à tort | 0,013 / 0,097 | 0,026 / 0,035 | |
| `retrieval_miss` | 9,5 % | 6,2 % | |
| Appels d'outil (moyenne), part au plafond, part de `get_article` | — | 3,2 ; 14 % ; 6 % | |
| Coût par question / latence médiane | 0,0032 $ / 4,5 s | 0,0071 $ / 8,5 s | |
| **Carbon (C', secondaire, déclarée d'avance)** | 0,886 | **0,953** | **+0,067** [+0,032 ; +0,102], **meilleure** |
| Réponses inventées / abstentions à tort | 0 / 0,115 | 0 / 0,015 | |
| `retrieval_miss` | 10,6 % | 1,5 % | |
| Appels d'outil (moyenne), part au plafond, part de `get_article` | — | 3,1 ; 23 % ; 43 % | |
| Coût par question / latence médiane | 0,0092 $ / 5,5 s | 0,0248 $ / 20,9 s | |

## Tableau final de la 002 (`test` v5, `correct`, coût et latence par question)

| Configuration | `correct` | Inventées | Coût | Latence médiane |
|---|---|---|---|---|
| Modèle seul (Mistral Small) | 0,402 | 0,255 | 0,0001 $ | 0,75 s |
| RAG naïf, 5 passages (Mistral Small) | 0,761 | 0,216 | 0,0002 $ | 0,72 s |
| RAG à 20 passages (Mistral Small) | 0,815 | 0,248 | 0,0006 $ | 0,78 s |
| RAG à 20 passages (Large 4) | 0,870 | 0,013 | 0,0032 $ | 4,5 s |
| RAG à 20 passages (Carbon) | 0,886 | 0 | 0,0092 $ | 5,5 s |
| RAG agentique (Large 4) | 0,899 | 0,026 | 0,0071 $ | 8,5 s |
| **RAG agentique (Carbon)** | **0,953** | **0** | 0,0248 $ | 20,9 s |

Les latences se comparent entre elles : même machine, même période (protocole). Les réponses inventées, la latence et le coût du modèle seul et du RAG naïf viennent du bloc A (`runs/consolidated2-test/A/mistral-mistral-small-2603/`). Leur coût est calculé après coup, sur le même barème.

## Lecture

- **Le RAG reste le gain principal**, de 28 à 44 points de `correct`. Sur la v5, la récupération est presque saturée dès 20 passages. Les réponses inventées, elles, bougent peu avec le RAG chez Mistral Small (de 0,255 à 0,216 puis 0,248) : elles dépendent surtout du modèle.
- **Le générateur est le second levier, et le plus net sur les réponses inventées.** Large 4 et Carbon les font presque disparaître (de 25 % à 1 % et à 0 %), ce qu'aucun levier de récupération ni de consigne n'avait obtenu. C'était l'hypothèse de la pré-étude du 2026-11-10 : les réponses inventées dépendent du modèle.
- **Le raisonnement seul n'aide pas `correct`.** Il réduit les réponses inventées de Mistral Small (−16 points), mais il casse 1,3 % des sorties.
- **L'agentique dépend du modèle.** Large 4 cherche peu (6 % de lectures d'article) et gagne peu. Carbon lit des articles entiers (43 % de ses appels), rattrape presque tous les échecs de récupération (de 10,6 % à 1,5 %), et donne la meilleure configuration de la série. C'est l'exploration du `dev`, confirmée sur le `test`.
- **Les leviers de récupération et de consigne pèsent peu sur la v5.** 20 passages et le reclassement ne restent concluants qu'avec Gemini après Holm. La consigne d'abstention garde son profil : utile pour un modèle qui invente, nuisible pour un modèle qui n'invente pas.

**Écarts avec le run consolidé 1 (v4, spec v1).**
- `top_k_20` avec Ministral passe de concluant (+6,8 points) à non concluant (+4,4).
- La consigne d'abstention devient concluante avec Ministral.

Une partie de ces écarts vient de la spec v2, qui note plus sévèrement `comparison` (rattachement) et `false_premise` (rejet de la prémisse). Le reste tient au bruit : les deltas du run consolidé 1 tombent dans les IC de la v5 (+6,8 points dans [−0,2 ; +9,0] pour 20 passages, −3,9 points dans [−8,8 ; −0,4] pour les réponses inventées de la consigne).

**Pour un produit**, sur ce corpus :
- le RAG agentique avec Carbon, pour le meilleur taux de réponses justes ;
- le RAG à 20 passages avec Mistral Large 4, pour le meilleur compromis : 0,870 pour 0,003 $ et 4,5 s, soit 8 fois moins cher et 5 fois plus rapide que Carbon agentique, à 8 points près.

## Limites

- **Troisième regard sur ce `test` en agrégat** : le `test` v5 est le `test` v4 complété des champs v2, déjà lu par le run consolidé 1 et l'étape 6. Aucune configuration n'a été réglée dessus.
- **Petits effectifs pour certains critères.** 51 questions sans réponse : le MDE des réponses inventées est de 12 à 19 points. Les modes récents ont 12 à 30 items `test`, et leurs scores par mode sont indicatifs.
- **La température est ignorée par Gemini** (Flash-Lite et Carbon) : note du README, « Limites ».
- **Large 4 et Carbon ne coupent pas leur réflexion.** « Plus gros » et « de pointe » changent donc aussi la réflexion.
- **Coût** : les embeddings des requêtes ne sont pas comptés. Gemma n'a pas de coût connu. Le tarif de Carbon double au 1ᵉʳ décembre : Carbon agentique passerait alors à environ 0,05 $ par question.
- **Incidents d'embeddings du bloc C'** : 20 recherches relancées, qui ont consommé une partie du plafond d'appels de Carbon. L'effet est faible (environ 1 % des appels), mais il joue contre Carbon.
- **Pas de multi-hop dans la v5** : l'avantage de l'agentique sur un vrai saut n'est pas mesuré.
- **Écarts MCP du serveur** : pas de limite de débit dans le temps, et `server/discover` non testé (rapport de l'étape 8).
