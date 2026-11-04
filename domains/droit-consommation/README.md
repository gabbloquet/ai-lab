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
| Empreinte SHA-256 de l'archive | à calculer à l'extraction ; elle sera enregistrée dans `data/v1/MANIFEST.json` |
| Texte extrait | Code de la consommation, `LEGITEXT000006069565` (identifiant relevé dans des liens Légifrance, à confirmer dans l'archive) |
| État du droit | versions en vigueur au 13 juillet 2025 |

Vérifié le 2026-11-04 : la licence et le contenu de la base sur data.gouv.fr, et la liste des archives sur le serveur de la DILA. Ce jour-là, l'archive du 13 juillet 2025 est la seule archive complète. Les archives quotidiennes qui suivent ne sont pas utilisées.

**Mention de la source**, exigée par la Licence Ouverte : « Source : DILA, base LEGI, archive du 13 juillet 2025 ».

## Pourquoi ce corpus

- **Des réponses courtes et vérifiables.** Le code est riche en délais, montants, seuils et conditions : une bonne réponse se note sans juge LLM.
- **Des difficultés réelles pour un RAG.** Numéros d'article, renvois d'un article à l'autre, exceptions, définitions éloignées de leur usage, partie législative et partie réglementaire qui se complètent. Les modes d'échec ci-dessous en découlent.
- **Un risque connu : le modèle a pu apprendre ce texte.** Le droit français est public et largement diffusé. Chaque expérience mesure donc d'abord ce que le modèle sait sans récupération (voir la 002).

## Entités

### Article

Un article du code, dans sa version en vigueur au 13 juillet 2025.

| Champ | Type | Exemple de format | Rôle |
|---|---|---|---|
| `id` | chaîne : `LEGIARTI` suivi de 12 chiffres | `LEGIARTI000032227169` | Identifiant LEGI de la version de l'article ; c'est la référence du golden set |
| `num` | chaîne | `L. 221-18` | Numéro de l'article, tel qu'on le cite |
| `part` | `L`, `R` ou `D` | `L` | Partie législative (L) ou réglementaire (R, D) |
| `path` | liste de chaînes | `["Livre II", "Titre II", "Chapitre Ier", "Section 3"]` | Place de l'article dans le plan du code, du livre à la section |
| `text` | chaîne | | Texte de l'article, sans balises |
| `valid_from` | date | `2016-07-01` | Date d'entrée en vigueur de cette version |

Le format exact de `num` et `path`, ainsi que le traitement des alinéas, sont fixés par l'extracteur. Ils seront documentés ici avec la v1.

### Renvoi

Un article qui en cite un autre, par exemple « dans les conditions prévues à l'article L. 221-5 ». Un renvoi relie deux `id`. C'est l'extracteur qui décide comment les repérer, entre les liens fournis par LEGI et une détection dans le texte ; ce choix sera documenté avec la v1.

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

## Golden set

À venir : `golden/rag-qa/v1/`, avec un split `dev` et un split `test`. Les règles de construction seront décrites dans `golden/rag-qa/README.md`. Elles reposent sur quatre principes :
- une réponse courte, présente dans le texte : un délai, un montant, un oui ou un non accompagné de son fait clé ;
- les `id` des articles qui justifient la réponse ;
- des questions sans réponse dans le code ;
- aucune question qui demande une interprétation juridique. C'est une limite assumée, écrite dans les expériences.

## Versions

| Jeu | Chemin | Statut |
|---|---|---|
| Données | `data/v1/` | à extraire |
| Golden set RAG | `golden/rag-qa/v1/` | à construire |

Un jeu publié ne change plus ; une correction donne une `v2`.
