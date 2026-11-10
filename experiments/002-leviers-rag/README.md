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

**Réponse à la question.** Deux leviers font gagner des réponses justes : **le RAG naïf** (+28 à +44 points) et **envoyer plus de bons articles au générateur**, soit par 20 passages (+6 à +10 points), soit par un reclassement des 50 premiers candidats en 5 (+4 à +8 points, à 2,5 fois moins de tokens). Ces deux façons se valent (−1 à −2 points, non concluant). La reformulation de la question ne fait rien gagner. La consigne d'abstention ne fait gagner à aucun modèle et coûte 9 points à Gemini.

**H1 est confirmée, sauf sur un point.** Les étapes 1 à 4 se retrouvent dans le même sens, Mistral Small restant non concluant pour 20 passages comme à l'étape 3. En revanche, la baisse des réponses inventées par la consigne d'abstention avec Mistral Small (−9,2 points à l'étape 5) ne se retrouve pas : −3,3 points, non concluant. Le nouveau delta reste dans l'IC de l'étape 5 (−15,7 à −2,6 points), mais n'exclut plus 0 : sur les mêmes 51 questions, le A de ce run invente moins que celui de l'étape 5 (0,222 contre 0,261), et l'effet de la consigne y est plus faible qu'on ne l'avait mesuré.

**Configuration recommandée sur ce corpus** : 20 passages, ou le reclassement en 5 pour réduire les tokens au prix d'un fournisseur de plus. Pas de consigne d'abstention commune aux modèles.

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

## Limites

- Celles de chaque étape. Les étapes 1 à 4 ont tourné sur la v1, dont 12 questions sans réponse du `test` ont en fait une réponse (audit du 2026-11-09). Leurs métriques d'abstention en sont biaisées en faveur de l'abstention. Le run consolidé écarte ces 12 questions.
- **Configurations non réitérées sur la v4**, comme le veut le protocole : une profondeur ou une consigne réglée sur les modes nouveaux (`comparison`, `set`, `false_premise`) pourrait faire mieux. Sur ces 56 items, `correct` tombe à 0,57–0,74 avec 20 passages.
- **Les modes nouveaux sont petits** (12 à 30 items `test`) et ne se lisent qu'en secondaire. La spec v1 ne vérifie ni le rattachement des valeurs en `comparison`, ni le rejet de la prémisse en `false_premise`.
- **Un seul run final par configuration et par modèle** ; le MDE mesuré (6,0 à 6,8 points pour les leviers de récupération) reste au-dessus des 3 points qui comptent pour 20 passages et pour le reclassement.
- **Sans Langfuse** ; coût non mesuré sur facture (estimation du protocole : 8 à 13 $).
