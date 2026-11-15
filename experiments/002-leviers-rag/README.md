# 002 — Notre RAG répond mal : quels sont les plus gros leviers ?

> **Statut :** run consolidé conclu le 2026-11-09 ([rapport](results/2026-11-09-run-consolide-test.md)) ; étape 6 conclue le 2026-11-10 ([rapport](results/2026-11-10-etape-6-test.md))
> **Domaines :** [`droit-consommation`](../../domains/droit-consommation/README.md)
> **Spec de notation :** [`rag-qa/v1`](../../evals/spec/rag-qa/v1/SPEC.md) (publiée)

Une seule expérience, découpée en étapes (règle 1 du lab). Chaque étape juge un levier contre une baseline gelée, avec son propre protocole, son commit de gel et un seul run final. L'expérience conclut par le tableau des deltas de tous les leviers.

Jusqu'au 2026-11-09, ces étapes étaient présentées comme cinq expériences d'une « série ». Leurs dossiers et leurs rapports gardent leurs numéros (002 à 006), qui servent d'identifiants d'étape : rien n'est renommé, et les rapports publiés restent tels quels.

## Question

Sur des questions de consommateurs portant sur le Code de la consommation, quels leviers font gagner le plus de réponses justes (`correct`) à un RAG, et à quel coût (réponses inventées, tokens, latence) ?

## Étapes

Toutes les étapes ont tourné sur les trois mêmes générateurs : `mistral-small-2603`, `ministral-14b-2512` et `gemini-3.5-flash-lite`, avec k = 3 répétitions. Un verdict par modèle.

| Étape | Levier | Baseline (A) | Golden set | Verdict au run final de l'étape | Run consolidé (v4, `test` 234, après Holm) |
|---|---|---|---|---|---|
| 1 — [002](../002-rag-naif-vs-modele-seul/README.md) | RAG naïf (5 passages) | modèle seul | v1, `test` 150 | **+37 à +44 pts** de `correct`, les trois modèles | **+28 à +44 pts**, les trois modèles |
| 2 — [003](../003-reformulation-de-requete/README.md) | reformulation de la question | RAG naïf | v1, `test` 150 | non concluant (−0,7 à −0,9 pt) | non concluant (−0,3 à +1,3 pt) |
| 3 — [004](../004-top-k-20/README.md) | 20 passages au lieu de 5 | RAG naïf | v1, `test` 150 | +7,3 et +8,0 pts (Ministral, Gemini) ; non concluant avec Mistral Small (+4,0) | +6,8 et +10,4 pts (Ministral, Gemini) ; non concluant avec Mistral Small (+6,1, p_holm = 0,056) |
| 4 — [005](../005-reclassement/README.md) | reclassement Cohere, 50 candidats vers 5 | RAG à 20 passages | v1, `test` 150 | non concluant (−0,4 à −2,0 pts), 2,6 fois moins de tokens | non concluant (−1,0 à −2,1 pts), 2,5 fois moins de tokens ; contre 5 passages denses : +5,8 et +8,3 pts (Ministral, Gemini), non concluant avec Mistral Small |
| 5 — [006](../006-consigne-abstention/README.md) | consigne d'abstention plus exigeante | RAG à 20 passages | v3, `test` 190 | moins de réponses inventées avec Mistral Small (−9,2 pts) ; non concluant avec Ministral ; plus d'abstentions à tort avec Gemini (+8,7 pts) | non concluant avec Mistral Small (−3,3 pts, garde franchie) et Ministral ; plus d'abstentions à tort avec Gemini (+15,1 pts, −9,0 pts de `correct`) |
| 6 — [ci-dessous](#étape-6--sabstenir-daprès-le-score-de-reclassement) | abstention si le meilleur score Cohere est sous un seuil | RAG à 20 passages | v4, `test` 234 | — | non concluant pour les trois modèles : réponses inventées −2,6 (Mistral Small), −3,9 (Ministral), 0 (Gemini) pts ; garde tenue |
| 7 — [ci-dessous](#étape-7--le-générateur-comme-levier) | générateur : Mistral Large 4, Gemini 4 Carbon, Gemma 4 31B, Mistral Small avec raisonnement | RAG à 20 passages avec Mistral Small | v5, `dev` 118 | gelée le 2026-11-13 ; verdict au run consolidé 2 (`test` v5). Sur le `dev` : moins de réponses inventées avec les quatre candidats ; Large 4 retenu pour l'étape 8 | — |
| 8 — [ci-dessous](#étape-8--rag-agentique) | RAG agentique : recherche par outil MCP, autant d'appels que voulu (6 au plus) | RAG à 20 passages avec Mistral Large 4 | v5, `dev` 118 | gelée le 2026-11-15 ; verdict au run consolidé 2 (`test` v5). Sur le `dev` : +2,8 pts de `correct` (non concluant), 2,4 fois plus cher | — |

Les étapes 4 et 5 ont pris pour baseline la meilleure configuration du moment (20 passages) : l'expérience mêle donc des deltas isolés (contre le RAG naïf) et des deltas cumulés (contre 20 passages).

## Run consolidé sur le golden set v4

Les sections Question, Hypothèse, Protocole, Discipline d'itération et Mesures du run consolidé sont écrites le 2026-11-09, avant tout code et tout run. Décisions du propriétaire du même jour : un seul run, configurations gelées sans nouvelle itération, double lecture (isolée et cumulative), k = 3, consigne d'abstention de l'étape 5 telle quelle.

### Question du run

Sur le golden set v4, de combien chaque levier gelé fait-il varier `correct` : seul, contre le RAG naïf, et en plus des leviers précédents ?

### Hypothèse

- **H1** : chaque verdict d'étape se retrouve dans le même sens. Le RAG naïf bat largement le modèle seul ; 20 passages battent le RAG naïf ; la reformulation et le reclassement ne font rien gagner ; la consigne d'abstention fait moins inventer Mistral Small, sans gain pour les deux autres.
- **H0** : aucun écart mesurable entre une configuration et celle à laquelle on la compare.
- **Plus petit écart qui compte** : celui de chaque étape (10 points pour le RAG naïf, 5 pour la reformulation, 3 pour 20 passages et pour le reclassement). Pour la consigne d'abstention, ce sont les critères de l'étape 5.

### Protocole

| Élément | Valeur |
|---|---|
| Configurations | six, gelées, reprises **telles quelles** de leurs étapes (voir ci-dessous) |
| Ce qui change entre deux configurations comparées | un seul levier |
| Ce qui est fixé | générateurs, prompts, `temperature = 0`, index (`mistral-embed`, un passage par article, texte seul), spec `rag-qa/v1` |
| Générateurs | `mistral:mistral-small-2603`, `mistral:ministral-14b-2512`, `google:gemini-3.5-flash-lite` ; un verdict par modèle |
| Golden set | `rag-qa/v4`, split `test` : 246 items, dont 234 valides. Les 12 questions sans réponse de l'audit sont écartées de toutes les métriques du verdict |
| Répétitions | k = 3 |

| Configuration | Étape d'origine | Source gelée |
|---|---|---|
| `closed_book` | 1 (A) | `exp002_rag`, commit de gel `8d082ad` |
| `naive_rag` (5 passages) | 1 (B) | `exp002_rag`, `8d082ad` |
| `query_rewrite` | 2 (B) | `exp003_rag`, `13e7cab` (reformulations de `gemini-3.8-flash`, cache) |
| `top_k_20` | 3 (B) | `exp004_rag`, `b05ab07` |
| `rerank_cohere` (50 candidats vers 5) | 4 (B) | `exp005_rag`, `0102fde` |
| `abstain_strict` (20 passages + consigne) | 5 (B) | `exp006_rag`, `28bc317` (`STRICT_GROUNDING`) |

**Comparaisons**, six par modèle, fixées d'avance :

| Lecture | Comparaison | Étape |
|---|---|---|
| isolée et cumulative | `naive_rag` − `closed_book` | 1 |
| isolée | `query_rewrite` − `naive_rag` | 2 |
| isolée et cumulative | `top_k_20` − `naive_rag` | 3 |
| cumulative (comme à l'étape 4) | `rerank_cohere` − `top_k_20` | 4 |
| isolée (nouvelle) | `rerank_cohere` − `naive_rag` : 5 passages reclassés contre 5 passages | 4 |
| cumulative | `abstain_strict` − `top_k_20` | 5 |

**Taille de l'échantillon.** L'écart type des différences par item, mesuré aux runs finaux des étapes, vaut 0,31 à 0,35 pour les leviers de récupération, 0,26 à 0,32 pour le reclassement et 0,15 à 0,24 pour la consigne. Avec n = 234 et la formule du gabarit, le MDE vaut environ 5,7 à 6,4 points pour la récupération, 4,8 à 5,9 pour le reclassement et 2,8 à 4,4 pour la consigne. La correction de Holm le porte à environ 1,3 fois ces valeurs pour la comparaison la plus exigeante. L'écart de 3 points qui compte pour 20 passages et pour le reclassement reste donc sous le MDE : un « non concluant » n'y exclura pas un petit gain.

**Coût estimé** (2026-11-09, tarifs publics non vérifiés sur facture) : 8 à 13 $ pour les trois modèles, dont 0,6 à 5,5 $ pour Cohere selon son mode de facturation. Durée : environ une heure, les trois modèles en parallèle.

### Discipline d'itération

- **Aucun cycle sur le `dev`** : chaque configuration a reçu ses cycles dans son étape. Un run `dev` unique sert seulement à vérifier que le code de campagne reproduit les configurations gelées. Ses résultats ne servent à rien régler.
- **Contrôle de reproduction avant le gel** : sur les items de la v1, le code de campagne doit redonner les contextes récupérés des runs finaux des étapes, pour chaque configuration. C'est vérifiable sans appel au générateur.
- Commit de gel, puis un seul run final sur le `test`.

### Mesures

- **Verdict** : delta de `correct` par comparaison et par modèle, IC à 95 % apparié par item (moyenne sur les répétitions), p-values corrigées par Holm sur les six comparaisons de chaque modèle.
- **Consigne d'abstention** : critères de l'étape 5 (`hallucination` sur les 51 questions sans réponse valides, garde sur `false_abstention`).
- **Secondaires, sans porter le verdict** : `correct` par mode, `hallucination`, `false_abstention`, `failure`, `evidence_recall@k`, tokens, latence.
- Rapport daté dans `results/`, qui cite le golden set `rag-qa/v4`, la spec `rag-qa/v1` et les lockfiles.

### Code de campagne

Paquet `exp002_leviers` (`python/`), écrit par Claude sur délégation du propriétaire (2026-11-09). Le registre importe les fonctions de recherche des paquets d'étape sans les réécrire. Seule exception : le `naive_rag` de l'étape 1 construit son index dans une fonction privée. Le registre prend donc celui des étapes 2 et 3, qui fait la même recherche.

- **Contrôle de reproduction** (`python -m exp002_leviers.reproduction`, sur les caches seuls et sans clé d'API) : 968 contextes sur 968 identiques à ceux des runs finaux des étapes, ordre compris. Une seule référence n'est pas unanime : `rq-001` à l'étape 1, où 1 exécution sur 27 a vu deux articles dans l'ordre inverse. La référence est le contexte majoritaire. Le lanceur rejoue ce contrôle et refuse de partir s'il échoue.
- **Verdict** : une comparaison conclut si sa p-value corrigée par Holm est sous 0,05. Cette p-value est celle du test t apparié dont l'IC de la spec est l'inversion. Le verdict de la spec (IC à 95 % non corrigé) est publié à côté. Les deux critères d'abstention de l'étape 5 restent sans correction, comme à l'étape 5.
- **Run `dev` de contrôle** (2026-11-09, commit `f8ca40f`) : 3 modèles, k = 1, 91 items valides (l'audit en écarte 2 du `dev`). 6 × 91 exécutions par modèle, aucune erreur. Ses scores n'ont servi à rien régler.
- Hors protocole, non mesurée : la reprise de la prémisse en `false_premise`, faute de `false_value` dans les items.

## Verdict

Run consolidé du 2026-11-09, sur le `test` de `rag-qa/v4` (234 items valides, k = 3, commit de gel `f836315`). Détail, provenance et dispersion : [rapport](results/2026-11-09-run-consolide-test.md). En points de `correct`, IC à 95 % apparié, verdict après correction de Holm sur les six comparaisons de chaque modèle :

| Comparaison | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| RAG naïf − modèle seul | **+33,9** [+26,8 ; +41,0] | **+43,9** [+36,9 ; +50,8] | **+28,1** [+20,8 ; +35,4] |
| reformulation − RAG naïf | −0,3, non concluant | +1,3, non concluant | +0,9, non concluant |
| 20 passages − RAG naïf | +6,1 [+1,4 ; +10,8], non concluant après Holm | **+6,8** [+2,0 ; +11,6] | **+10,4** [+6,2 ; +14,6] |
| reclassement − 20 passages | −2,1, non concluant | −1,0, non concluant | −2,1, non concluant |
| reclassement − RAG naïf | +4,0, non concluant | **+5,8** [+1,3 ; +10,4] | **+8,3** [+3,5 ; +13,0] |
| consigne d'abstention − 20 passages | −0,3, non concluant | +0,7, non concluant | **−9,0** [−12,7 ; −5,3] |

Consigne d'abstention, critères de l'étape 5 : **non concluant** avec Mistral Small (réponses inventées −3,3 points [−9,3 ; +2,7], abstentions à tort +3,5 [+0,8 ; +6,1], garde franchie) et avec Ministral 14B (−3,9 [−11,3 ; +3,5]) ; **moins bonne** avec Gemini Flash-Lite (abstentions à tort +15,1 [+9,8 ; +20,5]).

**Réponse à la question.** Deux leviers font gagner des réponses justes : **le RAG naïf** (+28 à +44 points) et **envoyer plus de bons articles au générateur**, soit par 20 passages (+6 à +10 points), soit par un reclassement des 50 premiers candidats en 5 (+4 à +8 points, à 2,5 fois moins de tokens). Entre ces deux façons, l'écart est non concluant (−1,0 à −2,1 points) : les IC excluent un gain de 3 points pour le reclassement avec Mistral Small et Gemini, mais pas une perte de 3 points (bornes basses de −5,0 à −6,1). La reformulation ne change rien à 5 points près avec Mistral Small et Gemini ; avec Ministral, un gain de 5 points n'est pas exclu (borne haute +5,2). *(Phrase corrigée le 2026-11-15 : la version précédente écrivait « se valent ».)* La consigne d'abstention ne fait gagner à aucun modèle et coûte 9 points à Gemini.

**H1 est confirmée, sauf sur un point.** Les étapes 1 à 4 se retrouvent dans le même sens, Mistral Small restant non concluant pour 20 passages comme à l'étape 3. En revanche, la baisse des réponses inventées par la consigne d'abstention avec Mistral Small (−9,2 points à l'étape 5) ne se retrouve pas : −3,3 points, non concluant. Le nouveau delta reste dans l'IC de l'étape 5 (−15,7 à −2,6 points), mais n'exclut plus 0 : sur les mêmes 51 questions, le A de ce run invente moins que celui de l'étape 5 (0,222 contre 0,261), et l'effet de la consigne y est plus faible qu'on ne l'avait mesuré.

**Configuration recommandée sur ce corpus** : 20 passages. Le reclassement en 5 réduit les tokens de 2,5 fois, au prix d'un fournisseur de plus et sans qu'une perte de 3 points soit exclue. Pas de consigne d'abstention commune aux modèles.

## Pré-étude après le run consolidé : d'autres types de recherche (2026-11-09, `dev` seulement)

**Question** : un autre type de recherche que la recherche dense ferait-il mieux sur la v4 ? Seule la pré-étude de l'étape 2 l'avait mesuré, sur la v1, à 5 et 10 passages. Changer la mesure de similarité ne sert à rien : les vecteurs sont normalisés, et le cosinus, le produit scalaire et la distance euclidienne donnent le même classement. La recherche est déjà exacte.

**Mesure** : récupération seule, sans générateur, sur les 63 items du `dev` de `rag-qa/v4` qui ont une réponse. Rappel des articles attendus (`evidence_recall`, spec § 6) et part des items dont tous les articles attendus sont trouvés. Le script est `prestudy/search_v4_dev.py`. Il ne lit que les caches, sans clé d'API, donc sans aucun appel. Le `test` n'a pas été mesuré.

| Recherche | Rappel @5 | @10 | @20 | Tous les articles @5 | Tous @20 |
|---|---|---|---|---|---|
| Dense, cosinus (configurations du run consolidé) | 0,778 | 0,833 | 0,929 | 0,762 | 0,921 |
| Hybride BM25 + dense (fusion RRF, k = 60) | 0,690 | 0,841 | 0,865 | 0,651 | 0,841 |
| Dense + en-tête (numéro et plan indexés) | 0,762 | 0,873 | 0,937 | 0,730 | 0,921 |
| Hybride + en-tête | 0,825 | 0,857 | 0,905 | 0,794 | 0,889 |
| Reclassement Cohere de 50 candidats (étape 4) | **0,913** | 0,913 | **0,960** | **0,889** | **0,952** |

| Recherche, contre la dense | Items gagnés / perdus @5 | @20 |
|---|---|---|
| Hybride | 4 / 10 | 0 / 5 |
| Dense + en-tête | 4 / 5 | 3 / 3 |
| Hybride + en-tête | 8 / 4 | 1 / 3 |
| Reclassement Cohere | 12 / 1 | 3 / 0 |

- **L'hybride seul dégrade**, surtout en paraphrase (0,50 → 0,20 @5) : BM25 ne retrouve pas une question posée avec d'autres mots que l'article. On retrouve le constat de la pré-étude de l'étape 2.
- **Hybride + en-tête gagne un peu à 5 passages** (+4,7 points) et perd à 20. Il reste loin du reclassement, déjà jugé au run consolidé.
- **À 20 passages, la récupération est presque saturée sur le `dev`** : 93 % des articles attendus avec la recherche dense, 96 % avec le reclassement. Les articles manqués sont surtout en paraphrase (0,70 @20) et en comparaison (0,75, sur 4 items).
- **63 items** : un item vaut 1,6 point. Seuls les écarts du reclassement sont nets.

**Décision du propriétaire** (2026-11-09) : pas d'étape sur le type de recherche. Les erreurs qui restent avec 20 passages ne viennent plus surtout de la récupération. Une piste n'est pas couverte, parce qu'elle demande un appel : un autre modèle d'embedding, qui obligerait à encoder les 2 150 articles chez un autre fournisseur.

## Pré-étude : s'abstenir d'après le score de reclassement (2026-11-09, `dev` seulement)

**Question** : le meilleur score de reclassement Cohere d'une question sépare-t-il les questions avec réponse des questions sans réponse assez nettement pour décider d'une abstention sans le générateur ? Ce levier vise la plus grosse erreur qui reste aux deux modèles Mistral avec 20 passages : environ 22 % de réponses inventées aux questions sans réponse du `test` (run consolidé). L'étape 5 a montré qu'une consigne ne se transfère pas d'un modèle à l'autre ; un seuil sur la récupération ne dépend pas du générateur.

**Mesure** : les 91 items valides du `dev` de `rag-qa/v4` (63 avec réponse, 28 sans réponse). Pour chaque question, le meilleur score Cohere (`rerank-v5.0-pro`) sur ses 50 candidats denses, lu dans le cache. Pour chaque seuil, une exécution dont la question est sous le seuil est remplacée par une abstention, puis notée par la spec. Les réponses sont celles du run `dev` de contrôle du run consolidé (k = 1, commit `f8ca40f`). Ce run ne devait rien régler pour le run consolidé ; s'en servir ici, une fois le run consolidé conclu, est une décision du propriétaire (2026-11-09). Script : `prestudy/rerank_threshold_v4_dev.py`, caches seuls, sans aucun appel.

Meilleur score Cohere : médiane 0,632 pour les questions avec réponse, 0,270 pour les questions sans réponse ; AUC 0,917.

| Seuil | Questions avec réponse écartées (sur 63) | Questions sans réponse écartées (sur 28) |
|---|---|---|
| 0,10 | 0 | 2 |
| 0,15 | 0 | 6 |
| **0,20** | **0** | **10** |
| 0,25 | 2 | 13 |
| 0,30 | 2 | 15 |
| 0,40 | 7 | 21 |
| 0,50 | 15 | 26 |

Effet avec 20 passages (`top_k_20`), sans seuil → seuil 0,20 :

| Générateur | Réponses inventées (28 items) | Abstentions à tort (63 items) | `correct` (91 items) |
|---|---|---|---|
| `mistral-small-2603` | 0,321 → **0,179** | 0,016 → 0,016 | 0,791 → 0,835 |
| `ministral-14b-2512` | 0,179 → 0,143 | 0,000 → 0,000 | 0,879 → 0,890 |
| `gemini-3.5-flash-lite` | 0,000 → 0,000 | 0,143 → 0,143 | 0,879 → 0,879 |

- **Le seuil 0,20 n'écarte aucune question avec réponse** et en écarte 10 sans réponse. Pour la plupart, le générateur s'abstenait déjà : le gain porte sur 4 questions avec Mistral Small, 1 avec Ministral, aucune avec Gemini, qui n'invente pas.
- **Au-delà de 0,20, les abstentions à tort montent** (2 questions avec réponse écartées à 0,25, 7 à 0,40). Le palier sans perte va de 0,10 à 0,20.
- **Reclassement vers 5 passages** (`rerank_cohere`) : même tendance (Mistral Small 0,250 → 0,179 à 0,20).
- **Petit échantillon** : 28 questions sans réponse et une seule répétition ; une question vaut 3,6 points.

**Décision du propriétaire** (2026-11-09) : rédiger le protocole d'une étape 6 sur ce levier, ci-dessous, à relire avant tout calcul sur le `test`.

## Étape 6 — s'abstenir d'après le score de reclassement

Les sections Question, Hypothèse, Protocole, Discipline d'itération et Mesures sont écrites le 2026-11-09, après la pré-étude et avant tout calcul sur le `test`.

### Question

Sur le golden set v4, s'abstenir quand le meilleur score de reclassement Cohere de la question est sous 0,20 fait-il baisser les réponses inventées aux questions sans réponse du RAG à 20 passages, sans faire augmenter les abstentions à tort, à générateur constant ?

### Hypothèse

- **H1** : moins de réponses inventées avec Mistral Small et Ministral 14B ; aucun effet avec Gemini Flash-Lite, qui n'invente presque pas (0,020 au run consolidé) ; la garde tient pour les trois.
- **H0** : aucun écart mesurable des réponses inventées.
- **Plus petit écart qui compte** : 10 points de réponses inventées, comme à l'étape 5.

### Protocole

| Élément | Valeur |
|---|---|
| Baseline (A) | `top_k_20` du run consolidé, gelé (commit `f836315`) : ses exécutions `test` telles quelles |
| Variante (B) | A, sauf pour les questions dont le meilleur score Cohere (`rerank-v5.0-pro`, 50 candidats denses) est sous **0,20** : abstention, sans appel au générateur |
| Ce qui change entre A et B | la seule décision de s'abstenir sous le seuil |
| Ce qui est fixé | générateurs, prompts, `temperature = 0`, index, 20 passages, spec `rag-qa/v1` |
| Générateurs | `mistral:mistral-small-2603`, `mistral:ministral-14b-2512`, `google:gemini-3.5-flash-lite` ; un verdict par modèle |
| Golden set | `rag-qa/v4`, split `test` : 234 items valides (51 sans réponse, 183 avec réponse), les 12 items de l'audit écartés comme au run consolidé |
| Répétitions | k = 3, celles du run consolidé |

**Calcul sans appel.** B ne fait aucun appel que A n'ait fait : au-dessus du seuil, sa réponse est celle de A ; en dessous, c'est une abstention. Le résultat de B se calcule donc exactement à partir des exécutions `test` de A et des notes Cohere des 234 questions, toutes en cache (vérifié le 2026-11-09, sans lire leurs valeurs). Coût : 0 $. Refaire tourner le générateur n'ajouterait que son bruit.

**Taille de l'échantillon.** Sur le `dev`, l'écart type de la différence par question vaut 0,356 pour Mistral Small, 0,189 pour Ministral et 0 pour Gemini. Avec n = 51 : MDE ≈ (2,01 + 0,85) × s_d / √51, soit **14 points** pour Mistral Small et 8 pour Ministral. Pour Mistral Small, un effet de 10 points peut passer inaperçu. Les 3 répétitions du `test` lissent un peu la dispersion.

### Discipline d'itération

- **Budget** : A, le RAG à 20 passages, a reçu 2 cycles (ceux du RAG naïf, à l'étape 1) et aucun à l'étape 3. B y a droit aussi, mais B n'a pas de prompt à régler : son seul paramètre, le seuil, est fixé par la pré-étude, comme k = 20 l'a été pour l'étape 3. **Aucun cycle** n'est prévu.
- **Un écart à signaler** : le seuil a été choisi sur le `dev` parmi 9 valeurs, d'après les réponses du run `dev` de contrôle, avec une seule répétition.
- **Commit de gel** du code de calcul et du seuil, puis **un seul calcul sur le `test`**.

**Code** : `python/src/exp002_leviers/step6.py`, écrit par Claude sur délégation du propriétaire (2026-11-10), avec `RerankingRetriever.best_score` dans `ailab_rag.reranking`, qui lit le même cache que le reclassement. Le calcul refuse une baseline `test` qui ne vient pas du run final gelé (`f836315`). Vérification sur le `dev` (`--split dev`) : il redonne exactement les chiffres de la pré-étude. Le contrôle de reproduction du run consolidé passe toujours (968 contextes sur 968).

**Commit de gel** : « Geler l'étape 6 de la 002 avant le calcul sur le test » (2026-11-10), enregistré dans chaque `summary.json` (`run.commit`).

### Mesures

- **Verdict** : la règle à deux critères de l'étape 5, sans correction. Critère principal : delta apparié des réponses inventées (B − A) sur les 51 questions sans réponse valides, IC de Student à 95 %. Garde : delta des abstentions à tort sur les 183 questions avec réponse, à ne pas augmenter de plus de 0,03 (`ailab_evals.paired.joint_verdict`).
- **Secondaires, sans porter le verdict** : delta de `correct` (règle de la spec), part des questions écartées par le seuil (avec et sans réponse), `correct` par mode.
- Rapport daté dans `results/`, qui cite `rag-qa/v4`, la spec `rag-qa/v1`, le commit de gel du run consolidé, celui de l'étape 6, et `uv.lock`.

### Verdict de l'étape 6

Calcul unique sur le `test` le 2026-11-10 (commit de gel `0a5a9f4`, sans aucun appel) : [rapport](results/2026-11-10-etape-6-test.md).

- **Mistral Small : non concluant**, réponses inventées −2,6 points [−6,3 ; +1,1], garde tenue (+0,5 [−0,5 ; +1,6]).
- **Ministral 14B : non concluant**, −3,9 points [−9,4 ; +1,6], garde tenue.
- **Gemini Flash-Lite : non concluant**, aucun changement (0,020 → 0,020), garde tenue.

Un gain de 10 points est exclu pour les deux modèles Mistral. Le seuil écarte 16 questions sans réponse sur 51, mais le générateur s'y abstenait déjà presque toujours. Les réponses inventées portent surtout sur les 35 autres, où un article voisin obtient un score élevé (29 % de réponses inventées avec Mistral Small, contre 8 % sous le seuil). Un signal de récupération ne distingue pas ce cas d'une vraie réponse. Le levier qui reste pour ces questions est dans la génération, une vérification de la réponse par exemple, et non dans la recherche.

## Pré-étude : où cassent les erreurs qui restent (2026-11-10, `dev` seulement)

**Question** : avec les configurations jugées, les erreurs qui restent viennent-elles de la récupération ou de la génération, et dans quels modes ? La réponse décide du côté où chercher un prochain levier.

**Mesure** : le run `dev` de contrôle du run consolidé (k = 1, trois modèles), relu sans aucun appel par `prestudy/failures_v4_dev.py`. Chaque exécution d'une question avec réponse est classée par la catégorie `failure` du scorer (spec § 6) : `retrieval_miss` si un article attendu manque au contexte, `generation_miss` s'ils y sont tous et que la réponse est fausse. 63 items avec réponse × 3 modèles = 189 exécutions par configuration. Le script lit les runs locaux, que git ignore. Le `test` n'a pas été relu item par item.

| Configuration | `correct` | `generation_miss` | `retrieval_miss` |
|---|---|---|---|
| `naive_rag` | 136 | 14 | 39 |
| `top_k_20` | **162** (0,857) | **20** | **7** |
| `rerank_cohere` | 157 | 20 | 12 |

- **Avec 20 passages, la récupération ne rate plus que 3 items** (`rq-005`, `rq-192` en `paraphrase`, `rq-334` en `comparison`) : 7 exécutions, soit au plus 3,7 points à regagner sur le `dev` pour un levier de récupération.
- **Suivre les renvois entre articles ne rattraperait aucun de ces échecs.** 1 295 articles du corpus sur 2 150 citent un autre article, mais aucun article manquant d'un item en échec n'est cité par le contexte. Dans l'autre sens, un seul (L341-42, `rq-334`) cite le contexte, et l'item manque aussi L341-49.
- **Les erreurs de génération se concentrent sur `set`** : 10 exécutions sur 15. Ce sont surtout des listes incomplètes alors que l'article est dans le contexte (`rq-298`, `rq-329`). Un seul cas net est un faux négatif du scorer par mots-clés (`rq-267` avec Mistral Small : « évaluer et contrôler l'activité » n'est pas reconnu comme « évaluer leur activité »).
- **Réponses inventées aux 28 questions sans réponse** (`top_k_20`) : 9 avec Mistral Small, 5 avec Ministral 14B, 0 avec Gemini Flash-Lite.
- **Le `dev` ne reproduit pas la difficulté du `test` sur les modes nouveaux** : `multi_article` y fait 23/24 et `comparison` 9/12, contre 0,48 à 0,70 au `test`. Ces modes comptent 4 à 8 items `dev` : un levier qui les viserait ne pourrait pas s'y régler.

**Décision du propriétaire** (2026-11-10) : pas de levier taillé pour corriger les réponses inventées d'un modèle. Le générateur est lui-même un levier, et les conclusions de l'expérience le traiteront comme tel.

## Étape 7 — le générateur comme levier

Les sections Question, Hypothèse, Protocole, Discipline d'itération et Mesures sont écrites le 2026-11-12. C'est après le run `dev` de contrôle sur la v5 ([rapport](results/2026-11-12-controle-dev-v5.md)) et le smoke test des candidats, et avant tout run des candidats sur le `dev` ou le `test`. Les candidats ont été vérifiés à la source le 2026-11-12 (plan de la 002).

### Question

Sur le golden set v5, avec le RAG à 20 passages et les prompts gelés, remplacer le générateur Mistral Small 2603 change-t-il la part de réponses justes, et la part de réponses inventées aux questions sans réponse ? Et pour quel coût par question ?

### Hypothèse

- **H1, par candidat.** A est `mistral-small-2603` sans réflexion : `correct` = 0,785 et réponses inventées = 0,238 au contrôle `dev`.
  - **Mistral Large 4** (réflexion `low`) : plus de réponses justes et moins de réponses inventées. Avec 20 passages, les échecs viennent surtout de la génération (16 % de `generation_miss` au contrôle), et c'est ce qu'un modèle plus gros devrait corriger.
  - **Gemini 4 Carbon** (réflexion `low`) : le gain le plus grand sur les deux critères. Gemini Flash-Lite, de la même famille, n'invente aucune réponse avec 20 passages. C'est une hypothèse tirée d'un modèle d'une autre génération, pas un résultat.
  - **Gemma 4 31B** : pas d'hypothèse de sens. C'est la mesure d'un modèle ouvert d'une autre famille.
  - **Mistral Small avec raisonnement** : plus de réponses justes sur les modes à plusieurs éléments (`set`, `comparison`, `multi_article`). Pas d'hypothèse de sens sur les réponses inventées.
- **H0** : aucun écart mesurable entre A et B, sur aucun des deux critères.
- **Plus petits écarts qui comptent.**
  - **5 points de `correct`** : c'est l'écart entre les générateurs actuels au contrôle (de 0,785 à 0,833). En dessous, un générateur de 3 à 10 fois plus lent, et jusqu'à 18 fois plus cher, ne se justifie pas.
  - **10 points de réponses inventées**, comme aux étapes 5 et 6.

### Protocole

| Élément | Valeur |
|---|---|
| Baseline (A) | `top_k_20` avec `mistral-small-2603`, sans paramètre de réflexion (63 tokens de sortie en médiane au contrôle), `temperature = 0` : la configuration gelée du run consolidé |
| Variantes (B) | `mistral-large-4-0` (réflexion `low`) ; `gemini-4-carbon` (réflexion `low`, sans `temperature`) ; `gemma-4-31b-it` (réflexion `minimal`, `temperature = 0`) ; `mistral-small-2603` avec `reasoning_effort = "high"`. Les réglages sont dans `exp002_leviers.step7.generators()` |
| Ce qui change entre A et B | le générateur, avec les réglages qu'il impose : niveau de réflexion, et `temperature` absente pour Gemini, qui l'ignore |
| Ce qui est fixé | la récupération (`top_k_20` : index `mistral-embed`, 20 passages, caches de l'étape 3) ; le prompt système et la phrase d'ancrage (`ailab_rag.prompting`) ; la sortie structurée `ModelAnswer` par l'outil de sortie de Pydantic AI, sans seconde chance ; la spec `rag-qa/v2` ; l'audit de la v1 (2 items `dev` et 12 items `test` écartés) |
| Golden set | `rag-qa/v5` : n_dev = 118 items valides, n_test = 234 (dont 51 sans réponse) |
| Répétitions | k = 3 |
| Implémentation | `python/` : campagne `ailab_rag`, scorer `ailab_evals.rag_qa_v2`. Le scorer Java est conforme aux mêmes vecteurs |

**Critères et verdict** (spec v2, § 8.1 et § 8.3).
- **Critère principal : `correct`**, en `higher_better`. Les 4 comparaisons B − A forment une famille de Holm, avec α = 0,05. Le verdict corrigé porte celui de chaque candidat.
- **Second critère : `hallucination`**, sur les questions sans réponse, en `lower_better`. Il a sa propre famille de Holm sur les 4 candidats, et son propre verdict corrigé. Les deux verdicts sont publiés côte à côte ; il n'y a pas de verdict joint.
- **Publiés sans verdict** : `false_abstention`, taux d'erreur, coût par question, latence, `correct` par mode, répartitions de `failure` et de `premise`.

**Moment du verdict.** L'étape s'arrête à son gel sur le `dev`. Son verdict vient du run consolidé 2 sur le `test` v5, qui rejoue toutes les configurations gelées. C'est le seul nouveau regard sur ce `test` (décision du propriétaire, 2026-11-12).

**Choix du générateur de l'étape 8**, fixé ici avant tout run des candidats, et fait sur le `dev`. On prend le candidat, ou la baseline, qui remplit ces conditions :
- le meilleur `correct` ;
- un taux d'erreur de sortie structurée sous 1 % ;
- des réponses inventées pas pires que A : la borne haute de l'IC du delta reste sous +0,10.

En cas d'écart de `correct` de moins de 2 points, on prend le moins cher.

**Coût** (spec v2, § 3.2 et § 10).
- **Calcul.** `cost_usd` = tokens d'entrée × prix d'entrée + tokens de sortie × prix de sortie, calculé après coup pour chaque exécution.
- **Tokens de sortie.** Pour Gemini, ils comptent la réflexion (vérifié le 2026-11-12 : 12 217 tokens de sortie, dont 11 302 de réflexion). Pour Mistral, ce point est à vérifier sur le run `dev`.
- **Barème.** Celui du jour du run, relevé sur docs.mistral.ai/inference/pricing et aistudio.google.com/docs/pricing, et cité avec sa date. Carbon passe de 2 / 10 $ à 4 / 20 $ par million de tokens le 1ᵉʳ décembre : le rapport donne les deux tarifs.
- **Gemma** : coût `null`, puisque le palier gratuit ne représente pas un hébergement.

**Latence.** C'est `latency_s` de la spec v2 : de bout en bout, réseau du fournisseur compris, recherche servie par les caches. Les latences ne se comparent qu'entre runs de la même période : au run consolidé 2, où tout tourne ensemble.

**A sur le `dev`.** A est repris du run `dev` de contrôle, au lieu d'être relancé : sa configuration est la même. Les latences du `dev` ne se comparent donc pas entre A et B.

**Taille de l'échantillon.**
- **Sur `correct`** : s_d = 0,31 à 0,35 (comparaisons du run consolidé) et n = 234. Le MDE vaut 5,7 à 6,4 points, et 6,8 à 7,7 avec Holm sur 4 comparaisons. Le plus petit écart qui compte (5 points) est en dessous : un « non concluant » n'exclura pas un gain de cette taille.
- **Sur `hallucination`** : n = 51 et s_d = 0,30 à 0,40. Le MDE vaut 12 à 16 points, et 14,5 à 19 avec Holm. Seul un écart de l'ordre de celui entre Mistral Small (0,238) et Gemini Flash-Lite (0) au contrôle sera détectable.

**Limites connues avant le run.**
- **Large 4 et Carbon ne peuvent pas couper leur réflexion.** « Plus gros » et « de pointe » changent donc aussi la réflexion, même au niveau le plus bas.
- **Gemma tourne sur le palier gratuit.** Ses quotas ne sont pas documentés ; la campagne relance après une limite de débit.
- **`temperature = 0` avec la réflexion Mistral** : l'effet n'est pas documenté par Mistral.
- **Pydantic AI 2.65 ramène tout effort de réflexion à `high` chez Mistral.** `ailab_rag.generators.MistralEffortModel` envoie l'effort demandé ; le smoke test l'a confirmé par les tokens de sortie (263 à 547 pour Large 4 en `low`).

**Lancer un run :** `uv run --env-file .env python -m exp002_leviers.step7 --split dev`. Ce lanceur reste à écrire.

### Discipline d'itération

- **Aucun cycle de réglage.** Les prompts, la récupération et le format de sortie sont gelés. Le seul changement est le générateur, avec ses réglages fixés dans `step7.generators()` avant tout run. Un seul run `dev` des candidats est prévu. Il sert de contrôle d'intégration à grande échelle (taux d'erreur, sortie structurée) et au choix du générateur de l'étape 8.
- **Écart assumé.** Les baselines des étapes précédentes ont reçu 2 cycles sur le `dev`, et les candidats aucun. Ce n'est pas un désavantage, puisqu'il n'y a rien à régler.
  - Un candidat qui échoue sur la sortie structurée garde ses erreurs, comptées comme réponses fausses.
  - On ne règle ni son prompt ni son format pour lui : ce serait tailler un levier pour un modèle (décision du 2026-11-10).
- **Ce qu'un run `dev` peut changer** : seulement les incidents d'infrastructure (identifiant retiré, quota épuisé, erreur 400 sur un paramètre). Chaque correction est écrite ici avant tout run `test`. Un résultat du `dev` ne change ni les candidats, ni leurs réglages, ni les critères.
  - **Incident du 2026-11-12, au premier run `dev`.** Le run s'est arrêté sur Gemma, après 4 exécutions, sur une erreur 429 : le palier n'admet que 16 000 tokens d'entrée par minute, soit environ 4 requêtes par minute avec 20 passages. Large 4 et Carbon avaient fini (354 exécutions chacun) ; aucune exécution n'a été notée à tort. Deux corrections d'infrastructure, avant toute reprise :
    - la campagne attend au moins le délai demandé par le fournisseur (`retry_after`) ;
    - elle relance aussi les limites de débit et les coupures réseau, que Pydantic AI 2.65 lève sous des classes qui ne dérivent pas de `ModelHTTPError`.

    Gemma tourne ensuite seul, une requête à la fois, avec 30 tentatives au plus. Ni les candidats, ni leurs réglages, ni les critères ne changent.
  - **Conséquence pour les runs précédents.** Au run `dev` de contrôle, 4 coupures réseau (`ReadError`) de Gemini Flash-Lite ont été comptées comme réponses fausses (0,6 % d'erreurs en `closed_book` et `naive_rag`), comme le prévoit la spec. Elles seraient relancées aujourd'hui.
- **Gel.** Le commit de gel précède le run consolidé 2. Il porte le registre des générateurs, le barème relevé et le lanceur. Le `test` v5 ne se lance qu'avec `--final`, sur un arbre git propre.
- **Interdit avant le run consolidé 2** : faire tourner un candidat sur le `test` v5, ou analyser ses échecs item par item.

### Mesures

| Mesure | Définition | Rôle |
|---|---|---|
| `correct` | spec v2, § 5.5 ; une erreur compte comme une réponse fausse | critère principal, verdict corrigé par Holm (4 candidats) |
| `hallucination_rate` | part des questions sans réponse où le modèle ne s'abstient pas (§ 7) | second critère, verdict corrigé par Holm (4 candidats) |
| `false_abstention_rate` | part des questions avec réponse où le modèle s'abstient | publié |
| `error_rate` | part des exécutions en erreur, dont les sorties structurées invalides | publié ; seuil de 1 % pour l'étape 8 |
| Coût par question | moyenne de `cost_usd`, barème daté, Gemma exclu | publié en dollars, jamais en tokens entre fournisseurs |
| Latence | médiane et 95ᵉ centile de `latency_s` | publiée, seulement entre runs de la même période |
| Tokens de sortie | médiane par générateur | publiée : c'est la trace de la réflexion |
| `correct` par mode | § 7 | publié ; `set` et `comparison` à titre indicatif (7 et 9 items `dev`) |
| `failure`, `premise` | répartitions du § 7 | publiés |

Le rapport cite la spec `rag-qa/v2`, le golden set v5, `uv.lock`, le commit de gel, le barème avec sa date et ses URL, et les réglages de chaque générateur. Il dit aussi quels générateurs respectent `temperature`, et quel niveau de réflexion a été effectivement envoyé.

### Gel de l'étape 7 (2026-11-13)

**L'étape 7 est gelée.** Le run `dev` des candidats a eu lieu le 2026-11-12 ([rapport](results/2026-11-12-etape-7-dev.md)). Ce qui est gelé, à ce commit :
- le registre des générateurs et leurs réglages (`exp002_leviers.step7.generators()`) ;
- le barème des prix relevé le 2026-11-12 (`PRICES`) ;
- le lanceur et la règle de choix de l'étape 8.

Rien n'a été réglé sur le `dev`, comme prévu. La seule correction est celle de l'incident d'infrastructure du 2026-11-12, écrite plus haut.

**Générateur de l'étape 8 : Mistral Large 4** (`mistral-large-4-0`, réflexion `low`), par la règle du protocole.
- Les quatre candidats sont éligibles.
- Gemma 4 31B (0,881) et Large 4 (0,873) sont à moins de 2 points l'un de l'autre.
- Le coût de Gemma est inconnu, il passe donc en dernier.

**Verdict** : au run consolidé 2, sur le `test` v5. Les candidats y tournent avec ces réglages gelés.

## Étape 8 — RAG agentique

Les sections Question, Hypothèse, Protocole, Discipline d'itération et Mesures sont écrites le 2026-11-14. C'est après le gel de l'étape 7, qui a retenu Mistral Large 4 comme générateur, et avant toute ligne du serveur MCP.

### Question

Sur le golden set v5, avec Mistral Large 4 comme générateur, laisser le modèle interroger lui-même le corpus par un outil MCP de recherche, autant de fois qu'il le juge utile, change-t-il la part de réponses justes par rapport au RAG à 20 passages ? Et pour quel coût par question, quelle latence et combien d'appels ?

### Hypothèse

- **H1** : un petit gain de `correct`, borné par les échecs de récupération de la baseline. Avec 20 passages, Large 4 ne manque un article attendu que dans 6,7 % des exécutions (`retrieval_miss` au `dev` de l'étape 7) : c'est le plafond de ce que l'agentique peut rattraper par la recherche. La v5 n'a pas de multi-hop. Le coût et la latence augmentent.
- **H0** : aucun écart mesurable de `correct`.
- **Plus petit écart qui compte : 3 points de `correct`**, comme pour 20 passages et le reclassement.

### Protocole

| Élément | Valeur |
|---|---|
| Baseline (A) | `top_k_20` avec `mistral-large-4-0` (réflexion `low`), les réglages gelés de l'étape 7. Sur le `dev`, A est repris du run `dev` de l'étape 7 ; au run consolidé 2, il est rejoué |
| Variante (B) | `agentic_rag` : le même générateur et la même réflexion, avec deux outils MCP servis en stdio par un serveur Python du dépôt. Pas de passages imposés au départ |
| Outils | `consommation_search_articles(query)` rend 5 passages : numéro d'article, chemin dans le code et texte, avec l'index et les caches de `top_k_20`. `consommation_get_article(num)` rend le texte d'un article par son numéro. Les noms suivent `{service}_{action}_{resource}` (référentiel MCP, § 1) |
| Plafond | 6 appels d'outil par question. Au-delà, le serveur répond par une erreur d'exécution (`isError`) qui demande de répondre avec ce qui a été trouvé |
| Contexte noté | la concaténation des articles rendus par tous les appels, dans l'ordre, chaque article gardé à sa première occurrence (spec v2, § 3.2). `tool_calls` est le nombre d'appels. Les métriques à k sont nulles dès 2 appels |
| Ce qui change entre A et B | la façon d'obtenir le contexte, et le prompt qui va avec : consigne d'usage des outils et descriptions des outils |
| Ce qui est fixé | le générateur et ses réglages ; l'index (`mistral-embed`, un passage par article) ; k = 5 par recherche ; le plafond de 6 appels ; la sortie structurée `ModelAnswer` ; la spec `rag-qa/v2` ; le golden set v5 et l'audit |
| Golden set | `rag-qa/v5` : n_dev = 118, n_test = 234 |
| Répétitions | k = 3 |
| Implémentation | `python/` : serveur MCP (SDK MCP officiel, version vérifiée sur PyPI avant d'écrire le serveur), client Pydantic AI en stdio, scorer `ailab_evals.rag_qa_v2` |

**Critère et verdict.**
- **Critère principal : `correct`**, en `higher_better`. Il n'y a qu'une comparaison, donc pas de famille de Holm. Le verdict vient de l'IC du § 8.1 de la spec v2.
- **Publiés sans verdict** : réponses inventées, abstentions à tort, coût par question, latence, `tool_calls` (moyenne et distribution), part des questions au plafond, part des appels à `get_article`, répartition de `failure`.
- **Moment du verdict** : au run consolidé 2 sur le `test` v5, comme pour l'étape 7.

**Conformité MCP** (référentiel [`docs/mcp-bonnes-pratiques.md`](../../docs/mcp-bonnes-pratiques.md)).
- Les entrées sont validées : une requête non vide de 500 caractères au plus, un numéro d'article au format du code.
- Un article inconnu, une requête invalide ou un plafond atteint donnent une erreur d'exécution transmise au modèle, et non une erreur de protocole.
- Un `structuredContent` est accompagné de son JSON en texte.
- `tools/list` est dans un ordre déterministe.
- En stdio, pas d'OAuth : les identifiants viennent de l'environnement.
- La révision de la spec MCP que supporte le SDK Python est vérifiée à la source avant d'écrire le serveur. Tout écart à un MUST ou à un SHOULD est écrit dans les limites.

**Taille de l'échantillon.** Avec s_d = 0,31 à 0,35 (comparaisons du run consolidé) et n = 234, le MDE vaut 5,7 à 6,4 points. Les 3 points qui comptent sont en dessous : un « non concluant » n'exclura pas un petit gain.

**Limites connues avant le run.**
- **Le couple outil et prompt.** Le prompt de B diffère forcément de celui de A, puisqu'il doit expliquer les outils. L'étape juge donc le couple « outils et prompt », pas l'outil seul.
- **Récupération déjà saturée, et pas de multi-hop dans la v5** : le gain possible est faible par construction.
- **Large 4 réfléchit toujours**, au niveau `low`, comme à l'étape 7.

### Discipline d'itération

- **2 cycles sur le `dev`**, autant que la baseline en a reçu. Un cycle, c'est une modification suivie d'un run `dev` complet.
- **Seuls changent le prompt agentique et les descriptions des outils.** Le modèle, l'index, k, le plafond et les outils eux-mêmes sont fixés avant le premier run.
- **Contrôle avant le premier cycle** : un smoke test d'intégration sur 3 items. Il ne compte pas comme un cycle, et ne sert à rien régler.
- **Cycle 1 (2026-11-15)** : consigne écrite avant tout run. Sur le `dev`, `correct` passe de 0,873 à 0,898 (non concluant), les réponses inventées de 0,048 à 0,095, et 16 % des questions touchent le plafond. Les questions sans réponse prennent 5,4 appels en moyenne, contre 2,7 pour les autres.
- **Cycle 2 (2026-11-15)** : la même consigne, plus une règle d'arrêt de la recherche (« Arrête de chercher dès qu'un passage donne la valeur… Si trois recherches reformulées ne la font pas apparaître, ne cherche plus »). Aucune consigne nouvelle sur l'abstention (décision du 2026-11-10).
- **Choix du cycle gelé**, fixé avant le run du cycle 2 : le meilleur `correct` sur le `dev`. À moins d'un point d'écart, c'est le moins cher qui est gelé.
- **Gel** avant le run consolidé 2. Ne pas faire tourner B sur le `test` v5 avant, ni analyser ses échecs item par item.

### Mesures

Ce sont celles de l'étape 7 : `correct`, réponses inventées, abstentions à tort, taux d'erreur, coût par question, latence, tokens de sortie, `correct` par mode, `failure` et `premise`. S'y ajoutent :
- `tool_calls` : moyenne, médiane et distribution ;
- la part des questions qui touchent le plafond ;
- la part des appels à `consommation_get_article`.

Le coût compte tous les appels au modèle de la boucle agentique, sur le barème gelé de l'étape 7.

### Gel de l'étape 8 (2026-11-15)

**L'étape 8 est gelée** après ses deux cycles `dev` ([rapport](results/2026-11-15-etape-8-dev.md)). Ce qui est gelé, à ce commit :
- le serveur MCP (`experiments/002-leviers-rag/mcp_server`) et ses deux outils ;
- le client agentique (`ailab_rag.agentic`) ;
- la consigne du cycle 2 (`exp002_leviers.step8.GUIDANCES[2]`, `FROZEN_CYCLE = 2`) ;
- le lanceur.

**Cycle gelé : le cycle 2**, par la règle écrite avant son run. Son `correct` est le meilleur (0,901 contre 0,898), et c'est le moins cher (0,007978 $ contre 0,007980 $).

**Sur le `dev`** : +2,8 points de `correct` contre `top_k_20` avec Large 4, non concluant. `retrieval_miss` passe de 6,7 % à 1,9 %, et le coût par question est 2,4 fois plus élevé.

**Verdict** : au run consolidé 2, sur le `test` v5.

**Exploration hors protocole (2026-11-15, à la demande du propriétaire).** Le même RAG agentique, gelé au cycle 2, avec Gemini 4 Carbon (réflexion `low`), contre le `top_k_20` de Carbon au run `dev` de l'étape 7. Elle se fait sur le `dev` seulement, sans réglage, et ne change ni la configuration gelée ni le générateur de l'étape. Lancement : `python -m exp002_leviers.step8 --split dev --cycle 2 --generator gemini-4-carbon`.

**Résultat de l'exploration (`dev`, sans verdict)** : `runs/2026-11-15-step8-dev-cycle2-gemini-4-carbon/`.
- **Avec Carbon, l'agentique gagne nettement plus qu'avec Large 4.** `correct` passe de 0,859 à 0,918 : +5,9 points [+0,1 ; +11,8], contre +2,8 non concluant avec Large 4.
- **Le gain vient de la récupération et des abstentions à tort.** `retrieval_miss` passe de 8,9 % à 2,6 %, et les abstentions à tort de 13,7 % à 5,9 %. Les réponses inventées restent à 0.
- **Carbon cherche autrement.** 40 % de ses appels lisent un article entier (`get_article`), contre 5 % pour Large 4, et `multi_article` passe de 0,72 à 0,98.
- **Le coût est bien plus lourd** : 0,027 $ par question au lieu de 0,009 $, et une latence médiane de 21,7 s au lieu de 6,5 s.
- **Ce run a révélé un défaut du lanceur**, corrigé avant toute lecture : l'analyse prenait la baseline de Large 4 au lieu de celle de Carbon. Il a été réanalysé à partir des exécutions enregistrées, sans nouvel appel.
- **Cela ne change pas l'étape gelée.** Son générateur reste Large 4, comme le veut la règle de l'étape 7. Ce résultat dit seulement que le gain de l'agentique dépend du modèle.

## Run consolidé 2 sur le golden set v5

Protocole écrit le 2026-11-15, après le gel des étapes 7 et 8, et avant tout run sur le `test` v5. Les choix sont du propriétaire, le 2026-11-15.

### Question du run

Sur le `test` v5, notés par la spec `rag-qa/v2`, quels leviers des étapes 1 à 8 restent concluants ? Et quel est le tableau final des deltas de la 002, coût et latence compris ?

### Ce qui tourne

| Bloc | Configurations | Générateurs | Comparaisons et verdict |
|---|---|---|---|
| A — étapes 1 à 6 | `closed_book`, `naive_rag`, `query_rewrite`, `top_k_20`, `rerank_cohere`, `abstain_strict`, et `abstain_low_rerank` (calculée sans appel) | `mistral-small-2603`, `ministral-14b-2512`, `gemini-3.5-flash-lite` | Les 6 comparaisons de `correct` du run consolidé 1, en famille de Holm par générateur ; c'est le verdict corrigé qui porte le verdict. Les étapes 5 et 6 ont leur verdict à deux critères (spec v2, § 8.2) |
| B — étape 7 | `top_k_20` avec `mistral-large-4-0`, `gemini-4-carbon`, `gemma-4-31b-it` et `mistral-small-2603` en raisonnement | contre `top_k_20` avec Mistral Small (bloc A) | `correct` et réponses inventées, chacun en famille de Holm de 4 comparaisons (§ 8.3) |
| C — étape 8 | `agentic_rag`, cycle 2 gelé, avec Large 4 | contre `top_k_20` avec Large 4 (bloc B) | `correct`, une seule comparaison, verdict par l'IC (§ 8.1) |
| C' — secondaire, déclarée d'avance | `agentic_rag`, cycle 2, avec Carbon | contre `top_k_20` avec Carbon (bloc B) | `correct`, IC publié. Elle confirme ou non l'exploration du `dev` (étape 8), et ne porte aucun verdict d'étape |

**Fixé** :
- le golden set v5 : n_test = 234 items valides (12 écartés par l'audit de la v1), dont 51 sans réponse ;
- k = 3 répétitions ;
- tous les réglages gelés des étapes : générateurs, réflexion, prompts, consignes, serveur MCP ;
- le barème de l'étape 7, relevé le 2026-11-12 ;
- la spec `rag-qa/v2`.

**Mesures publiées sans verdict** : les agrégats du § 7 pour chaque configuration (coût par question, latence médiane et au 95ᵉ centile, tokens, `tool_calls`, `failure`, `premise`, `correct` par mode).

### Règles

- **Un seul run, avec `--final`**, après le commit de gel, sur un arbre git propre. Pour le bloc A, le contrôle de reproduction passe avant tout appel payant.
- **Aucune analyse item par item du `test` avant le rapport.** Un incident d'infrastructure se relance, sans rien régler : la campagne reprend les exécutions déjà enregistrées.
- **Le `test` v5 est le `test` v4, complété des champs v2** : c'est son troisième regard en agrégat, après le run consolidé 1 et l'étape 6. Aucune configuration n'a été réglée dessus, et c'est une limite écrite.
- **Latence** : toutes les configurations tournent sur la même machine, pendant la même période, et se comparent entre elles. Le réseau des fournisseurs y est compris, et les embeddings de la recherche viennent des caches.
- **Tarif de Carbon** : celui du jour du run. S'il change (le 1ᵉʳ décembre), le rapport cite les deux tarifs.
- **Générateurs du bloc A** : les trois générateurs de la série seulement, pour rester comparable au run consolidé 1 (décision ouverte du plan, tranchée le 2026-11-15).
- **Lecture des « non concluant »** (décidée le 2026-11-15, après le gel et pendant le run, avant le bloc `report` ; écrite ici après lui, parce que le lanceur exige un arbre git propre). Pour chaque comparaison non concluante, le rapport dit si l'IC à 95 % exclut un gain ou une perte de l'écart utile écrit au protocole (borne haute < +δ, borne basse > −δ). On n'écrit « se valent » que si les deux sont exclus. Cette lecture ne change aucun verdict et n'a pas de correction de Holm.

### Taille et MDE

- **`correct`** : avec s_d = 0,31 à 0,35 et n = 234, le MDE vaut 5,7 à 6,4 points, et 6,8 à 7,7 points avec Holm sur 4 ou 6 comparaisons.
- **Réponses inventées** : avec n = 51, le MDE vaut 12 à 19 points.

### Lancement

```
uv run --env-file .env python -m exp002_leviers.consolidated2 --final --block A
uv run --env-file .env python -m exp002_leviers.consolidated2 --final --block B
uv run --env-file .env python -m exp002_leviers.consolidated2 --final --block C
uv run --env-file .env python -m exp002_leviers.consolidated2 --final --block report
```

- **Ordre.** Les blocs A, B et C tournent en parallèle. Le bloc `report` vient ensuite : il réunit les verdicts dans `runs/<date>-consolidated2-test/summary.json`.
- **Coût et durée estimés** : environ 45 $, et 3 à 4 h à cause du quota de Gemma (environ 4 requêtes par minute).

## Limites

- Celles de chaque étape. Les étapes 1 à 4 ont tourné sur la v1, dont 12 questions sans réponse du `test` ont en fait une réponse (audit du 2026-11-09). Leurs métriques d'abstention en sont biaisées en faveur de l'abstention. Le run consolidé écarte ces 12 questions.
- **Configurations non réitérées sur la v4**, comme le veut le protocole : une profondeur ou une consigne réglée sur les modes nouveaux (`comparison`, `set`, `false_premise`) pourrait faire mieux. Sur ces 56 items, `correct` tombe à 0,57–0,74 avec 20 passages.
- **Les modes nouveaux sont petits** (12 à 30 items `test`) et ne se lisent qu'en secondaire. La spec v1 ne vérifie ni le rattachement des valeurs en `comparison`, ni le rejet de la prémisse en `false_premise`.
- **Un seul run final par configuration et par modèle** ; le MDE mesuré (6,0 à 6,8 points pour les leviers de récupération) reste au-dessus des 3 points qui comptent pour 20 passages et pour le reclassement.
- **Sans Langfuse** ; coût non mesuré sur facture (estimation du protocole : 8 à 13 $).
- **Gemini Flash-Lite n'a pas tourné à température 0** (note ajoutée le 2026-11-12). Le protocole fixe `temperature = 0`, et le code l'envoie à chaque générateur. Mais Google documente que, à partir de Gemini 3.5 Flash-Lite, `temperature`, `top_p` et `top_k` sont « deprecated and ignored », et seront refusés (HTTP 400) par les générations suivantes ([nouveautés Gemini 3.6](https://aistudio.google.com/docs/whats-new-gemini-3.6#api-changes-and-parameter-updates), [dépannage](https://aistudio.google.com/docs/troubleshooting), vérifié le 2026-11-12).
  - **Ce que ça touche** : tous les runs `gemini-3.5-flash-lite` de la 002 (étapes 1 à 6, run consolidé, run `dev` de contrôle sur la v5) ont tourné avec la température par défaut du modèle. Leurs rapports, publiés et immuables, écrivent « `temperature = 0` » : cette note les corrige.
  - **Ce que ça change pour la lecture** : les verdicts restent valables, puisque chaque comparaison oppose deux configurations au même réglage. La dispersion entre répétitions de Gemini vient en partie de l'échantillonnage, et pas seulement du modèle.
  - **Pour la suite** : à partir de l'étape 7, `temperature` n'est plus envoyée aux modèles qui l'ignorent, et le rapport dit pour chaque générateur s'il la respecte.
