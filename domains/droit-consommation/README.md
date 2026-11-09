# Domaine `droit-consommation`

Le Code de la consommation français, extrait de la base LEGI de la DILA, dans son état au **13 juillet 2025**. Ce domaine sert à la série d'expériences sur le RAG : quels leviers corrigent un RAG qui répond mal ?

**Données publiques, pas synthétiques.** Les articles sont repris tels que la DILA les publie. Ce domaine ne contient aucune donnée client et aucune donnée personnelle.

**Ce n'est pas une source officielle du droit.** Le texte peut avoir changé depuis le 13 juillet 2025, et l'extraction peut contenir des erreurs. Ne vous en servez pas pour un conseil juridique : la version qui fait foi est sur [Légifrance](https://www.legifrance.gouv.fr/).

## Source et licence

| Élément | Valeur |
|---|---|
| Producteur | DILA (Direction de l'information légale et administrative), pour le Premier ministre |
| Base | [LEGI : codes, lois et règlements consolidés](https://www.data.gouv.fr/datasets/53ae8af9a3a729709f56d50c) |
| Licence | [Licence Ouverte / Open Licence](https://www.etalab.gouv.fr/licence-ouverte-open-licence/) (Etalab) |
| Archive | `Freemium_legi_global_20250713-140000.tar.gz` (1,1 Go), sur [echanges.dila.gouv.fr/OPENDATA/LEGI/](https://echanges.dila.gouv.fr/OPENDATA/LEGI/) |
| Empreinte SHA-256 de l'archive | `f862b4a2238e11ec3c48ec70f3b1c68bac0bb1985907841666b98608653d4eca`, vérifiée par l'extracteur |
| Texte extrait | Code de la consommation, `LEGITEXT000006069565` (confirmé dans l'archive : c'est le cid de ses articles) |
| État du droit | versions en vigueur au 13 juillet 2025 |

Vérifié le 2026-11-04 : la licence et le contenu de la base sur data.gouv.fr, et la liste des archives sur le serveur de la DILA. Ce jour-là, l'archive du 13 juillet 2025 est la seule archive complète. Les archives quotidiennes qui suivent ne sont pas utilisées.

**Mention de la source**, exigée par la Licence Ouverte : « Source : DILA, base LEGI, archive du 13 juillet 2025 ».

## Pourquoi ce corpus

- **Des réponses courtes et vérifiables.** Le code est riche en délais, montants, seuils et conditions : une bonne réponse se note sans juge LLM.
- **Des difficultés réelles pour un RAG.** Numéros d'article, renvois d'un article à l'autre, exceptions, définitions éloignées de leur usage, partie législative et partie réglementaire qui se complètent. Les modes d'échec ci-dessous en découlent.
- **Un risque connu : le modèle a pu apprendre ce texte.** Le droit français est public et largement diffusé. Chaque expérience mesure donc d'abord ce que le modèle sait sans récupération (voir la 002).

## Entités

### Article

Un article du code, dans sa version en vigueur au 13 juillet 2025. Une ligne de `data/v1/articles.jsonl` par article, triées par `id`.

| Champ | Type | Exemple | Rôle |
|---|---|---|---|
| `id` | chaîne : `LEGIARTI` suivi de 12 chiffres | `LEGIARTI000032226842` | Identifiant LEGI de cette version de l'article ; chaque version a le sien. C'est la référence du golden set |
| `num` | chaîne | `L221-18` | Numéro tel que LEGI l'écrit, sans point ni espace (le texte cite « L. 221-18 »). Quelques numéros ne sont pas de la forme L, R ou D : `liminaire`, `Annexe à l'article R313-4` |
| `part` | `legislative` ou `regulatory` | `legislative` | Partie du code, tirée de la racine du plan |
| `path` | liste de chaînes | `["Partie législative nouvelle", "Livre II : FORMATION ET ÉXECUTION DES CONTRATS", …]` | Titres du plan, de la partie à la section qui contient l'article |
| `section_id` | chaîne : `LEGISCTA…` | `LEGISCTA000032226844` | Section qui contient l'article : utile pour un découpage par section |
| `text` | chaîne | | Texte de l'article (voir ci-dessous) |
| `nota` | chaîne, souvent vide | | Note de la DILA, par exemple une condition d'entrée en vigueur. Séparée du texte : chaque expérience décide de l'indexer ou non |
| `valid_from` | date | `2016-07-01` | Début de vigueur de cette version |
| `valid_to` | date ou `null` | `null` | Fin de vigueur déjà connue (abrogation différée), sinon `null` |
| `cites` | liste d'`id` | | Articles du code que cet article cite (voir Renvoi) |

**Texte.** Le HTML de LEGI devient du texte brut : une ligne par alinéa (`<p>`, `<div>`, `<br>`), une ligne par rangée de tableau avec ses cellules séparées par ` | `, la mise en forme en ligne (`<b>`, `<sup>`…) gardée dans la ligne. Les espaces, y compris insécables, sont réduites à une espace simple.

**Version en vigueur.** Une version l'est le jour J si `DATE_DEBUT ≤ J < DATE_FIN`, sauf les versions mort-nées ou annulées (`MODIFIE_MORT_NE`, `ANNULE`), jamais entrées en vigueur. Quand LEGI laisse deux versions ouvertes pour un même numéro, l'extracteur garde celle qui commence le plus tard et l'inscrit dans les `anomalies` du manifeste. C'est arrivé une fois en v1 (R542-1).

### Renvoi

Un article qui en cite un autre, par exemple L221-18, qui vise « ceux mentionnés à l'article L. 221-4 ». Un renvoi relie deux `id`.

Les renvois viennent des liens de LEGI (`typelien="CITATION"`, `sens="source"`, vers le même code), pas d'une détection dans le texte. LEGI pointe souvent vers une ancienne version de l'article cité : le lien est donc rattaché par **numéro** à la version en vigueur. Un renvoi d'un article vers lui-même est ignoré ; un renvoi vers un numéro absent du corpus est compté dans `unresolved_cites` (83 en v1, dont 53 liens sans numéro).

**Limite connue.** LEGI ne relie pas toujours chaque article d'une plage : L221-18 cite « les articles L. 221-23 à L. 221-25 », mais n'a de lien que vers L221-23. Les renvois sont donc incomplets.

Les renvois servent à construire des questions dont la réponse se trouve sur plusieurs articles.

## Modes d'échec visés

Le golden set couvre chacun de ces modes. Chaque item indique son mode, pour qu'on puisse publier les scores mode par mode.

| Mode | Ce qui fait échouer un RAG naïf | Levier qui pourrait le corriger |
|---|---|---|
| Référence exacte | la question cite un numéro d'article, et la recherche dense ne le retrouve pas | recherche hybride (BM25 et dense) |
| Paraphrase | la question n'emploie pas les mots du texte | réécriture de requête |
| Réponse sur plusieurs articles | la règle est dans un article, son exception ou sa condition dans un autre | multi-query, récupération qui suit les renvois |
| Contexte perdu | un passage découpé n'a plus de sens hors de son article ou de sa section | découpage par article, contextualisation des chunks |
| Sans réponse | le code ne répond pas à la question | prompt qui autorise « le code ne le précise pas » |

## Volumétrie (v1)

| Mesure | Valeur |
|---|---|
| Versions d'article lues dans l'archive | 6 131 |
| Articles en vigueur au 13/07/2025 | 2 150 (1 291 en partie législative, 859 en partie réglementaire) |
| Renvois résolus | 2 192, partant de 1 137 articles, vers 893 articles distincts |
| Articles avec un `nota` | 488 |
| Articles à abrogation différée (`valid_to` renseigné) | 11 |
| Longueur du texte, en caractères | médiane 424, 9e décile 1 365, maximum 39 906 (une annexe) ; 1,49 million au total |

## Extraire

```bash
curl -fo domains/droit-consommation/.cache/Freemium_legi_global_20250713-140000.tar.gz \
  https://echanges.dila.gouv.fr/OPENDATA/LEGI/Freemium_legi_global_20250713-140000.tar.gz
uv run python domains/droit-consommation/consommation_extract.py \
  --archive domains/droit-consommation/.cache/Freemium_legi_global_20250713-140000.tar.gz --version v1
```

L'archive (1,1 Go) n'est pas versionnée : `.cache/` est ignoré par git. L'extracteur refuse une archive dont l'empreinte diffère et une version qui existe déjà. Il lit l'archive en un seul passage, sans la décompresser sur disque (environ 2 minutes). `MANIFEST.json` enregistre la source, son empreinte, les comptes, les anomalies et l'empreinte de `articles.jsonl`.

## Golden set

`golden/rag-qa/v1/` (publiée) et `golden/rag-qa/v2/`, chacune avec un split `dev` et un split `test`. Les règles de construction sont décrites dans [`golden/rag-qa/README.md`](golden/rag-qa/README.md). Elles reposent sur quatre principes :
- une réponse courte, présente dans le texte : un délai, un montant, un oui ou un non accompagné de son fait clé ;
- les `id` des articles qui justifient la réponse ;
- des questions sans réponse dans le code ;
- aucune question qui demande une interprétation juridique. C'est une limite assumée, écrite dans les expériences.

## Versions

| Jeu | Chemin | Statut |
|---|---|---|
| Données | `data/v1/` | extraites le 2026-11-04 par `consommation_extract.py`. **Publiées** : citées par le run final de la 002 |
| Golden set RAG | `golden/rag-qa/v1/`, `v2/`, `v3/` | v1 publiée (2026-11-07), citée par les 002 à 005 ; v2 (2026-11-09) : la v1 plus 24 questions sans réponse dans le `dev`, même `test` ; v3 (2026-11-09) : la v2 plus 40 questions sans réponse dans le `test`. Audit des questions sans réponse de la v1 : `golden/rag-qa/audit/` |

Un jeu publié ne change plus ; une correction donne une `v2`.
