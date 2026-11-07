# Golden set `rag-qa` du domaine droit-consommation

Des questions posées sur le Code de la consommation, avec leur réponse attendue et les articles qui la justifient. Ce jeu sert à la série d'expériences sur le RAG, à commencer par la 002 (modèle seul ou RAG naïf). Le format d'un item et les règles de notation sont fixés par la spec [`rag-qa/v1`](../../../../evals/spec/rag-qa/v1/SPEC.md).

**Statut : règles de construction, rien n'est encore généré.** Ces règles sont écrites avant le générateur. Une règle qui change après le pilote est signalée ici.

## Principe : construction hybride

Ici, aucun oracle ne peut calculer la réponse à une question sur un texte juridique : il faut la rédiger. Chaque item suit donc cinq étapes.

1. **Tirage seedé des articles.** C'est le script qui choisit les articles, pas le LLM. Laissé libre, un LLM choisirait les articles les plus connus, ce qui gonflerait le score du modèle sans récupération.
2. **Rédaction d'un brouillon par un LLM** : Claude Sonnet 5.5 (`claude-sonnet-5-5`), un fournisseur différent du modèle évalué dans la 002 (Mistral Small). Le prompt du rédacteur est versionné dans le dépôt.
3. **Contrôles automatiques.** Un brouillon qui échoue à un contrôle bloquant est rejeté ; un brouillon qui échoue à un contrôle d'alerte est signalé pour la relecture.
4. **Relecture de tous les items retenus**, assistée par un LLM et arbitrée par le propriétaire (voir « Relecture »).
5. **Gel.** Les réponses du rédacteur sont enregistrées dans `drafts/v1/`, et le générateur les rejoue sans appeler l'API. La sélection et le split se rejouent à l'identique ; la rédaction, elle, ne se rejoue pas. Une nouvelle rédaction donne une nouvelle version.

## Composition

200 items, dont 50 `dev` et 150 `test`, répartis par mode avec un quart en `dev` dans chaque mode.

| Mode | Items (dev + test) | Construction | Contrôle bloquant | Alerte (relecture) |
|---|---|---|---|---|
| `direct` (témoin) | 40 (10 + 30) | question simple sur un article | citation exacte | — |
| `reference` | 30 (8 + 22) | la question cite le numéro de l'article (« l'article L. 221-18 ») | le numéro figure dans la question, sous la forme L. 221-18 ou L221-18 | — |
| `paraphrase` | 40 (10 + 30) | question en langage courant, sans les termes du texte | recouvrement lexical question/article sous le seuil (voir plus bas) | — |
| `multi_article` | 30 (8 + 22) | un article A et un article B que A cite (`cites`) ; la réponse demande un fait de chacun | une citation exacte dans A **et** une dans B | — |
| `lost_context` | 30 (7 + 23) | article dont le texte renvoie à son contexte (« le présent chapitre », « ce délai ») ; la question demande ce que le passage seul ne dit pas | l'article contient une telle expression | toujours relu |
| `unanswerable` | 30 (7 + 23) | question plausible sur le thème d'un article, à laquelle le code ne répond pas | aucun fait attendu | toujours relu, avec les 10 articles les plus proches selon BM25 |

Le verdict d'une expérience porte sur l'ensemble des items. Les scores par mode sont des résultats secondaires : avec 22 à 30 items `test` par mode, ils ont peu de puissance.

Taille de l'échantillon : avec un écart type de la différence par item de 0,4 (hypothèse proche de la 001), 150 items `test` donnent un MDE d'environ 9 points.

## Tirage des articles

- **Articles éligibles** : ni annexe, entre 200 et 4 000 caractères de texte, sans abrogation différée (`valid_to` vide), et pas un tableau (moins de la moitié des lignes contiennent ` | `). Au 2026-11-04, cela fait **1 707 articles** sur 2 150, dont 212 qui conviennent au mode `lost_context` et 1 496 paires A → B possibles pour `multi_article`.
- **Répartition par livre**, proportionnelle au nombre d'articles éligibles de chaque livre, pour ne pas concentrer les questions sur un seul thème.
- **Un article ne sert qu'une fois** dans tout le golden set, même dans une paire. Surtout, aucun article n'apparaît à la fois en `dev` et en `test` : itérer sur le `dev` ne doit rien apprendre du `test`.
- **Surplus.** Le script tire deux fois le besoin de chaque mode et de chaque split, pour absorber les rejets (1,5 fois avant le second pilote, voir plus bas). Les items gardés sont les premiers à passer les contrôles, dans l'ordre du tirage seedé.
- **Les articles des pilotes sont exclus** du tirage de la v1.
- **Extension.** Si la réserve ne suffit pas, on ajoute des tâches à un mode et un split (`--extend mode:split:n`), tirées avec le même seed parmi les articles encore libres, à la suite des rangs existants. Les tâches déjà tirées ne changent jamais ; les tâches ajoutées portent `"extension": true`. En v1, avec les questions de chat, le mode `paraphrase` a perdu 53 brouillons sur 80, dont environ deux tiers déclarés inutilisables : 20 tâches `dev` et 30 tâches `test` ont été ajoutées, et le mode est complet.

## Format d'un item (fixé par la spec [`rag-qa/v1`](../../../../evals/spec/rag-qa/v1/SPEC.md))

```json
{"id": "rq-001", "split": "dev", "mode": "paraphrase", "answerable": true,
 "question": "J'ai acheté un aspirateur en ligne, combien de temps ai-je pour changer d'avis ?",
 "expected": {
   "facts": [{"accepted": ["quatorze jours", "14 jours"]}],
   "articles": [{"id": "LEGIARTI000032226842", "num": "L221-18"}]},
 "evidence": [{"article": "LEGIARTI000032226842", "quote": "dispose d'un délai de quatorze jours"}]}
```

Les identifiants `rq-001` à `rq-200` sont mélangés : ils ne révèlent ni le mode ni l'article.

**Faits attendus.** Une réponse est juste si elle contient chaque fait attendu, sous l'une de ses formes acceptées. La normalisation (casse, accents, espaces, apostrophes) est définie par la spec.
- Une question demande 1 à 3 faits. Un fait est une valeur courte : une durée, un montant, un nombre, un seuil, un acteur, une condition courte.
- **Pas de question fermée (oui / non)** : chercher « non » dans une réponse libre donnerait des faux positifs. On reformule la question pour demander la valeur.
- Les formes acceptées couvrent les variantes d'écriture d'un même fait (« quatorze jours », « 14 jours »). Le rédacteur les propose et la relecture peut en ajouter.

**Articles attendus.** Ce sont tous les articles nécessaires à la réponse (deux pour `multi_article`). Pour `unanswerable`, la liste est vide et l'article de départ est gardé à part, pour l'analyse.

**Citations.** Chaque fait est justifié par un extrait copié mot pour mot de l'article, après normalisation des espaces. C'est un contrôle bloquant : il élimine les réponses que le rédacteur aurait inventées.

## Recouvrement lexical (mode `paraphrase`)

Il se mesure ainsi : la part des mots pleins de la question (au moins 4 lettres, hors mots vides, après normalisation de la casse et des accents) qui apparaissent aussi dans l'article. Il sert aussi de mesure secondaire pour tous les modes, ce qui permet de vérifier que `paraphrase` est bien plus éloigné du texte que `direct`.

**Seuil : 0,40**, fixé après les pilotes. Une question `paraphrase` qui le dépasse est rejetée.

## Pilotes

Avant la v1, trois pilotes de 20 brouillons chacun ont servi à mettre au point le prompt du rédacteur, le seuil de recouvrement et la longueur des questions. Leurs items sont jetés, et leurs articles sont exclus de la v1 (le pilote 3, tiré après le plan v1, exclut aussi les articles de ce plan). Leurs plans et leurs brouillons restent versionnés (`pilot*/`, `drafts/pilot*/`) pour retracer la calibration.

| | Pilote 1 (seed 7) | Pilote 2 (seed 8) | Pilote 3 (seed 9) |
|---|---|---|---|
| Prompt | première version | valeurs plutôt que phrases | questions de chat |
| Mots par question, médiane des modes | non mesuré | non mesuré | 15 à 24 (28 à 39 avec le prompt du pilote 2, mesuré sur la première rédaction de la v1) |
| Formes sans chiffre absentes du texte (reformulations, traduction, coquille) | 15 formes, dans 7 brouillons | 2 formes | non compté |
| Formes de plus de 6 mots | 6 | 2 | non compté |
| Questions portant sur un autre code | 3 | 0 | 0 |
| Brouillons rejetés | 1 sur 20 | 4 sur 20, dont 3 articles déclarés inutilisables | 5 sur 20 |
| Recouvrement lexical : maximum en `paraphrase`, minimum en `direct` | 0,33 / 0,57 | 0,31 / 0,42 | 0,80 (rejeté) puis 0,40 / 0,44 |
| Coût | 0,12 $ | 0,13 $ | 0,14 $ |

**Changements décidés aux pilotes**, tous avant la v1 :
- **Le prompt demande des valeurs, pas des phrases.** Une forme acceptée est la valeur telle qu'écrite dans le texte, ou une variante d'écriture (chiffres ou lettres, unité, sigle), en six mots au plus. Elle n'est jamais une reformulation, une négation ni une traduction. Un seul fait de préférence, deux au plus hors `multi_article`. Aucune question ne porte sur un autre code.
- **Le rédacteur peut déclarer un article inutilisable** (`usable: false`) quand il n'offre aucune valeur précise. Le brouillon est alors rejeté et remplacé par le surplus.
- **Le surplus passe de 1,5 à 2 fois le besoin**, car les rejets ont atteint 20 % au second pilote.
- **Le seuil de recouvrement est fixé à 0,40.**
- **Le contrôle « forme longue » est une alerte, au-delà de 6 mots.**
- **Une forme sans chiffre absente du texte de l'article déclenche une alerte.** C'est le signal le plus fréquent d'une forme reformulée. Une forme avec chiffre est exemptée, car « 14 jours » est une variante légitime de « quatorze jours ».
- **Pilote 3 : des questions de chat.** À la relecture des 10 premiers items de la première rédaction de la v1, les questions étaient justes mais trop longues et trop précises : 28 à 39 mots en médiane selon le mode, loin de ce qu'on tape dans un chat. Elles reprenaient aussi beaucoup de termes de l'article, ce qui rend la récupération artificiellement facile. Le prompt demande désormais une question de 15 mots au plus, avec seulement le contexte nécessaire pour que la réponse soit unique dans le code.
- **Une question de plus de 20 mots est rejetée** (25 en `multi_article`). Le rédacteur dépasse la cible de 15 mots, jusqu'à 20 au pilote 3.
- **Un article sur lequel personne ne poserait de question dans un chat est déclaré inutilisable** : adaptation à l'outre-mer par remplacement de mots, procédure interne à une administration.
- **La rédaction de la v1 a été refaite** avec ce prompt, sur le même plan. La première rédaction reste dans l'historique git (commit `c072abc`). Rien n'avait été publié.

## Relecture

Le générateur produit une page de relecture locale, qui n'est pas versionnée. Pour chaque item, elle montre la question, les faits, les citations surlignées dans l'article et, pour `unanswerable`, les articles les plus proches.

**Comment la relecture a été faite (2026-11-07).** Le propriétaire a fait relire les items par un assistant IA (non nommé), sur la page de relecture. Chaque remarque de l'assistant a été vérifiée sur le texte des articles par Claude, puis tranchée par le propriétaire. Les items que l'assistant a lus sans remarque sont notés `ok` ; le propriétaire a confirmé que tous les items avaient été lus. Ce n'est donc pas une relecture humaine item par item : c'est une limite des expériences qui utilisent ce jeu.

Bilan : `dev` 46 `ok`, 4 corrigés (dont `rq-133`, transformé en item avec réponse), 1 rejeté et remplacé ; `test` 137 `ok`, 13 corrigés. Une part des remarques de l'assistant demandait de retirer des formes absentes du texte (« ANSES », « cinquième classe ») : elles ont été gardées, car la notation cherche le fait dans une réponse libre.

**Tout est relu, en commençant par le `dev`.** La règle prévue était de relire les items signalés par une alerte, plus 20 % des autres tirés au hasard. En v1, le rédacteur exprime un doute sur 148 des 200 items retenus, et 171 items étaient déjà à relire. Relire les 29 restants coûte peu et rend la règle simple. Ce choix ne dépend d'aucun résultat d'expérience. Les 50 items `dev` sont relus d'abord, pour démarrer la 002 ; les 150 items `test` le sont avant le gel des variantes.

**Critères de relecture.** La question se pose comme dans un chat, par quelqu'un qui ne connaît pas le droit : pas de jargon juridique (« mainlevée », « mesures imposées », « attestation ») quand un mot courant suffit, sauf en mode `reference`, où citer un numéro d'article est déjà une démarche de spécialiste. Elle garde juste assez de contexte pour que la réponse soit unique dans le code, et ne donne jamais un détail faux. Les formes acceptées sont des valeurs courtes ; leurs variantes d'écriture (chiffres ou lettres, sigle, unité) sont voulues, car la notation cherche le fait dans une réponse libre, et une réponse plus complète que le fait attendu n'est pas pénalisée.

Le relecteur donne un verdict par item : `ok`, `corrige` (avec la correction) ou `rejete`. Les verdicts sont versionnés dans `review/v1.jsonl`, pour qu'on puisse retracer qui a validé quoi. Un item rejeté est remplacé par le suivant du surplus, qui passe à son tour en relecture.

Relire des items `test` avant le run final ne biaise pas le verdict : aucune variante n'a encore tourné dessus. Après le premier run, la règle du lab s'applique : on n'analyse pas les échecs du `test` item par item avant le run final.

## Limites connues

- **Rédacteur LLM.** Les questions gardent le style de Claude Sonnet 5.5, et des modèles proches de lui pourraient en profiter. Le contrôle de recouvrement ne mesure que le vocabulaire, pas le style.
- **Réponses courtes uniquement.** Aucune question ne demande une interprétation juridique ou une synthèse longue.
- **Renvois incomplets.** Les paires de `multi_article` viennent des liens LEGI, qui ne relient pas toujours chaque article d'une plage (voir la fiche du domaine).
- **Sans réponse.** On ne peut pas prouver que le code ne répond pas à une question. La recherche BM25 et la relecture réduisent ce risque sans l'éliminer.

## Versions

| Version | Données | Seed | Spec | Statut |
|---|---|---|---|---|
| `v1` | `data/v1` | 42 | `rag-qa/v1` | 200 items relus et écrits dans `v1/items.jsonl`, avec `MANIFEST.json` (2026-11-07). Pas encore publiée : elle le sera dès qu'un rapport de la 002 la citera |

**Composition du `dev` après relecture : 6 items sans réponse et 11 en mode `direct`**, au lieu de 7 et 10. `rq-133` (« Garantie de conformité : quel délai a le vendeur pour me rembourser après la résolution du contrat ? ») avait été classé sans réponse, mais L217-17 y répond (« au plus tard dans les quatorze jours ») ; il a été transformé en item avec réponse, en mode `direct`, plutôt que remplacé (décision du 2026-11-07). La correction d'un relecteur peut désormais changer le statut, le mode, les articles et les extraits d'un item, et chaque extrait est vérifié dans son article.

**`items-dev.jsonl` ne vaut pas publication de la v1.** Il sert à itérer sur la 002 dès que le `dev` est relu. Les identifiants sont attribués sur les 200 items retenus, dans l'ordre (mode, split, rang) : remplacer un item `test` à la relecture ne change aucun identifiant du `dev`. La v1 sera publiée, avec `items.jsonl` et son manifeste, une fois les 200 items relus.
