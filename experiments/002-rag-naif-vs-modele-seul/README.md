# 002 — RAG naïf ou modèle seul ?

> **Statut :** cadrage
> **Domaines :** [`droit-consommation`](../../domains/droit-consommation/README.md)
> **Spec de notation :** [`rag-qa/v1`](../../evals/spec/rag-qa/v1/SPEC.md) (brouillon)

Première expérience de la série sur le RAG : « notre RAG répond mal, quels sont les plus gros leviers ? ». La 002 pose la baseline de toute la série, le RAG naïf, et mesure ce qu'il apporte par rapport au modèle seul. Les expériences suivantes testeront chacune un levier contre cette même baseline.

Les sections Question, Hypothèse, Protocole, Discipline d'itération et Mesures sont écrites avant le premier run.

## Question

Sur le Code de la consommation, de combien un **RAG naïf** augmente-t-il le taux de réponses justes (`correct`, spec `rag-qa/v1`) par rapport au **même modèle sans récupération** ?

## Hypothèse

- **H1 :** le RAG naïf (B) répond juste plus souvent que le modèle seul (A).
- **H0 :** pas de différence mesurable entre A et B.
- **Plus petit écart qui compte en pratique : 10 points de `correct`.** En dessous, un RAG ne justifierait pas son coût d'exploitation.

**Ce que la 002 doit aussi dire, sans que cela porte le verdict :**
- **Ce que le modèle sait déjà du code.** Le score de A mesure la part des questions auxquelles le modèle répond de mémoire. Un score élevé signalerait que le golden set est contaminé par l'entraînement du modèle.
- **Où le RAG naïf échoue.** La répartition de `failure` en B (`retrieval_miss` ou `generation_miss`) dit s'il faut d'abord travailler la récupération ou la génération.
- **Sur quels modes il échoue.** Les scores par mode désignent les premiers leviers à tester dans la série.

## Protocole

| Élément | Valeur |
|---|---|
| Baseline (A) | **Modèle seul** : la question, sans aucun passage du code |
| Variante (B) | **RAG naïf** : la question, suivie des 5 articles les plus proches selon les embeddings |
| Ce qui change entre A et B | La présence du contexte récupéré, et la phrase d'ancrage qui l'introduit (précisée au cycle 2 de B). Une phrase propre à A, essayée à son cycle 2, a été retirée faute de gain |
| Ce qui est fixé | Le modèle, le prompt système hors contexte, le format de sortie, la température (0), les données (`domains/droit-consommation/data/v1`) |
| Modèles | Un verdict par modèle : `mistral:mistral-small-2603` et `google:gemini-3.5-flash-lite`, les mêmes que dans la 001, et `mistral:mistral-medium-2604`, ajouté le 2026-11-07 après le run 0 du `dev` et avant tout run `test`, pour voir si l'apport du RAG baisse quand le modèle grandit. Aucun ne vient du fournisseur du rédacteur du golden set (Claude Sonnet 5.5). Identifiants vérifiés le 2026-11-07 sur les API Mistral (`/v1/models`) et Google (`v1beta/models`). |
| Golden set | `domains/droit-consommation/golden/rag-qa/v1` : 200 items, **n_dev = 50, n_test = 150**, en six modes (direct, référence, paraphrase, plusieurs articles, contexte perdu, sans réponse). [Règles du golden set](../../domains/droit-consommation/golden/rag-qa/README.md) |
| Répétitions | k = 3 |
| Implémentation | `python/` uniquement : la boucle de question-réponse (Pydantic AI), l'index et la notation (métrique DeepEval conforme à la spec) |

### Le RAG naïf

« Naïf » veut dire ce qu'on obtient en suivant un tutoriel standard, sans optimisation. Chaque choix laissé simple ici est un levier que la série pourra tester.

| Étape | Choix | Levier que la série pourra tester |
|---|---|---|
| Découpage | **Un passage par article** du corpus. Un article de plus de 12 000 caractères est coupé en morceaux qui gardent l'`id` de l'article, sur un saut de ligne quand c'est possible. Ce seuil garde chaque passage sous les 8 192 tokens de `mistral-embed`, même à 3 caractères par token, faute de tokenizer Mistral pour compter exactement. Il ne touche que 3 annexes, qui ne sont la réponse d'aucun item : 2 150 articles donnent 2 155 passages. | Découpage à taille fixe ; découpage plus fin des articles longs |
| Texte indexé | Le texte de l'article seul : ni numéro, ni titre du plan, ni `nota` | En-tête « Article L221-18 » et plan dans le texte indexé ; contextualisation des passages |
| Embeddings | `mistral-embed` (1 024 dimensions, 8 192 tokens d'entrée, lus sur l'API `/v1/models` le 2026-11-05), le même pour les deux modèles générateurs | Autre modèle d'embedding |
| Recherche | Similarité cosinus exacte en mémoire (numpy), sur la question telle quelle | Recherche hybride (BM25 et dense), réécriture de requête, reranking |
| Contexte | Les **5** passages les plus proches (top-k = 5), chacun précédé du numéro de son article (« Article L221-18 ») pour que le modèle puisse le citer. On envoie le passage récupéré tel quel : il est identique à l'article pour 2 147 articles sur 2 150, et seules les 3 annexes coupées en diffèrent. Deux morceaux d'une même annexe peuvent occuper deux places du top-5. | Taille du contexte, filtrage par métadonnées ; « récupérer petit, envoyer grand » (*parent document retrieval*) : chercher dans des morceaux fins, envoyer l'article qui les contient, à tester avec un découpage à taille fixe |

Le numéro de l'article est montré au modèle mais n'est pas indexé : une question qui cite un numéro (mode `reference`) ne profite donc pas du numéro pour la recherche. C'est voulu : le mode `reference` mesure ce manque.

**Conséquence du découpage par article :** le levier « découpage par structure » fait déjà partie de la baseline. La série testera l'inverse, un découpage à taille fixe, qui pourrait faire perdre des points.

### Format de sortie

Le modèle répond en JSON, avec la même consigne en A et en B : `{"answer": str, "abstained": bool, "cited": [str]}`, un numéro d'article par élément de `cited` (spec § 3.2). Les deux variantes ont le droit de s'abstenir quand elles ne savent pas : sans ce droit, A serait poussé à inventer. Une sortie illisible compte comme une erreur d'exécution, donc comme une réponse fausse (spec § 6), et son taux est publié par variante.

**Taille de l'échantillon.** MDE = (t₀,₉₇₅ + t₀,₈₀) × s_d / √n_test. Hypothèse : s_d = 0,4, proche de la 001 (0,373 au run 0). Avec n_test = 150 : MDE ≈ (1,976 + 0,844) × 0,4 / √150 ≈ **9,2 points**, sous les 10 points qui comptent.

**Lancer un run :** commande à écrire avec l'implémentation.

## Discipline d'itération

1. **Même effort pour chaque variante.** Seul le prompt est mis au point. La recette du RAG naïf est figée par le tableau ci-dessus.
2. **Gel avant le run final.** Les deux variantes sont figées par un commit, et plus rien ne change ensuite.
3. **Un seul run sur le `test`.**

**Budget d'itération :** N = 3 cycles par variante, sur le `dev` uniquement, avec un seul modèle (`mistral-small-2603`).

**Journal d'itération**, sur le `dev` uniquement :

| # | Date | Variante | Modification | Motif | `correct` dev |
|---|---|---|---|---|---|
| 0 | 2026-11-07 | A et B | aucune : mesure de départ, hors budget | point de départ des cycles | A 0,30 · B 0,69 (Mistral Small, k = 3, `dev` corrigé) |
| 1 | 2026-11-07 | A et B (prompt système commun) | Consigne d'abstention : « Si le Code de la consommation ne fixe pas la valeur demandée, ou si tu ne la connais pas avec certitude, mets `abstained` à vrai. Dès que ta réponse revient à dire que le code ne prévoit rien ou ne précise pas cette valeur, `abstained` doit être vrai. » (commit `9e537b3`) | Au run 0, le modèle écrivait « le code ne prévoit pas » en laissant `abstained` à faux : 83 à 94 % d'hallucinations sur les items sans réponse | A 0,41 · B 0,71. Hallucination A 0,94 → 0,22, B 0,83 → 0,33 ; fausse abstention A 0,00 → 0,17, B 0,13 → 0,20 ; B sur les items avec réponse 0,77 → 0,71 |
| 2 | 2026-11-07 | B seulement (phrase d'ancrage) ; A n'utilise pas ce cycle et garde ses exécutions du cycle 1 | « Si un extrait contient la valeur demandée, réponds, même si sa formulation diffère de celle de la question. » (commit du cycle 2) | Au cycle 1, B s'abstenait sur des réponses présentes dans le contexte : paraphrase 0,73 → 0,60, fausse abstention 0,20 | A 0,41 · B 0,75. B sur les items avec réponse 0,71 → 0,77, paraphrase 0,60 → 0,73, fausse abstention 0,20 → 0,14, hallucination 0,33 → 0,39 |
| 3 | 2026-11-07 | A seulement (phrase propre à A) : cycle 2 de A ; B garde ses exécutions de son cycle 2 | « Réponds avec tes connaissances du Code de la consommation. Si tu connais la valeur demandée, donne-la, même si tu n'es pas sûr du numéro de l'article. » (commit `6204e5b`) | Équilibrer le budget (B avait reçu deux cycles) ; au cycle 1, A s'abstenait sur 17 % des items avec réponse | A 0,39 · B 0,75. Fausse abstention A 0,17 → 0,08, hallucination A 0,22 → 0,33, A sur les items avec réponse 0,36 → 0,35 : pas de gain |
| 4 | | | | | |

**Commit de gel :** à venir
**Run final sur le `test` :** à venir

## Mesures

- **Métrique principale, qui porte le verdict :** `correct`, telle que définie dans la spec `rag-qa/v1` (§ 5).
- **Métriques secondaires, publiées sans porter le verdict :**
  - `correct` restreint aux items avec réponse, `false_abstention`, `hallucination` ;
  - le taux d'erreur, dont les sorties illisibles ;
  - pour B seulement : `evidence_recall@k` et `all_evidence@k` (k ∈ {1, 3, 5}) et la répartition de `failure` ;
  - `correct` par mode, pour A et pour B ;
  - les citations (`citation_precision`, `citation_recall`) ;
  - les tokens, comparés seulement à modèle constant.
- **Règle de verdict :** celle de la spec (§ 8).

## Résultats

À venir : seul le run final sur le `test` portera le verdict.

### Résultats `dev` (hors verdict)

**Runs 0, 2026-11-07, par modèle** : 50 items `dev`, k = 3, 300 exécutions par modèle, aucune erreur ni sortie illisible. Golden set : `v1/items-dev.jsonl`, relu. Les chiffres sont ceux du `dev` corrigé : `rq-133`, d'abord classé sans réponse, a une réponse dans le code (L217-17) et a été transformé en item avec réponse ; sa question n'a pas changé, les exécutions ont été renotées sans nouvel appel.

| Modèle | A `correct` | B `correct` | Delta B − A [IC 95 %] | A, avec réponse | B `retrieval_miss` / `generation_miss` | B `hallucination` | B `false_abstention` |
|---|---|---|---|---|---|---|---|
| `mistral-small-2603` | 0,30 | 0,69 | +0,39 [+0,24 ; +0,54] | 0,33 | 0,21 / 0,02 | 0,83 | 0,13 |
| `mistral-medium-2604` | 0,31 | 0,72 | +0,41 [+0,24 ; +0,57] | 0,36 | 0,25 / 0,00 | 0,50 | 0,19 |
| `gemini-3.5-flash-lite` | 0,48 | 0,70 | +0,22 [+0,04 ; +0,40] | 0,52 | 0,30 / 0,02 | 0,17 | 0,27 |

- **Gemini Flash-Lite connaît bien mieux le code** (52 % de bonnes réponses de mémoire sur les items avec réponse) : l'apport du RAG est deux fois plus faible. En paraphrase, B fait moins bien que A (0,40 contre 0,50) : quand la récupération rate, la consigne d'ancrage le fait s'abstenir là où sa mémoire suffisait.
- **Mistral Medium ne sait pas plus de choses que Mistral Small** sans contexte (0,31 contre 0,30), mais il invente moins en B (0,50 contre 0,83).
- **Pour les trois modèles, la récupération est le goulot** : 21 à 30 % de `retrieval_miss`, 0 à 2 % de `generation_miss`.

**Run exploratoire, hors protocole et sans verdict** : `gemini-3.8-flash` (Gemini 3.8 Flash, un modèle qui raisonne, d'un palier au-dessus des trois autres), mêmes conditions, 2026-11-07.

| Métrique | A, modèle seul | B, RAG naïf |
|---|---|---|
| `correct`, tous items | 0,65 | 0,69 |
| `correct`, items avec réponse | 0,71 | 0,67 |
| `hallucination` (items sans réponse) | 0,83 | 0,17 |
| `false_abstention` | 0,00 | 0,30 |
| `correct` en `paraphrase` | 0,77 | 0,43 |
| Tokens par exécution | 3 192 | 1 675 |

Delta B − A : +0,05, IC 95 % [−0,13 ; +0,23]. Ce modèle répond juste de mémoire à 71 % des questions qui ont une réponse : le RAG naïf ancré ne l'aide plus sur ces questions et le pénalise en paraphrase, où une récupération ratée (30 % de `retrieval_miss`) le fait s'abstenir. Il réduit en revanche fortement les réponses inventées aux questions sans réponse. Pour la série, la consigne d'ancrage devient un levier à tester : laisser le modèle compléter avec ses connaissances.

**Runs exploratoires sur de plus petits modèles, hors protocole et sans verdict** : la gamme Ministral de Mistral, mêmes conditions, 2026-11-07.

| Modèle | A `correct` | B `correct` | Delta B − A [IC 95 %] | B `retrieval_miss` / `generation_miss` | B `hallucination` | Erreurs |
|---|---|---|---|---|---|---|
| `ministral-3b-2512` | 0,17 | 0,63 | +0,47 [+0,30 ; +0,63] | 0,26 / 0,05 | 0,78 | 1 % |
| `ministral-8b-2512` | 0,25 | 0,67 | +0,43 [+0,27 ; +0,58] | 0,24 / 0,02 | 0,78 | 0 % |
| `ministral-14b-2512` | 0,29 | 0,69 | +0,39 [+0,23 ; +0,55] | 0,27 / 0,04 | 0,33 | 0 % |

Plus le modèle est petit, moins il sait de mémoire et plus le RAG naïf lui apporte. Avec le contexte, tous atteignent 0,63 à 0,72 : la récupération plafonne le score, quel que soit le modèle.

Détail pour Mistral Small :

| Métrique | A, modèle seul | B, RAG naïf |
|---|---|---|
| `correct`, tous items | 0,30 | 0,69 |
| `correct`, items avec réponse | 0,33 | 0,77 |
| `hallucination` (items sans réponse) | 0,94 | 0,83 |
| `false_abstention` | 0,00 | 0,13 |
| Citations, précision / rappel | 0,21 / 0,20 | 0,73 / 0,67 |
| Tokens par exécution | 321 | 1 219 |

Delta B − A : +0,39, IC 95 % [+0,24 ; +0,54] sur 50 items `dev`.

- **Ce que le modèle sait déjà.** Mistral Small répond juste de mémoire à 33 % des questions qui ont une réponse.
- **Où le RAG naïf échoue.** Sur les items avec réponse, B se trompe à 21 % par `retrieval_miss` (l'article attendu manquait au contexte) et à 2 % par `generation_miss`. L'article attendu est au rang 1 dans 47 % des cas, dans le top-5 dans 72 %.
- **Par mode, en B.** `direct` 0,90 · `reference` 0,83 · `lost_context` 0,81 · `paraphrase` 0,73 · `multi_article` 0,50 · `unanswerable` 0,14.
- **Stabilité.** 10 couples item × variante sur 100 changent de résultat d'une répétition à l'autre, malgré la température 0.

## Verdict

À venir.

## Limites

À compléter. Déjà connues :
- **Un seul corpus**, en français, dans un seul domaine du droit, dans son état au 13 juillet 2025.
- **Questions rédigées par un LLM** (Claude Sonnet 5.5), puis relues : leur style peut différer de celui de vrais utilisateurs.
- **Réponses courtes uniquement** : aucune question ne demande d'interprétation ni de synthèse longue.
- **Itération sur un seul modèle** : les prompts sont mis au point avec Mistral Small, ce qui peut avantager ce modèle au run final.
- **Puissance** : au run 0 (`dev`, Mistral Small), s_d = 0,529, au-dessus des 0,4 supposés. Le MDE sur 150 items `test` passe d'environ 9,2 à environ 12,2 points, au-dessus des 10 points qui comptent. Sans conséquence pour la 002, dont l'écart attendu est bien plus grand ; à recalculer pour les expériences de la série, qui compareront deux RAG plus corrélés.
- **Langfuse** : au run 0, le serveur local a coupé plusieurs envois et des scores ont été perdus dans Langfuse. Les fichiers `executions.jsonl` font foi.
