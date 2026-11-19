# 003 — Plan

> **Mis à jour le 2026-11-19.** Ce plan n'est pas un protocole. Il donne les objectifs des trois étapes et l'ordre des chantiers. Chaque étape écrit son protocole dans le [README](README.md) avant ses résultats.

## Le besoin

Beaucoup de décisions métier sont écrites dans un texte : une loi, un règlement, des conditions générales. Quand on met un LLM dans ce genre de système, on peut lui donner trois rôles différents : décider, lire le cas, ou écrire les règles. Le choix se fait souvent à l'intuition.

La 003 mesure ces trois rôles sur une même décision : « à la date D, le consommateur peut-il encore se rétracter ? » (Code de la consommation, L221-18 à L221-28).

## Les trois étapes

### Étape 1 — Qui décide ?

- **Objectif :** savoir si on gagne à retirer la décision au LLM.
- **Comparaison :** le LLM seul, avec les articles sous les yeux, contre un LLM qui extrait les faits du cas, suivi de règles écrites à la main qui décident.
- **Ce qu'on saura :** combien de décisions justes on gagne ou on perd, sur quelles issues (exclusions, calcul du délai), et à quel coût.
- **Ce qu'on ne saura pas :** si les règles sont justes. Elles servent d'oracle : cette étape ne mesure que la lecture du cas.

### Étape 2 — Comment appeler les règles ?

- **Objectif :** savoir ce que coûte de laisser le LLM piloter les règles, plutôt que de les enchaîner dans le code.
- **Comparaison :** l'enchaînement fixe de l'étape 1 (extraction, puis règles), contre les mêmes règles exposées en outil MCP, que le LLM choisit d'appeler.
- **Ce qu'on saura :** si le LLM appelle l'outil quand il le faut, s'il lui passe les bons faits, et ce que l'on perd par rapport à l'enchaînement fixe.
- **Ce qu'on ne saura pas :** si un outil MCP vaut mieux pour une tâche plus large, où la décision n'est qu'une étape parmi d'autres. Ici, la tâche se réduit à la décision.

### Étape 3 — Qui écrit les règles ?

- **Objectif :** savoir si le LLM peut écrire les règles une fois, plutôt que décider à chaque appel.
- **Comparaison :** les règles écrites à la main de l'étape 1, contre une table de décision écrite par le LLM à partir des articles, gelée, puis exécutée sans LLM.
- **Ce qu'on saura :** combien de décisions on perd avec une table écrite par le LLM, et sur quelles règles elle se trompe. C'est la seule étape qui met le contenu des règles à l'épreuve.
- **Ce qu'on ne saura pas :** le temps gagné à ne pas écrire les règles à la main. Il n'est pas mesuré.

## Ce que les trois étapes partagent

- **La décision et sa sortie :** `oui`, `non : hors champ`, `non : exclusion`, `non : délai expiré`, et la date limite.
- **Le schéma des faits :** fixé avant l'étape 1. Il sépare la lecture du cas (le LLM) de la décision (les règles).
- **Les règles écrites à la main :** variante de l'étape 1, baseline des étapes 2 et 3, et oracle du golden set.
- **Le golden set :** des cas synthétiques, tirés par un script seedé, rédigés en langage naturel, puis relus.
- **La spec de notation :** une nouvelle famille, avec ses vecteurs de conformance.

## Décisions du propriétaire (2026-11-19)

- Les trois leviers forment une seule expérience, découpée en étapes. Les étapes 2 et 3 se jugent contre la variante de l'étape 1.
- Le périmètre est le droit de rétractation, et non tout le Code de la consommation.
- Le schéma décrit des faits élémentaires, que les règles combinent. Il n'a pas de champ « motif d'exclusion » que le LLM remplirait.
- L221-2 (contrats exclus du chapitre) et L221-3 (extension à certains professionnels) restent hors périmètre : on suppose un consommateur et un contrat que L221-2 n'exclut pas. C'est une limite écrite.
- Le contrat signé en magasin juste après un démarchage ailleurs (L221-1, 2° b) est dans le périmètre : c'est un contrat hors établissement.
- L'exclusion 8° de L221-28 (réparation urgente) sort du générateur : elle ne vaut que dans la limite des pièces et travaux strictement nécessaires, et son issue partielle n'entre pas dans les quatre sorties.

## Feuille de route

| # | Chantier | Qui écrit |
|---|---|---|
| 1 | Schéma des faits, champ par champ, avec l'article qui justifie chaque fait | Ensemble, dans le README |
| 2 | Spec de notation et vecteurs de conformance | À décider |
| 3 | Règles écrites à la main | À décider (voir les décisions ouvertes) |
| 4 | Golden set : générateur seedé, rédaction des cas, relecture | Claude, en TDD, avec un résumé des choix |
| 5 | Protocole de l'étape 1, puis itération sur le `dev` | Ensemble |
| 6 | Étape 2 : serveur MCP et son protocole | Ensemble, selon `docs/mcp-bonnes-pratiques.md` |
| 7 | Étape 3 : génération de la table et son protocole | Ensemble |
| 8 | Gel, run final sur le `test`, rapport, README racine | Ensemble |

## Décisions ouvertes

- **Qui écrit les règles, et combien de fois.** Si le même code sert de variante et d'oracle, un bogue dans une règle ne se voit pas : les deux se trompent ensemble. Proposition : deux écritures indépendantes, l'oracle dans le générateur du golden set et les règles de l'expérience, comparées sur tous les cas. Une divergence se corrige alors en relisant l'article.
- Les six autres points sont dans la section « Points à trancher » du [README](README.md) : calendrier des jours fériés, métrique principale, modèles et tailles, forme des règles, relecture de la table à l'étape 3, familles de Holm.
