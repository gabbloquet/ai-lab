# 004 — Run final sur le split `test` (2026-11-08)

**Question :** sur le Code de la consommation, envoyer au générateur les 20 passages les plus proches au lieu de 5 augmente-t-il le taux de réponses justes (`correct`) d'un RAG naïf, à générateur constant ?

**Réponse :** oui pour deux générateurs sur trois. **B est meilleure** avec Ministral 14B (+7,3 points) et Gemini Flash-Lite (+8,0 points). Avec Mistral Small, le gain est de +4,0 points mais l'intervalle contient 0 : **non concluant**. Pour les trois, le gain vient des questions qui ont une réponse (+6,6 à +10,8 points), où les échecs de récupération sont divisés par deux ou plus. Sur les questions sans réponse, les articles voisins en plus poussent Mistral Small et Gemini Flash-Lite à inventer davantage. Les tokens d'entrée sont multipliés par 3,1.

## Provenance

| Élément | Valeur |
|---|---|
| Commit de gel des variantes | « Geler la 004 avant le run final sur le test » (`b05ab07`), dépôt propre (`--final`), commit relevé au démarrage et enregistré dans chaque `summary.json` (`run.commit`) |
| Golden set | `domains/droit-consommation/golden/rag-qa/v1`, `items.jsonl` sha256 `1df25172a69b336e203896ab60a6bfbff8d2d0e18cc90f86e299a8a34ea5b5c3`, 150 items `test`, les mêmes que les 002 et 003 |
| Données | `domains/droit-consommation/data/v1/articles.jsonl` sha256 `ed9bb9ffd05103792132a35f1fab91c0c3dc07a719c7764ab7269eb85851d9d2` (Code de la consommation, LEGI, état au 13/07/2025) |
| Spec de notation | `evals/spec/rag-qa/v1` |
| Lockfile | `uv.lock` sha256 `2fbe8e4b8044c0fc5257e98d116b362ca947a01cbd0e21ee2700ee9b0b7b9076` |
| Baseline (A) | Le RAG naïf gelé de la 002 : un passage par article, `mistral-embed`, cosinus exact, top-k = 5 |
| Variante (B) | A avec top-k = 20 ; mêmes prompts, même requête, même index |
| Prompts | `rag/python/src/ailab_rag/prompting.py` sha256 `e84ea88df6323ce435e4a4ec477b575eb734fde2b43fe71b5177539951881daf`, identique au `prompting.py` du gel de la 002 (`8d082ad`) à l'import près |
| Campagne | `python/src/exp004_rag/campaign.py` sha256 `fcc5079c29aaf31d5fee9af1c209138f1d7394c5860bcea3ea09789ebb759cf8` |
| Boucle | Pydantic AI 2.65.0, sortie imposée par l'outil de sortie, aucune nouvelle tentative sur une sortie invalide, `temperature = 0` |
| Plan | 150 items `test` × 2 variantes × k = 3, soit 900 exécutions par générateur |
| Runs | `runs/final-test-mistral-small-2603`, `runs/final-test-ministral-14b-2512`, `runs/final-test-gemini-3.5-flash-lite`, le 2026-11-08 entre 13:47 et 13:59 (heure de Paris). Traces dans Langfuse, sessions du même nom, incomplètes (voir Limites) |
| Calcul | `ailab_rag.campaign.summarize` (`summary.json` de chaque run) ; verdict de `ailab_evals.paired.aggregate` |

| Générateur | Identifiant vérifié le 2026-11-08 | Réglages envoyés |
|---|---|---|
| Mistral Small | `mistral:mistral-small-2603` (API Mistral, `/v1/models`) | `temperature = 0` |
| Ministral 14B | `mistral:ministral-14b-2512` (API Mistral, `/v1/models`) | `temperature = 0` |
| Gemini Flash-Lite | `google:gemini-3.5-flash-lite` (API Google, `v1beta/models`) | `temperature = 0` |

## Verdict par générateur

La règle a été fixée avant le run : B est meilleure si la borne basse de l'IC à 95 % du delta apparié de `correct` est au-dessus de 0, pire si la borne haute est en dessous, non concluant sinon. Plus petit écart qui compte : 3 points.

| Générateur | `correct` A | `correct` B | Delta B − A | IC 95 % | Verdict |
|---|---|---|---|---|---|
| `mistral-small-2603` | 0,798 | 0,838 | **+0,040** | [−0,016 ; +0,096] | **non concluant** |
| `ministral-14b-2512` | 0,767 | 0,840 | **+0,073** | [+0,019 ; +0,128] | **B meilleure** |
| `gemini-3.5-flash-lite` | 0,784 | 0,864 | **+0,080** | [+0,030 ; +0,130] | **B meilleure** |

Aucune erreur d'exécution ni sortie illisible sur les 2 700 exécutions.

**Lecture du seuil de 3 points.** Pour Gemini Flash-Lite, la borne basse est à 3 points (+0,0299) : le gain est réel et vaut, à la marge près, l'écart qui compte. Pour Ministral 14B, le gain est réel mais sa borne basse (+1,9 points) reste sous 3 points : il peut être plus petit que l'écart qui compte. Pour Mistral Small, l'intervalle va de −1,6 à +9,6 points : on ne peut ni affirmer un gain ni l'exclure.

**A reproduit les 002 et 003.** Même RAG naïf, même `test` : 0,798 (0,791 dans les 002 et 003) pour Mistral Small, 0,767 (0,762 ; 0,767) pour Ministral 14B, 0,784 (0,787 ; 0,791) pour Gemini Flash-Lite. Les écarts, au plus 0,7 point, viennent de l'indéterminisme résiduel des API à température 0.

## Métriques secondaires

Elles ne portent pas le verdict. Les tokens se comparent entre variantes d'un même générateur, jamais d'un fournisseur à l'autre.

| Métrique | Mistral Small A | B | Ministral 14B A | B | Gemini Flash-Lite A | B |
|---|---|---|---|---|---|---|
| `correct`, items avec réponse | 0,832 | 0,898 | 0,806 | 0,885 | 0,753 | 0,861 |
| `retrieval_miss` | 0,142 | 0,063 | 0,171 | 0,063 | 0,210 | 0,094 |
| `generation_miss` | 0,026 | 0,039 | 0,024 | 0,052 | 0,037 | 0,045 |
| `hallucination` (items sans réponse) | 0,391 | **0,493** | 0,449 | 0,406 | 0,043 | **0,116** |
| `false_abstention` | 0,037 | 0,008 | 0,052 | 0,021 | 0,199 | 0,089 |
| Citations, précision / rappel | 0,72 / 0,77 | 0,79 / 0,90 | 0,72 / 0,79 | 0,77 / 0,88 | 0,83 / 0,74 | 0,88 / 0,87 |
| Tokens du générateur par exécution | 1 281 | 3 961 | 1 292 | 3 974 | 1 338 | 4 107 |

**Delta par type d'item :**

| Générateur | Items avec réponse (127) | Items sans réponse (23) |
|---|---|---|
| `mistral-small-2603` | +0,066 | −0,101 |
| `ministral-14b-2512` | +0,079 | +0,043 |
| `gemini-3.5-flash-lite` | +0,108 | −0,072 |

**Récupération**, identique pour les trois générateurs (items avec réponse) : rappel au top-5 0,81 pour les deux variantes, au top-10 0,81 → 0,86 ; tous les articles attendus dans les 10 premiers passages, 0,76 → 0,81. La spec ne mesure pas le rappel au-delà du top-10 ; la baisse de `retrieval_miss` (de 0,14-0,21 à 0,06-0,09) montre que les passages 11 à 20 en apportent encore.

**`correct` par mode, A → B :**

| Mode | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| `direct` (30) | 0,90 → 0,96 | 0,87 → 0,88 | 0,83 → 0,89 |
| `reference` (22) | 0,88 → 0,95 | 0,82 → 1,00 | 0,77 → 0,91 |
| `paraphrase` (30) | 0,86 → 0,93 | 0,88 → 0,84 | 0,80 → 0,90 |
| `multi_article` (22) | 0,53 → 0,61 | 0,45 → 0,71 | 0,38 → 0,58 |
| `lost_context` (23) | 0,96 → 1,00 | 0,96 → 1,00 | 0,93 → 1,00 |
| `unanswerable` (23) | 0,61 → 0,51 | 0,55 → 0,59 | 0,96 → 0,88 |

Chaque mode compte 22 à 30 items : un écart de 5 points y représente un ou deux items.

## Lecture

- **Le levier marche là où la 003 échouait.** La reformulation changeait l'ordre des passages sans en ajouter ; 20 passages font entrer les articles classés de la 6e à la 20e place. Les échecs de récupération baissent de moitié ou plus, pour tous les générateurs.
- **Les questions sur plusieurs articles gagnent le plus** (+8 à +26 points) : il suffit qu'un article manquant soit dans le top-20 pour que la réponse devienne complète. Le mode reste pourtant le plus faible (0,58 à 0,71).
- **Le prix se paie sur les questions sans réponse.** Avec 20 passages, le modèle trouve plus souvent un article voisin qui ressemble à une réponse. Chez Mistral Small, cinq items sans réponse sur 23 se dégradent : à « quelle police de caractères pour le formulaire de rétractation ? », B répond avec la taille minimale des caractères (corps 12) d'une annexe voisine ; à « quels honoraires pour le liquidateur ? », il cite un tarif général. Gemini Flash-Lite, qui s'abstient presque toujours, invente un peu plus (0,04 → 0,12). Ministral 14B n'invente pas davantage.
- **Le bilan dépend de ce rapport.** Mistral Small gagne +6,6 points sur les questions avec réponse et en perd 10 sur les questions sans réponse : son gain total (+4,0) n'est pas assez net pour conclure. Ministral 14B gagne des deux côtés.
- **Les erreurs de génération montent un peu** (+0,8 à +2,8 points) : avec l'article attendu présent dans 20 passages, le modèle se trompe ou s'abstient un peu plus souvent qu'avec 5. C'est faible devant la baisse des échecs de récupération.
- **Coût :** environ 2 700 tokens d'entrée de plus par question, sans appel supplémentaire.

## Écarts par rapport au `dev`

Au run 0 du `dev` (Mistral Small), B gagnait +0,10 [−0,002 ; +0,20], avec une baisse des réponses inventées (0,33 → 0,28). Sur le `test`, Mistral Small gagne +0,04 et ses réponses inventées montent (0,39 → 0,49). Le `dev` compte 6 items sans réponse, le `test` 23 : la hausse des réponses inventées ne pouvait pas se voir sur le `dev`. C'est le risque que la décision de geler sans cycle a pris (voir Limites).

## Dispersion

| Générateur | s_d | Couples item × variante instables sur 3 répétitions | Items où B > A / B < A |
|---|---|---|---|
| `mistral-small-2603` | 0,347 | 8 / 300 | 14 / 10 |
| `ministral-14b-2512` | 0,336 | 7 / 300 | 16 / 6 |
| `gemini-3.5-flash-lite` | 0,311 | 13 / 300 | 19 / 6 |

Avec s_d ≈ 0,33, le MDE sur 150 items est d'environ 7,6 points, comme prévu au protocole. Les deux gains concluants (+7,3 et +8,0) sont à ce niveau ; celui de Mistral Small (+4,0) est en dessous.

## Limites

- **Traces Langfuse incomplètes.** Le serveur Langfuse auto-hébergé n'a pas reçu toutes les traces et tous les scores dans les 120 s laissées après chaque run (`run.langfuse_flushed: false` dans les trois résumés). Les résumés ont été écrits avant l'envoi, et les processus sont sortis normalement : les `executions.jsonl` et les `summary.json` font foi.
- **B moins travaillée que A.** A a reçu deux cycles de mise au point dans la 002, B aucun : la 004 a été gelée au run 0 du `dev`, faute de hausse des réponses inventées sur ses 6 items sans réponse. Sur le `test`, cette hausse apparaît pour Mistral Small. Un cycle sur la consigne d'abstention aurait pu la réduire ; l'écart joue contre B.
- **La spec ne mesure pas le rappel au-delà du top-10** (`KS = (1, 3, 5, 10)`) : l'apport des passages 11 à 20 ne se lit qu'à travers `retrieval_miss`.
- **Profondeur choisie sur le `dev`**, parmi six valeurs : k = 20 n'est pas forcément la meilleure profondeur, et 10 ou 15 n'ont pas été testés sur la génération.
- **Les limites de la 002 s'appliquent** : un seul corpus, questions rédigées par un LLM, golden set relu avec l'aide d'un LLM.
