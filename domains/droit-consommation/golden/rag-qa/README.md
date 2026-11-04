# Golden set `rag-qa` du domaine droit-consommation

Des questions posées sur le Code de la consommation, avec leur réponse attendue et les articles qui la justifient. Ce jeu sert à la série d'expériences sur le RAG, à commencer par la 002 (modèle seul ou RAG naïf). Le format d'un item et les règles de notation sont fixés par la spec [`rag-qa/v1`](../../../../evals/spec/rag-qa/v1/SPEC.md).

**Statut : règles de construction, rien n'est encore généré.** Ces règles sont écrites avant le générateur. Une règle qui change après le pilote est signalée ici.

## Principe : construction hybride

Ici, aucun oracle ne peut calculer la réponse à une question sur un texte juridique : il faut la rédiger. Chaque item suit donc cinq étapes.

1. **Tirage seedé des articles.** C'est le script qui choisit les articles, pas le LLM. Laissé libre, un LLM choisirait les articles les plus connus, ce qui gonflerait le score du modèle sans récupération.
2. **Rédaction d'un brouillon par un LLM** : Claude Sonnet 5.5 (`claude-sonnet-5-5`), un fournisseur différent du modèle évalué dans la 002 (Mistral Small). Le prompt du rédacteur est versionné dans le dépôt.
3. **Contrôles automatiques.** Un brouillon qui échoue à un contrôle bloquant est rejeté ; un brouillon qui échoue à un contrôle d'alerte est signalé pour la relecture.
4. **Relecture humaine** de tous les items signalés, plus 20 % des autres tirés au hasard.
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
- **Surplus.** Le script tire environ 1,5 fois le besoin de chaque mode, pour absorber les rejets. Les items gardés sont les premiers à passer les contrôles, dans l'ordre du tirage seedé.

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

Il se mesure ainsi : la part des mots pleins de la question (au moins 4 lettres, hors mots vides, après normalisation de la casse et des accents) qui apparaissent aussi dans l'article. Le seuil est fixé au pilote, puis écrit ici, avant la génération de la v1. Il sert aussi de mesure secondaire pour tous les modes, ce qui permet de vérifier que `paraphrase` est bien plus éloigné du texte que `direct`.

## Pilote

Avant la v1, un pilote de 20 brouillons, tirés hors des articles de la v1, sert à mettre au point le prompt du rédacteur et le seuil de recouvrement. Ses items sont jetés. Tout changement de règle décidé au pilote est noté dans cette fiche.

## Relecture

Le générateur produit une page de relecture locale, qui n'est pas versionnée. Pour chaque item, elle montre la question, les faits, les citations surlignées dans l'article et, pour `unanswerable`, les articles les plus proches.

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
| `v1` | `data/v1` | à fixer | `rag-qa/v1` | règles écrites, à générer |
