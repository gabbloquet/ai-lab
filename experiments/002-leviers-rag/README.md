# 002 — Notre RAG répond mal : quels sont les plus gros leviers ?

> **Statut :** conclue le 2026-11-09 — [rapport du run consolidé](results/2026-11-09-run-consolide-test.md)
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

**Recommandation** (2026-11-09, non tranchée par le propriétaire) : pas d'étape sur le type de recherche. Les erreurs qui restent avec 20 passages ne viennent plus surtout de la récupération. Une piste n'est pas couverte, parce qu'elle demande un appel : un autre modèle d'embedding, qui obligerait à encoder les 2 150 articles chez un autre fournisseur.

## Limites

- Celles de chaque étape. Les étapes 1 à 4 ont tourné sur la v1, dont 12 questions sans réponse du `test` ont en fait une réponse (audit du 2026-11-09). Leurs métriques d'abstention en sont biaisées en faveur de l'abstention. Le run consolidé écarte ces 12 questions.
- **Configurations non réitérées sur la v4**, comme le veut le protocole : une profondeur ou une consigne réglée sur les modes nouveaux (`comparison`, `set`, `false_premise`) pourrait faire mieux. Sur ces 56 items, `correct` tombe à 0,57–0,74 avec 20 passages.
- **Les modes nouveaux sont petits** (12 à 30 items `test`) et ne se lisent qu'en secondaire. La spec v1 ne vérifie ni le rattachement des valeurs en `comparison`, ni le rejet de la prémisse en `false_premise`.
- **Un seul run final par configuration et par modèle** ; le MDE mesuré (6,0 à 6,8 points pour les leviers de récupération) reste au-dessus des 3 points qui comptent pour 20 passages et pour le reclassement.
- **Sans Langfuse** ; coût non mesuré sur facture (estimation du protocole : 8 à 13 $).
