# NNN — Titre court de l'expérience

> **Statut :** cadrage | itération (dev) | gelée | conclue
> **Domaines :** [`<domaine>`](../../domains/<domaine>/README.md)
> **Spec de notation :** [`<famille>/vN`](../../evals/spec/<famille>/vN/SPEC.md)

Les sections Question, Hypothèse, Protocole, Discipline d'itération et Mesures s'écrivent **avant** le premier run. Résultats, Verdict et Limites se remplissent après.

## Question

Une seule question, à laquelle on peut répondre par un chiffre.

## Hypothèse

- **H1 :** ce qu'on s'attend à observer, avec le sens de l'écart (B meilleure ou moins bonne que A).
- **H0 :** pas de différence mesurable entre A et B.
- **Plus petit écart qui compte en pratique :** en dessous de X points, l'écart n'a pas d'intérêt.

## Protocole

| Élément | Valeur |
|---|---|
| Baseline (A) | |
| Variante (B) | |
| Ce qui change entre A et B | une seule chose |
| Ce qui est fixé | modèle, prompt système, température, nombre maximal d'étapes, … |
| Modèles | `<fournisseur>/<modèle>`, … (un verdict par modèle) |
| Golden set | `domains/<domaine>/golden/<famille>/vN`, n_dev = …, n_test = … |
| Répétitions | k = … |
| Implémentations | `java/`, `python/` |

**Taille de l'échantillon.** MDE = (t₀,₉₇₅ + t₀,₈₀) × s_d / √n_test. Indiquer l'hypothèse retenue pour s_d, le MDE obtenu, et le comparer au plus petit écart qui compte.

**Lancer un run :** donner la commande exacte.

## Discipline d'itération

Le split `dev` sert à mettre au point les variantes, le split `test` à les juger. Trois règles empêchent de biaiser le verdict :

1. **Même effort pour chaque variante.** Budget fixé avant de commencer : N cycles d'itération sur le `dev` par variante. Un cycle, c'est une modification suivie d'un run `dev`.
2. **Gel avant le run final.** Les deux variantes sont figées par un commit, et plus rien ne change ensuite.
3. **Un seul run sur le `test`.** On ne relance pas pour obtenir un meilleur résultat. Un run raté pour une raison technique (panne, quota dépassé) se relance en entier, et l'incident est noté dans les Limites.

**Budget d'itération :** N = … cycles par variante.

**Journal d'itération**, sur le `dev` uniquement :

| # | Date | Variante | Modification | Motif | `success` dev |
|---|---|---|---|---|---|
| 1 | | | | | |

**Commit de gel :** `<hash>` du `<date>`
**Run final sur le `test` :** `<date>`, rapport [`results/<date>-<slug>.md`](results/)

## Mesures

- **Métrique principale, qui porte le verdict :** …, telle que définie dans la spec.
- **Métriques secondaires, publiées sans porter le verdict :** …
- **Règle de verdict :** celle de la spec (§ Agrégation et verdict), sauf mention contraire justifiée ici avant le run.

## Résultats

Split `test`, n = …, k = …. Une table par modèle.

| Métrique | A | B | Delta | IC 95 % |
|---|---|---|---|---|
| | | | | |

Les résultats `dev` éventuels vont dans une section à part, signalée comme telle.

## Verdict

Pour chaque modèle : **B meilleure**, **B moins bonne** ou **non concluant**, avec le delta et son IC. Une phrase d'interprétation au plus.

Pour un **non concluant**, dire si l'IC exclut le plus petit écart qui compte, en gain et en perte. Sans cela, ne pas écrire que A et B se valent, ni que le levier pèse peu.

Pour un verdict **concluant**, dire aussi si l'IC exclut cet écart : l'effet est alors mesuré, mais sous le seuil utile.

Quand l'expérience compare plusieurs leviers, les classer par leur delta et leur IC, pas par leur verdict. Si deux deltas voisins ont deux verdicts à cause de la correction de Holm, le dire.

**Avant de publier le rapport :** relire le protocole et `git log` depuis le commit de gel, pour appliquer toute règle ajoutée entre-temps. **À la clôture :** mettre à jour le README racine dans le même commit (statut, résultats clés, domaines).

## Limites

Ce que l'expérience ne permet pas de conclure, les biais connus, les incidents de run, et les vérifications de versions ou de specs externes (mention « vérifié le <date> » ou « non vérifié »).
