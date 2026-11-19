# 003 — Décision réglementaire : où placer le LLM ?

> **Statut :** cadrage (proposition du 2026-11-19 : le protocole n'est pas figé, aucun run)
> **Domaines :** [`droit-consommation`](../../domains/droit-consommation/README.md)
> **Spec de notation :** à créer (nouvelle famille, nom à trancher)

Les sections Question, Hypothèse, Protocole, Discipline d'itération et Mesures s'écrivent **avant** le premier run. Résultats, Verdict et Limites se remplissent après.

Ce README est une proposition. Chaque « à trancher » est une décision du propriétaire, réunie dans la section [Points à trancher](#points-à-trancher-avant-de-figer-le-protocole).

## Question

Pour une décision réglementaire dont les règles sont écrites dans un texte, où placer le LLM : le laisser décider, lui faire extraire les faits pour un moteur de règles, ou lui faire écrire les règles ?

L'expérience compare trois leviers. Elle se découpe donc en trois étapes, une par levier, et conclut par le tableau des deltas.

## Décision étudiée

**« À la date D, le consommateur peut-il encore se rétracter ? »**

| Élément | Valeur |
|---|---|
| Entrée | Un cas rédigé en langage naturel : le contrat, les dates, et la date D à laquelle le consommateur veut se rétracter |
| Sortie | `oui`, `non : hors champ`, `non : exclusion` ou `non : délai expiré`, et la date limite quand elle existe |
| Articles codés en règles | L221-18 (champ et point de départ du délai), L221-19 (calcul du délai), L221-20 (prolongation de douze mois), L221-28 (13 exclusions) |
| Hors périmètre | L221-21 à L221-27 (modalités, remboursement, frais) : ce sont des conséquences de la rétractation, pas la décision |
| Source | `domains/droit-consommation/data/v1/articles.jsonl`, articles en vigueur au 13/07/2025 |

Le périmètre se limite à une décision. Coder tout le Code de la consommation demanderait des règles écrites à la main et juridiquement justes pour chaque décision : le risque d'erreur dans l'oracle grandit avec le périmètre.

## Étapes

| Étape | Levier | Baseline gelée | Variante |
|---|---|---|---|
| 1 | Qui décide | Le LLM seul, avec les articles en contexte | Le LLM extrait les faits, des règles écrites à la main décident |
| 2 | Comment les règles sont appelées | Étape 1 : enchaînement fixe, extraction puis règles | Les mêmes règles en outil MCP, que le LLM choisit d'appeler |
| 3 | Qui écrit les règles | Étape 1 : règles écrites à la main | Une table de décision écrite par le LLM, gelée, puis exécutée sans LLM |

Les étapes 2 et 3 se jugent contre la variante de l'étape 1, et non contre le LLM seul : sinon chacune mêlerait deux leviers. La comparaison au LLM seul reste possible en comparaison secondaire, à déclarer avant le run.

## Hypothèse

Les hypothèses ci-dessous sont des propositions. Le sens attendu et le plus petit écart qui compte sont à trancher.

- **Étape 1.**
  - **H1 :** l'extraction suivie des règles décide plus juste que le LLM seul.
  - **H0 :** pas de différence mesurable.
- **Étape 2.**
  - **H1 :** à écrire. L'outil MCP n'ajoute pas de règle : on attend au mieux l'égalité avec l'étape 1, et une perte si le LLM n'appelle pas l'outil ou lui passe de mauvais faits. La question est donc de savoir si la perte dépasse le plus petit écart qui compte.
  - **H0 :** pas de différence mesurable.
- **Étape 3.**
  - **H1 :** à écrire. Les règles écrites à la main servent d'oracle : la table du LLM ne peut pas faire mieux sur le contenu des règles. La question est la même qu'à l'étape 2 : combien perd-on ? Le gain attendu est ailleurs, dans le temps d'écriture des règles, qui n'est pas mesuré ici.
  - **H0 :** pas de différence mesurable.
- **Plus petit écart qui compte en pratique :** à trancher, par étape.

## Protocole

| Élément | Valeur |
|---|---|
| Baseline et variante | Voir [Étapes](#étapes) |
| Ce qui change | Un levier par étape |
| Contexte donné au LLM | Les 12 articles L221-18 à L221-28 (dont L221-26-1), fixes, sans récupération. Chercher dans tout le code ajouterait un levier de récupération, déjà mesuré par la 002 |
| Schéma des faits | Fixé avant l'étape 1 et commun aux trois étapes. Si le LLM de l'étape 3 choisissait son schéma, l'extraction changerait aussi et le levier ne serait plus isolé. À écrire |
| Ce qui est fixé | Modèle, prompt système, température, nombre maximal d'étapes : à écrire |
| Modèles | À trancher (un verdict par modèle) |
| Golden set | À créer : `domains/droit-consommation/golden/<famille>/v1`. Synthétique : un script seedé tire les cas dans l'espace des faits, les règles calculent la décision attendue, puis le cas est rédigé en langage naturel et relu. n_dev et n_test à dimensionner |
| Répétitions | k à trancher. À l'étape 3, l'unité de répétition est la table générée, pas l'appel : il faut k générations pour mesurer une dispersion |
| Implémentations | À trancher (`java/`, `python/`) |

**Taille de l'échantillon.** MDE = (t₀,₉₇₅ + t₀,₈₀) × s_d / √n_test. Le golden set est synthétique : n_test se choisit d'après le plus petit écart qui compte, et non l'inverse. Ce qui borne la taille est la relecture des cas rédigés. Hypothèse sur s_d et MDE : à écrire.

**Lancer un run :** à écrire.

## Discipline d'itération

Le split `dev` sert à mettre au point les variantes, le split `test` à les juger. Trois règles empêchent de biaiser le verdict :

1. **Même effort pour chaque variante.** Budget fixé avant de commencer : N cycles d'itération sur le `dev` par variante. Un cycle, c'est une modification suivie d'un run `dev`. Aux étapes 2 et 3, la baseline compte les cycles qu'elle a reçus à l'étape 1, et le levier a droit au même nombre.
2. **Gel avant le run final.** Les variantes sont figées par un commit, et plus rien ne change ensuite.
3. **Un seul run sur le `test`.** On ne relance pas pour obtenir un meilleur résultat. Un run raté pour une raison technique (panne, quota dépassé) se relance en entier, et l'incident est noté dans les Limites.

Le golden set étant synthétique, chaque étape peut recevoir un `test` neuf, tiré avec une autre graine. À trancher : un `test` par étape, ou un seul `test` lu une fois par un run consolidé.

**Budget d'itération :** N = … cycles par variante (à fixer).

**Journal d'itération**, sur le `dev` uniquement :

| # | Date | Étape | Variante | Modification | Motif | Métrique principale, dev |
|---|---|---|---|---|---|---|
| 1 | | | | | | |

**Commit de gel :** à venir
**Run final sur le `test` :** à venir

## Mesures

- **Métrique principale, qui porte le verdict :** proposition : l'exactitude de la décision, parmi les quatre issues. À trancher : la date limite compte-t-elle dans la métrique principale ?
- **Métriques secondaires, publiées sans porter le verdict :**
  - exactitude de la date limite ;
  - exactitude des faits extraits (étapes 1 et 2) ;
  - cohérence : sur k répétitions du même cas, la décision est-elle la même ?
  - taux d'appel de l'outil (étape 2) ;
  - coût et latence par décision, à modèle constant.
- **Règle de verdict :** celle de la spec, à écrire.

## Points à trancher avant de figer le protocole

1. **Schéma des faits.** Un seul champ « motif d'exclusion », que le LLM qualifie, ou des faits élémentaires que les règles combinent. Le premier laisse au LLM le raisonnement juridique, et les règles n'ont presque plus rien à décider.
2. **Renvois hors périmètre.** L221-18 et L221-28 renvoient à L221-4, L221-5 (7°) et L221-13. Les lire et les coder, ou supposer que le contrat entre dans le champ du chapitre et l'écrire dans les limites.
3. **Calendrier.** L221-19 reporte l'échéance qui tombe un samedi, un dimanche ou un jour férié ou chômé. Il faut une liste de jours fériés figée dans le domaine. « Chômé » ne se définit pas sans connaître le professionnel.
4. **Métrique principale et plus petit écart qui compte**, par étape.
5. **Modèles, k, n_dev et n_test.**
6. **Forme des règles et langage.** DMN, table de décision ou code ; Java, Python ou les deux.
7. **Étape 3 : avec ou sans relecture humaine de la table.** Ce sont deux variantes différentes.
8. **Familles de Holm.** Trois étapes et plusieurs modèles : dire d'avance quelles comparaisons forment une famille.

## Résultats

Aucun run à ce jour.

## Verdict

À venir.

## Limites

Limites connues dès le cadrage, à compléter après les runs :

- **Une seule décision, dans un seul code.** Rien ne dit que le classement des leviers tient pour une autre décision.
- **Les règles écrites à la main sont aussi l'oracle.** Aux étapes 1 et 2, la variante ne peut se tromper que sur les faits : ces étapes mesurent l'extraction et l'appel d'outil, pas le contenu des règles. Une erreur juridique dans les règles compterait à tort contre le LLM seul. Seule l'étape 3 met le contenu des règles à l'épreuve.
- **Des cas sans ambiguïté.** Plusieurs exclusions de L221-28 demandent un jugement (« nettement personnalisés », « se périmer rapidement », « raisons d'hygiène »). Pour que l'oracle soit sûr, le générateur ne produit que des cas tranchés : l'expérience ne dit rien des cas limites.
- **Des cas synthétiques**, rédigés à partir de faits tirés au hasard, et non des litiges réels.
- **Travaux existants : non vérifié** au 2026-11-19. La littérature sur ces comparaisons n'a pas été consultée.
