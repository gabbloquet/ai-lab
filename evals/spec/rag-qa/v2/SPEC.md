# Spec de notation — famille `rag-qa`, v2

> **Statut : publiée** le 2026-11-12, citée par le [run `dev` de contrôle de la 002 sur la v5](../../../../experiments/002-leviers-rag/results/2026-11-12-controle-dev-v5.md). Elle ne change plus ; toute correction passe par une `v3`.

## 0. Ce qui change depuis la v1

La [v1](../v1/SPEC.md) reste valable pour les rapports qui la citent. La v2 corrige trois limites relevées sur `rag-qa/v4`, et ajoute ce que demandent les étapes 7 et 8 de la 002 ([plan](../../../../experiments/002-leviers-rag/PLAN.md)).

| Changement | Motif | Section |
|---|---|---|
| Forme à mots-clés (`tokens`, `window`) | En `set`, un élément reformulé n'était pas retrouvé (`rq-267` : « évaluer et contrôler l'activité » au lieu de « évaluer leur activité ») | § 5.2 |
| Ancre d'un fait (`anchor`) et règle de rattachement | En `comparison`, une réponse qui attribue une valeur au mauvais cas était comptée juste | § 5.3 |
| Fausse valeur (`false_value`) et règle de rejet de la prémisse | En `false_premise`, une réponse qui donne les deux valeurs sans trancher était comptée juste | § 5.4 |
| Espace entre un chiffre et `%` ou `€` supprimée | « 10% » ne retrouvait pas « 10 % » | § 4 |
| `latency_s`, `cost_usd`, `tool_calls` ; contexte à plusieurs appels | L'étape 7 compare en dollars et en latence, et l'étape 8 compte les appels d'un RAG agentique | § 3.2, § 6, § 7 |
| Schéma des exécutions (`execution.schema.json`) | Les deux scorers lisent les mêmes exécutions : une conversion fautive doit être rejetée avant la notation | § 3.2 |
| Agrégats calculés par le scorer partagé, avec des clés fixées | En v1, chaque expérience les calculait elle-même, sans vecteur pour les vérifier | § 7, § 9 |
| Comparaison sur toute métrique, avec un sens ; n < 2 donne `null` | Le § 8 v1 ne disait ni comment traiter les valeurs nulles par item, ni quoi faire avec moins de deux items | § 8.1 |
| Verdict à deux critères (`tradeoff` compris) | Les étapes 5 et 6 de la 002 l'utilisent, mais seul un test Python le vérifiait | § 8.2 |
| p-value, correction de Holm et verdict corrigé | Le run consolidé de la 002 les publie, mais ils n'étaient calculés que dans son code | § 8.3 |
| Items exclus | La 002 en exclut par audit, sans règle écrite | § 8.4 |
| Scorer Java en plus du scorer Python | Règle du dépôt : chaque langage a son scorer | § 1, § 9 |

Les nouvelles règles se déclenchent selon les champs présents dans l'item, jamais selon son `mode`. Un item v1 valide reste valide en v2 et se note comme en v1, à la normalisation près (§ 4, étape 8).

**Étalonnage.** Les règles des § 5.3 et § 5.4 ont été choisies parmi plusieurs candidates. Le choix s'est fait sur toutes les exécutions `dev` de `rag-qa/v4` produites par la 002, les 2026-11-09 et 2026-11-10 : trois modèles, étapes 1 à 6, une répétition. Cela fait 84 exécutions `comparison` sur 4 items et 210 exécutions `false_premise` sur 10 items. Aucun item `test` n'a été lu.

- **Rattachement.** La règle retenue rejette les 2 exécutions mal rattachées, que la v1 comptait justes, et accepte les 50 autres. Les règles « ancre la plus proche » et « phrase exclusive » donnaient 7 à 25 faux négatifs.
- **Prémisse.** Les 26 exécutions sans abstention qui citent les deux valeurs rejettent toutes la prémisse explicitement. La règle retenue les accepte toutes, alors qu'exiger l'absence de la fausse valeur les aurait toutes rejetées. Pour `correct`, une fenêtre de 4 mots laisse 1 faux négatif, et une fenêtre de 5 mots aucun. Le diagnostic `premise` ne tient pas compte de l'abstention : il lui faut une fenêtre de 6 mots pour n'avoir aucun faux négatif, d'où le choix de 6.
- **Limites de l'étalonnage.** Il porte sur peu d'items. Les ancres ont été écrites après lecture des réponses. Le run `dev` de contrôle sur `rag-qa/v5` en donnera la première mesure indépendante.

## 1. Objet

Cette spec note **la réponse** d'un système à une question posée sur un corpus de documents, avec ou sans récupération (RAG). Quand le système fournit un contexte au modèle, elle note aussi ce contexte : y trouvait-on les documents nécessaires ? Elle classe enfin chaque échec, selon qu'il vient de la récupération ou de la génération.

La notation est **déterministe**, sans juge LLM : une réponse est juste si elle contient les faits attendus (§ 5), rattachés à leur cas quand l'item le demande (§ 5.3), sans reprendre une fausse prémisse (§ 5.4).

Deux scorers l'implémentent : un test JUnit dans `evals/java/` et une métrique DeepEval personnalisée dans `evals/python/`. Les deux doivent passer tous les vecteurs de `conformance.jsonl` (§ 9).

## 2. Vocabulaire

| Terme | Définition |
|---|---|
| **Item** | Une question du golden set |
| **Article** | Un document du corpus, identifié par un `id` et cité par son numéro (`num`) |
| **Fait attendu** | Une information courte que la réponse doit contenir, donnée sous une ou plusieurs **formes acceptées** |
| **Ancre** | Les formes qui désignent le cas auquel un fait se rapporte, dans une question qui compare plusieurs cas |
| **Fausse valeur** | La valeur erronée que la question tient pour acquise, quand l'item teste une fausse prémisse |
| **Item avec réponse** | Item dont le corpus contient la réponse (`answerable: true`) |
| **Item sans réponse** | Item auquel le corpus ne répond pas (`answerable: false`) : la bonne réponse est l'abstention |
| **Variante** | Une configuration testée, par exemple « modèle seul » ou « RAG naïf » |
| **Exécution** | Une tentative de réponse à un item, pour une variante, un modèle et une répétition |
| **Contexte** | Les articles réellement donnés au modèle pour une exécution, dans l'ordre où il les a reçus |
| **Appel de recherche** | Une recherche dans le corpus déclenchée par le modèle lui-même, dans une variante agentique |
| **Abstention** | Le système déclare que le corpus ne permet pas de répondre |

## 3. Entrées

### 3.1 Item du golden set

Fichier `items.jsonl`, un objet par ligne, validé par `golden.schema.json` :

```json
{
  "id": "rq-001",
  "split": "dev",
  "mode": "paraphrase",
  "answerable": true,
  "question": "J'ai acheté un aspirateur en ligne, combien de temps ai-je pour changer d'avis ?",
  "expected": {
    "facts": [{"accepted": ["quatorze jours", "14 jours"]}],
    "articles": [{"id": "LEGIARTI000032226842", "num": "L221-18"}]
  },
  "evidence": [{"article": "LEGIARTI000032226842", "quote": "dispose d'un délai de quatorze jours"}]
}
```

Les champs de la v1 ne changent pas :
- `split` vaut `dev` ou `test`. Les items `dev` servent à itérer ; seuls les items `test` portent le verdict (§ 8).
- `mode` dit quel mode d'échec l'item sollicite. Les valeurs possibles sont définies par le golden set du domaine. Le scorer ne s'en sert que pour ventiler les résultats.
- Pour un item avec réponse, `expected.facts` et `expected.articles` contiennent chacun au moins un élément. Pour un item sans réponse, ils sont tous deux vides.
- `evidence` justifie les faits : c'est un extrait copié du corpus. Le golden set le vérifie à sa construction, et le scorer ne le lit pas.
- `source_article`, facultatif, donne l'`id` de l'article à partir duquel un item sans réponse a été construit. Il sert à l'analyse, et le scorer ne le lit pas.

**Forme acceptée.** C'est soit une chaîne (**forme textuelle**, comme en v1), soit un objet (**forme à mots-clés**, § 5.2) :

```json
{"tokens": ["évaluer", "activité"], "window": 4}
```

`tokens` contient au moins deux mots, et `window` est un entier de 0 à 5.

**Ancre.** Un fait peut porter un champ `anchor`, la liste des formes textuelles qui désignent son cas :

```json
"facts": [
  {"accepted": ["375 000 €", "375 000 euros"], "anchor": ["numéros masqués", "démarchage téléphonique"]},
  {"accepted": ["15 000 euros", "15 000 €"], "anchor": ["contenus", "services numériques"]}
]
```

Dans un item, soit aucun fait ne porte d'ancre, soit tous en portent une, et il y a alors au moins deux faits.

**Fausse valeur.** Un item avec réponse peut porter un champ `false_value`, de la même forme qu'un fait mais en formes textuelles seulement :

```json
"false_value": {"accepted": ["30 jours", "trente jours"]}
```

**Règles vérifiées par le générateur**, parce que JSON Schema ne peut pas les exprimer :
- une forme, un mot-clé ou une ancre ne devient pas vide après normalisation (§ 4) ;
- chaque mot-clé d'une forme à mots-clés est un seul mot au sens du § 5.2 ;
- une ancre ou une forme d'un fait ancré ne contient pas de fin de segment (§ 5.3) : ni « . », ni « ; », ni « ! », ni « ? », ni le mot « et » ;
- aucune ancre d'un fait n'est retrouvée dans une ancre d'un autre fait du même item ;
- aucune forme de `false_value` n'est retrouvée dans une forme d'un fait attendu, et inversement ;
- chaque extrait de `evidence` figure dans le texte de son article.

### 3.2 Exécution observée

C'est la forme canonique, utilisée aussi par les vecteurs de conformance et les rapports. Chaque expérience convertit la sortie de son système vers cette forme, validée par `execution.schema.json`. Le format que le modèle doit produire est fixé par le protocole de l'expérience, avec une contrainte : il doit permettre de remplir `answer`, `abstained` et `cited`.

Tous les champs ci-dessous sont obligatoires. Un champ qui ne s'applique pas ou qui n'est pas mesuré vaut `null` : il n'est jamais omis. Les diagnostics propres à une expérience vont dans un objet facultatif `extra`, que le scorer ne lit pas. Aucun autre champ n'est admis.

```json
{
  "item_id": "rq-001",
  "variant": "naive_rag",
  "model": "<fournisseur>/<modèle>",
  "repeat": 0,
  "answer": "Vous disposez de 14 jours.",
  "abstained": false,
  "cited": ["L. 221-18"],
  "context": ["LEGIARTI000032226842", "LEGIARTI000032226840"],
  "usage": {"input_tokens": 1830, "output_tokens": 42},
  "latency_s": 1.42,
  "cost_usd": 0.00031,
  "tool_calls": null,
  "error": null
}
```

| Champ | Type | Règle |
|---|---|---|
| `answer` | chaîne | Réponse rédigée par le modèle. Elle peut être vide |
| `abstained` | booléen | Vrai si le modèle déclare que le corpus ne répond pas à la question |
| `cited` | liste de chaînes | Numéros d'article cités par le modèle, tels qu'il les écrit, **un numéro par élément**. Le format de sortie fixé par le protocole doit l'exiger : une plage ou une liste dans un seul élément (« L. 221-23 à L. 221-25 ») ne correspond à aucun article (§ 6) |
| `context` | liste d'`id`, ou `null` | Articles donnés au modèle. Il vaut `null` pour une variante sans récupération. Quand la récupération renvoie des passages, chaque passage est remplacé par l'`id` de son article, et seule la première occurrence d'un article est gardée. Le scorer applique aussi cette règle avant tout calcul |
| `tool_calls` | entier ≥ 0, ou `null` | Nombre d'appels de recherche faits par le modèle. Il vaut `null` pour une variante où le modèle ne choisit pas de chercher |
| `latency_s` | réel ≥ 0, ou `null` | Durée de bout en bout de l'exécution en secondes, de l'envoi de la question à la réception de la réponse, récupération comprise. Le protocole dit comment elle est mesurée. `null` si elle n'est pas mesurée |
| `cost_usd` | réel ≥ 0, ou `null` | Coût de l'exécution en dollars US : tous les appels payants qu'elle déclenche, calculés à partir de l'usage et d'un barème daté. Le protocole liste les appels comptés, et le rapport cite le barème. `null` s'il n'est pas calculé |
| `usage` | objet | `input_tokens` et `output_tokens`, entiers ≥ 0, ou `null` quand le fournisseur ne les renvoie pas (par exemple après un délai dépassé) |
| `error` | chaîne non vide, ou `null` | Non nul en cas d'erreur d'exécution : exception, délai dépassé, ou sortie impossible à lire dans le format fixé par le protocole |

**Contexte d'une variante agentique.** Quand le modèle fait plusieurs appels de recherche, `context` est la concaténation des résultats de tous les appels, dans l'ordre des appels, puis dans l'ordre du classement de chaque appel. La règle de la première occurrence s'applique à cette concaténation. Si le modèle répond sans chercher, `tool_calls` vaut 0 et `context` est une liste vide, pas `null`.

## 4. Normalisation du texte

Les faits sont recherchés dans `answer` (§ 5) après une même normalisation **N**, appliquée à la réponse comme à chaque forme acceptée, ancre ou fausse valeur. Les étapes s'appliquent dans cet ordre :

1. Normalisation Unicode NFC.
2. Les apostrophes `’` (U+2019), `‘` (U+2018) et `ʼ` (U+02BC) deviennent `'` (U+0027).
3. Tout caractère d'espacement Unicode (`str.isspace`, y compris les espaces insécables U+00A0 et U+202F) devient une espace U+0020.
4. *Casefold* Unicode complet.
5. Suppression des accents : décomposition NFD, suppression des marques de catégorie `Mn`, puis recomposition NFC.
6. Les ligatures `œ` et `æ` deviennent `oe` et `ae`.
7. Suppression des espaces situées entre deux chiffres décimaux (`1 500` devient `1500`).
8. **Nouveau en v2.** Suppression des espaces situées entre un chiffre décimal et un signe `%` ou `€` qui le suit (`10 %` devient `10%`, `1500 €` devient `1500€`).
9. Les suites d'espaces sont réduites à une seule, et les espaces en début et en fin sont retirées.

Exemples : N(« Délai de 1 500 €. ») = « delai de 1500€. », N(« 10 % du prix ») = N(« 10% du prix ») = « 10% du prix », et N(« L’Œuvre ») = « l'oeuvre ».

N ne touche ni à la ponctuation ni aux nombres écrits en lettres. « Quatorze jours » et « 14 jours » sont deux formes distinctes : le golden set doit lister les deux.

L'étape 8 ne fait qu'ajouter des correspondances : une forme et une réponse qui se correspondaient en v1 se correspondent encore en v2.

## 5. Faits retrouvés et réponse juste

### 5.1 Forme textuelle

Une forme textuelle f est **retrouvée** dans un texte T si N(f) apparaît dans N(T) à une position où elle est **délimitée** :
- le caractère qui précède, s'il y en a un, n'est pas une lettre ou un chiffre ;
- le caractère qui suit, s'il y en a un, n'est pas une lettre ou un chiffre.

Est « lettre ou chiffre » tout caractère de catégorie Unicode `L*` ou `N*`. Si N(f) apparaît plusieurs fois, une seule occurrence délimitée suffit. Ainsi, « 14 jours » est retrouvé dans « sous 14 jours. », mais pas dans « 114 jours » ni dans « 14 joursx ».

### 5.2 Forme à mots-clés

Les **mots** d'un texte normalisé sont ses suites maximales de lettres ou chiffres, au sens du § 5.1. Ainsi, « d'evaluer et controler l'activite » a pour mots `d`, `evaluer`, `et`, `controler`, `l`, `activite`.

Une forme `{"tokens": [t₁, …, tₘ], "window": w}` est **retrouvée** dans un texte T s'il existe, parmi les mots de N(T), des positions p₁ < p₂ < … < pₘ telles que :
- le mot en position pⱼ est égal à N(tⱼ), pour chaque j ;
- au plus w mots séparent deux mots-clés consécutifs : pⱼ₊₁ − pⱼ − 1 ≤ w.

Les mots se comparent en entier : `activite` ne retrouve pas `activites`. Le golden set liste les flexions comme formes distinctes, comme en v1.

Exemple : `{"tokens": ["évaluer", "activité"], "window": 4}` est retrouvée dans « d'évaluer et contrôler l'activité », où trois mots (`et`, `controler`, `l`) séparent les deux mots-clés. Elle ne l'est pas dans « l'activité à évaluer », où les mots-clés sont dans l'ordre inverse.

Cette forme sert aux éléments d'une liste que la réponse peut reformuler. Elle ne convient pas aux valeurs chiffrées : `{"tokens": ["15000", "euros"], "window": 3}` serait retrouvée dans « 15 000 € ou 300 000 euros ».

**Fait retrouvé.** Un fait est retrouvé dans un texte si l'une de ses formes acceptées l'est.

### 5.3 Rattachement d'un fait à son cas

Cette règle ne s'applique qu'aux items dont les faits portent une ancre.

**Segments.** La réponse est découpée en segments :
1. On applique NFC à `answer`.
2. **Phrases.** On coupe à chaque suite de caractères parmi `;`, `!`, `?`, U+000A et U+000D. On coupe aussi à chaque `.` suivi d'un caractère d'espacement ou de la fin du texte, sauf quand le mot qui précède ce point (au sens du § 5.2, après casefold) est une seule lettre ou `art`. Ainsi, « L. 242-14 » et « art. L. 221-18 » ne coupent pas. Les caractères de coupure sont retirés.
3. Chaque phrase est normalisée par N. Les phrases vides sont écartées.
4. **Propositions.** Chaque phrase normalisée est coupée à chaque occurrence de « et » entourée d'espaces, éventuellement précédée d'une virgule (` et ` ou `, et `). Le « et », la virgule et les espaces sont retirés. Les propositions vides sont écartées.

Les segments sont toutes les phrases et toutes les propositions. Une phrase sans « et » est à la fois une phrase et sa seule proposition.

**Fait rattaché.** Le fait i est rattaché s'il existe un segment S tel que :
- le fait i est retrouvé dans S ;
- une ancre du fait i est retrouvée dans S (forme textuelle, § 5.1) ;
- aucune ancre d'un autre fait de l'item n'est retrouvée dans S.

Exemples, avec A = « numéros masqués » pour 375 000 € et B = « contenus » pour 15 000 € :
- « 375 000 € pour les numéros masqués et 15 000 € pour les contenus » : rattachés, chacun dans sa proposition.
- « Pour les numéros masqués, 75 000 € pour une personne physique et 375 000 € pour une personne morale. Pour les contenus, 15 000 €. » : rattachés, chacun dans sa phrase.
- « 375 000 € pour les contenus et 15 000 € pour les numéros masqués » : aucun n'est rattaché.
- « L'amende est de 375 000 €. Pour les contenus, elle est de 15 000 €. » : 15 000 € est rattaché, mais pas 375 000 €, dont la phrase ne cite aucun cas (`facts_attached` vaut 1).

**Limite assumée.** Dans une phrase qui cite les deux cas, une valeur séparée de son cas par un « et » n'est pas rattachée. Une réponse qui donne les deux cas avant les deux valeurs (« A et B : 375 000 € et 15 000 € respectivement ») ne l'est pas non plus. Cette règle préfère ces faux négatifs à des inversions comptées justes.

### 5.4 Rejet de la prémisse

Cette règle ne s'applique qu'aux items qui portent un `false_value`.

**Occurrence marquée.** Une occurrence délimitée d'une forme de `false_value` dans N(`answer`) est **marquée** si un marqueur de correction figure parmi les 6 mots qui la précèdent, ou parmi tous les mots qui la précèdent s'il y en a moins de 6. Les mots sont ceux du § 5.2. Un marqueur de plusieurs mots doit y figurer en entier, ses mots consécutifs et dans l'ordre.

Marqueurs, déjà normalisés : `non`, `pas`, `ni`, `plutot que`, `au lieu de`, `contrairement`, `faux`, `inexact`, `errone`, `incorrect`.

**Fausse valeur reprise.** La fausse valeur est reprise si au moins une de ses occurrences délimitées n'est pas marquée.

Exemples, pour la fausse valeur « 30 jours » :
- « Non, le délai est de 14 jours, et non 30 jours. » : non reprise (`non` juste avant).
- « Le délai ne peut pas être de 30 jours : il est de 14 jours. » : non reprise (`pas` trois mots avant).
- « Le délai est de 14 jours, ou de 30 jours selon le cas. » : reprise.

**Limites assumées.**
- Un marqueur peut nier autre chose que la fausse valeur : « vous n'avez pas à payer, sous 30 jours » marque l'occurrence.
- Une réponse qui commence par « oui » et donne la vraie valeur n'est pas pénalisée. Le golden set évite ce cas : il choisit des fausses valeurs qui rendent « oui » faux.

### 5.5 Réponse juste

**Réponse juste (`correct`)**, pour une exécution sans erreur (`error` nul) :

| Item | `correct` vaut vrai si… |
|---|---|
| avec réponse | `abstained` est faux, **et** chaque fait attendu est retrouvé dans `answer`, **et**, si les faits portent une ancre, chacun est rattaché (§ 5.3), **et**, si l'item porte un `false_value`, la fausse valeur n'est pas reprise (§ 5.4) |
| sans réponse | `abstained` est vrai |

Une abstention l'emporte sur le texte : si `abstained` est vrai, la réponse est traitée comme une abstention, quel que soit le contenu de `answer`.

**Limite assumée.** En dehors du § 5.4, la recherche ne détecte pas la négation : « pas 14 jours mais 7 » contient « 14 jours ». Le golden set réduit ce risque en demandant des valeurs, jamais un oui ou un non.

## 6. Métriques par exécution

On note G l'ensemble des `id` de `expected.articles`. Pour un entier k, Cₖ désigne les k premiers éléments de `context`, ou tout `context` s'il en contient moins de k.

| Métrique | Définition | Vaut `null` si… |
|---|---|---|
| **`correct`** | § 5.5 ; faux en cas d'erreur | jamais |
| `facts_found` | nombre de faits attendus retrouvés, sans tenir compte de `abstained` | l'item est sans réponse |
| `facts_attached` | nombre de faits rattachés (§ 5.3), sans tenir compte de `abstained` | l'item est sans réponse, ou ses faits ne portent pas d'ancre |
| `premise` | voir ci-dessous | l'item ne porte pas de `false_value` |
| `false_abstention` | `abstained` est vrai | l'item est sans réponse, ou il y a une erreur |
| `hallucination` | `abstained` est faux | l'item a une réponse, ou il y a une erreur |
| `evidence_recall@k`, k ∈ {1, 3, 5, 10} | \|G ∩ Cₖ\| / \|G\| | `context` est nul, l'item est sans réponse, ou `tool_calls` > 1 |
| `all_evidence@k`, k ∈ {1, 3, 5, 10} | G ⊆ Cₖ | même condition |
| `all_evidence` | G ⊆ `context` | `context` est nul, ou l'item est sans réponse |
| `context_size` | nombre d'articles distincts de `context` | `context` est nul |
| **`failure`** | voir ci-dessous | l'item est sans réponse, ou `context` est nul |
| `citation_precision` | \|P ∩ E\| / \|P\| (voir ci-dessous) | l'item est sans réponse, ou P est vide |
| `citation_recall` | \|P ∩ E\| / \|E\| | l'item est sans réponse |
| `tool_calls`, `latency_s`, `cost_usd` | recopiés de l'exécution, sans notation | le champ est nul |

**Métriques à k fixe et variante agentique.** Avec plusieurs appels de recherche, `context` ne suit plus un classement unique : les métriques à k fixe n'ont donc plus de sens. `all_evidence` et `failure` portent sur le contexte complet, et restent définis.

**Diagnostic `premise`.** On note V « tous les faits attendus sont retrouvés » et F « la fausse valeur est reprise » (§ 5.4). Le diagnostic ne tient pas compte de `abstained`.

| V | F | `premise` |
|---|---|---|
| vrai | faux | `corrected` |
| vrai | vrai | `unresolved` |
| faux | vrai | `adopted` |
| faux | faux | `missed` |

**Diagnostic `failure`.** Il classe chaque exécution sur un item avec réponse, quand la variante fournit un contexte :
- `error` si l'exécution a échoué (quand `context` est nul, `failure` reste nul, même en cas d'erreur) ;
- sinon `correct` si la réponse est juste ;
- sinon `generation_miss` si G ⊆ `context` : tout ce qu'il fallait était sous les yeux du modèle ;
- sinon `retrieval_miss` : au moins un article attendu manquait au contexte.

Le diagnostic porte sur le **contexte complet**, c'est-à-dire ce que le modèle a réellement reçu, et non sur un top-k fixe. Une réponse fausse par défaut de rattachement ou par reprise de la prémisse, avec G ⊆ `context`, est un `generation_miss`.

**Citations.** Un numéro d'article est normalisé par la fonction **C** :
1. N (§ 4) ;
2. suppression des préfixes `articles`, `article` et `art.` en début de chaîne ;
3. suppression des espaces et des points ;
4. passage en majuscules.

Ainsi, C(« Article L. 221-18 ») = C(« l221-18 ») = « L221-18 ». P est l'ensemble des C(c) pour c dans `cited`, et E l'ensemble des C(`num`) des articles attendus. Les doublons de `cited` ne comptent qu'une fois.

**Erreur d'exécution.** `correct` vaut faux et l'item **reste compté** : l'exclure avantagerait la variante qui échoue. `failure` vaut `error`. Les métriques de contexte se calculent sur le `context` émis avant l'erreur, s'il y en a un. Les métriques de réponse (`facts_found`, `facts_attached`, `premise`, citations) se calculent sur les champs reçus.

**Tokens.** Ils ne sont pas notés. On les agrège (moyenne par item de `input_tokens + output_tokens`) et on ne les compare qu'à modèle constant.

## 7. Agrégats par variante

Ces agrégats sont publiés sans porter le verdict. Ils sont calculés par le scorer partagé, et non par le code de chaque expérience : deux étapes qui publient un même taux le calculent donc de la même façon.

**Entrées.** Le golden set, les exécutions d'**une** variante avec **un** modèle, un split et la liste des items exclus (§ 8.4). Les exécutions portant sur un item d'un autre split, ou sur un item exclu, sont ignorées. Les agrégats du `test` sont ceux du rapport ; ceux du `dev` ne servent qu'à itérer (§ 8).

On note X l'ensemble des exécutions retenues. Une moyenne se calcule sur les exécutions où la valeur n'est pas nulle, un booléen comptant 1 pour vrai et 0 pour faux. Elle vaut `null` s'il n'y a aucune telle exécution.

| Clé | Définition |
|---|---|
| `n_executions` | \|X\| |
| `correct` | moyenne de `correct` sur X |
| `correct_answerable` | moyenne de `correct` sur les exécutions de X portant sur un item avec réponse |
| `false_abstention_rate` | moyenne de `false_abstention` |
| `hallucination_rate` | moyenne de `hallucination` |
| `error_rate` | part des exécutions de X dont `error` n'est pas nul |
| `evidence_recall@k`, `all_evidence@k`, `all_evidence`, `context_size` | moyenne de la métrique |
| `failure` | objet `{correct, retrieval_miss, generation_miss, error}` : part de chaque valeur parmi les exécutions où `failure` n'est pas nul, ou `null` s'il n'y en a aucune |
| `premise` | objet `{corrected, unresolved, adopted, missed}`, même règle |
| `correct_by_mode` | objet qui associe à chaque `mode` présent dans X la moyenne de `correct` sur ses exécutions |
| `tokens_mean` | moyenne de `input_tokens + output_tokens` |
| `cost_usd_mean` | moyenne de `cost_usd`, c'est-à-dire le coût par question |
| `latency_s_median`, `latency_s_p95` | centiles 0,5 et 0,95 de `latency_s` |
| `tool_calls_mean` | moyenne de `tool_calls` |

Les cinq dernières clés ne sont calculées que si la valeur n'est nulle pour aucune exécution de X. Sinon, elles valent `null` : une moyenne sur une partie des exécutions seulement serait biaisée.

**Centile.** Le centile q d'une série triée x₁ ≤ … ≤ xₙ est obtenu par interpolation linéaire entre les rangs : h = (n − 1) × q, puis x₍⌊h⌋₊₁₎ + (h − ⌊h⌋) × (x₍⌊h⌋₊₂₎ − x₍⌊h⌋₊₁₎). C'est la méthode 7 de Hyndman et Fan, la méthode par défaut de NumPy et de R. La médiane est le centile 0,5.

**Coût et latence.** Le coût en dollars se compare d'un fournisseur à l'autre ; les tokens, jamais. La latence ne se compare qu'entre variantes mesurées de la même façon, sur la même machine et sur la même période.

## 8. Comparaison et verdict

On compare une variante B à une baseline A, avec un même modèle, sur les mêmes items **du split `test`**, chaque item étant exécuté k fois par variante.

Les items `dev` sont exclus du calcul. Leurs résultats peuvent figurer dans le rapport, dans une section séparée et signalée comme telle, mais ils ne portent jamais le verdict. Les résultats détaillés des items `test` (échecs item par item) ne se consultent pas avant le run final. Pour itérer sur le `dev`, on applique les mêmes calculs aux items `dev`, et le rapport le signale.

### 8.1 Comparaison sur une métrique

Elle porte sur une métrique m de l'exécution, avec un **sens** fixé avant le run : `higher_better` ou `lower_better`. Les métriques admises sont les métriques numériques ou booléennes du § 6, ainsi que `tool_calls`, `latency_s` et `cost_usd`. Un booléen compte 1 pour vrai et 0 pour faux.

1. Pour chaque item i et chaque variante V : pᵢ(V) = moyenne de m sur les exécutions de V pour l'item i où m n'est pas nul. Si m est nul pour toutes ces exécutions, pᵢ(V) n'est pas défini.
2. On garde les items du split où pᵢ(A) et pᵢ(B) sont tous deux définis. n est leur nombre.
3. Différence appariée : dᵢ = pᵢ(B) − pᵢ(A).
4. **Delta** = moyenne des dᵢ. **IC à 95 %** = delta ± t(0,975 ; n−1) × s(d) / √n, où s est l'écart-type empirique (dénominateur n − 1).
5. **Verdict**, avec une règle fixée avant le run :
   - B **s'améliore** si borne basse > 0 (`higher_better`) ou borne haute < 0 (`lower_better`) : verdict `b_better` ;
   - B **se dégrade** si borne haute < 0 (`higher_better`) ou borne basse > 0 (`lower_better`) : verdict `b_worse` ;
   - sinon : `inconclusive`.

Si n < 2, le delta, l'IC et le verdict valent `null`, et seul n est publié.

**Critère principal.** Sauf protocole contraire, le verdict d'une étape est celui de `correct`, en `higher_better`. Comme `correct` n'est jamais nul, une exécution en erreur compte comme une réponse fausse.

**Métriques secondaires.** Elles suivent le même calcul. Une métrique nulle en cas d'erreur, comme `hallucination`, ne compte que les exécutions notées. Quand une métrique est nulle pour toute la baseline (par exemple les métriques de contexte d'une variante sans récupération), n vaut 0, et on publie la valeur de B seule (§ 7), sans delta.

### 8.2 Verdict à deux critères

Un protocole peut juger un levier sur deux critères. Le **critère principal** est la métrique que le levier doit améliorer. La **garde** est une métrique qui ne doit pas se dégrader au-delà d'une **marge** m ≥ 0, exprimée dans l'unité de la métrique. Exemple de l'étape 5 de la 002 : le critère principal est `hallucination` (`lower_better`), la garde est `false_abstention` (`lower_better`), et la marge vaut 0,03.

Le protocole fixe, avant le run, les deux métriques, leur sens et la marge. Chacune est comparée selon le § 8.1. Ensuite :
- la garde **tient** si borne haute < m (`lower_better`) ou borne basse > −m (`higher_better`) ;
- la garde est **franchie** si borne basse > m (`lower_better`) ou borne haute < −m (`higher_better`).

| Verdict | Condition, évaluée dans cet ordre |
|---|---|
| `b_worse` | le critère principal se dégrade, ou la garde est franchie |
| `b_better` | le critère principal s'améliore, et la garde tient |
| `tradeoff` | le critère principal s'améliore, mais la garde ne tient pas sans être franchie |
| `inconclusive` | sinon |

Si l'une des deux comparaisons a n < 2, le verdict vaut `null`.

Une garde exactement à la marge ne tient pas, et n'est pas franchie. En `lower_better`, avec une borne haute égale à m, le verdict ne peut pas être `b_better` : il vaut `tradeoff` si le critère principal s'améliore.

### 8.3 Comparaisons multiples

Quand un rapport porte plusieurs comparaisons, la chance qu'au moins une soit concluante par hasard augmente. Le protocole fixe donc, avant le run, une **famille** de comparaisons (par exemple, les six comparaisons de `correct` d'un même modèle), et un seuil α, qui vaut 0,05 sauf protocole contraire.

**p-value.** Chaque comparaison du § 8.1 publie la p-value bilatérale du test t apparié, celui dont l'IC du § 8.1 est l'inversion : t = delta / (s(d) / √n), puis p = 2 × (1 − F(\|t\|)), où F est la fonction de répartition de Student à n − 1 degrés de liberté.
- Sans dispersion (s(d) = 0) : p vaut 1 si le delta est nul, 0 sinon.
- Si n < 2 : p vaut `null`.

**Ajustement de Holm.** Soit m le nombre de comparaisons de la famille. Une p-value nulle compte pour 1 dans le calcul : la famille garde sa taille, et la correction ne s'allège pas. On trie les p-values par ordre croissant, p₍₁₎ ≤ … ≤ p₍ₘ₎. La p-value ajustée de rang j vaut :

p̃₍ⱼ₎ = max sur l ≤ j de min(1, (m − l + 1) × p₍ₗ₎)

Chaque comparaison reprend la p-value ajustée de son rang. Une comparaison dont la p-value est nulle a une p-value ajustée nulle. Des p-values égales reçoivent la même valeur ajustée, quel que soit l'ordre entre elles.

**Verdict corrigé (`verdict_holm`).**
- Si p̃ < α, le verdict est `b_better` ou `b_worse`, selon le signe du delta et le sens de la métrique (§ 8.1).
- Sinon, il vaut `inconclusive`, ou `null` si p̃ est nul.

Le protocole dit lequel porte le verdict de l'étape : celui du § 8.1 ou le verdict corrigé. L'autre est publié à côté.

### 8.4 Items exclus

Le protocole peut exclure des items, par exemple ceux qu'un audit du golden set trouve défectueux. La liste est fixée au commit de gel, avant le run `test`, avec le motif de chaque exclusion. Un item ne s'exclut jamais après lecture des résultats du `test`.

Les items exclus sont retirés de tous les calculs des § 7 et § 8, avant toute autre opération. Le rapport publie leur liste. Le golden set, lui, ne change pas : la correction d'un item défectueux passe par une nouvelle version.

### 8.5 Taille du golden set

Ce n'est pas cette spec qui la fixe. Le protocole de chaque expérience la justifie avant le run, par un calcul d'effet minimal détectable : MDE = (t₀,₉₇₅ + t₀,₈₀) × s_d / √n, avec une puissance de 80 %. Quand le verdict corrigé du § 8.3 porte le verdict, le quantile t₀,₉₇₅ est remplacé par celui du seuil le plus exigeant de Holm, t(1 − α / (2m)). On n'utilise jamais moins de 30 items `test`.

## 9. Conformance

`conformance.jsonl` contient six types de vecteurs :
- `"kind": "execution"` : un item valide selon `golden.schema.json`, une exécution valide selon `execution.schema.json`, et les métriques attendues (§ 6) ;
- `"kind": "aggregate"` : des séries de pᵢ(A) et pᵢ(B) avec leur split, accompagnées du delta, des bornes de l'IC et du verdict de `correct` attendus (§ 8.1, étapes 3 à 5). C'est le type de la v1, repris tel quel ;
- `"kind": "variant"` : des items, les exécutions d'une variante et un split, accompagnés des agrégats attendus (§ 7) ;
- `"kind": "comparison"` : des items, les exécutions de A et de B, une métrique, son sens, un split et les items exclus, accompagnés de n, du delta, des bornes de l'IC, du verdict et de la p-value attendus (§ 8.1, § 8.3) ;
- `"kind": "joint"` : des items, les exécutions de A et de B, les deux critères, leur sens, la marge, un split et les items exclus, accompagnés des deux comparaisons et du verdict attendus (§ 8.2) ;
- `"kind": "family"` : une famille de comparaisons, chacune donnée par ses séries de pᵢ(A) et pᵢ(B), son split et son sens, et un seuil α, accompagnés pour chaque comparaison de la p-value, de la p-value ajustée et du verdict corrigé attendus (§ 8.3).

Les vecteurs `variant`, `comparison` et `joint` partent des exécutions, et non de pᵢ déjà calculés : ils vérifient aussi la moyenne par item, le traitement des valeurs nulles et l'exclusion d'items.

Une implémentation est conforme si elle reproduit exactement les entiers, les booléens, les chaînes et les `null`, et les nombres réels à 1e-9 près.

```json
{"id": "cv-001", "kind": "execution", "covers": ["réponse juste"], "description": "…",
 "item": {…item valide selon golden.schema.json…},
 "execution": {…exécution observée, forme canonique du § 3.2…},
 "expected": {"correct": true, "facts_found": 1, "facts_attached": null, "premise": null,
              "false_abstention": false, "hallucination": null,
              "evidence_recall@1": 1.0, "…": "…", "failure": "correct",
              "citation_precision": 1.0, "citation_recall": 1.0}}
```

`covers` relie chaque vecteur aux cas à couvrir ci-dessous, et un test vérifie que chaque cas en a au moins un.

Les vecteurs de la v1 sont repris sous le même `id`, avec le même item. Leur exécution est complétée des champs nouveaux à `null`, et leurs métriques attendues des métriques nouvelles. Un vecteur dont une métrique v1 change porte un champ `v1_change`, qui explique l'écart. Un test vérifie que tout autre vecteur repris garde les métriques v1 attendues.

Cas à couvrir au minimum. Les noms ci-dessous sont ceux du champ `covers`, mot pour mot ; le test des fichiers de la spec en garde la même liste.

- **réponse** : `réponse juste` ; `fait manquant` ; `un fait retrouvé sur deux` ; `plusieurs formes acceptées` ; `abstention sur un item avec réponse` ; `abstention qui l'emporte sur une réponse juste` ; `abstention juste sur un item sans réponse` ; `hallucination` ; `réponse vide` ; `erreur d'exécution`
- **normalisation** : `normalisation : casse` ; `normalisation : accents` ; `normalisation : apostrophe typographique` ; `normalisation : espace insécable` ; `normalisation : espaces entre chiffres` ; `normalisation : espace avant %` ; `normalisation : espace avant €` ; `normalisation : ligature` ; `délimitation : 114 jours` ; `délimitation : 14 joursx` ; `délimitation : début de réponse` ; `délimitation : fin de réponse` ; `délimitation : ponctuation`
- **mots-clés (§ 5.2)** : `mots-clés : dans la fenêtre` ; `mots-clés : fenêtre dépassée d'un mot` ; `mots-clés : ordre inverse` ; `mots-clés : mot fléchi` ; `mots-clés : mot coupé par une apostrophe` ; `mots-clés : fenêtre nulle`
- **rattachement (§ 5.3)** : `rattachement : deux phrases` ; `rattachement : deux propositions` ; `rattachement : phrase à une seule ancre malgré « et »` ; `rattachement : inversion entre deux phrases` ; `rattachement : inversion dans une phrase` ; `rattachement : valeur sans ancre` ; `rattachement : abréviation L. 242-14` ; `rattachement : facts_attached partiel`
- **prémisse (§ 5.4)** : `prémisse : vraie valeur seule` ; `prémisse : et non` ; `prémisse : marqueur à 6 mots` ; `prémisse : marqueur à 7 mots` ; `prémisse : marqueur de plusieurs mots` ; `prémisse : fausse valeur seule` ; `prémisse : ni l'une ni l'autre` ; `prémisse : une occurrence non marquée sur deux` ; `prémisse : abstention qui l'emporte`
- **contexte** : `contexte nul` ; `contexte plus court que k` ; `article attendu au rang 1` ; `article attendu au rang 4` ; `article attendu absent` ; `un article attendu sur deux` ; `retrieval_miss` ; `generation_miss` ; `erreur avec contexte` ; `contexte avec doublon`
- **variante agentique** : `agentique : un appel` ; `agentique : plusieurs appels` ; `agentique : aucun appel`
- **citations** : `citation : Article L. 221-18` ; `citation : art. L. 221-18` ; `citation : L221-18` ; `citation : l. 221-18` ; `citation en double` ; `aucune citation` ; `citation fausse` ; `citation : plage dans un seul élément`
- **verdict (`aggregate`)** : `B meilleure` ; `B moins bonne` ; `non concluant` ; `items dev ignorés` ; `IC nul`
- **agrégats (§ 7)** : `agrégats : autre split ignoré` ; `agrégats : moyenne sans valeur` ; `agrégats : répartition de failure` ; `agrégats : répartition de premise` ; `agrégats : deux modes` ; `agrégats : centiles sur un nombre pair` ; `agrégats : centiles sur un nombre impair` ; `agrégats : champ manquant` ; et chaque clé du § 7 non nulle dans au moins un vecteur.
- **comparaison (§ 8.1)** : `comparaison : lower_better qui s'améliore` ; `comparaison : lower_better qui se dégrade` ; `comparaison : k > 1 répétitions` ; `comparaison : répétition en erreur ignorée` ; `comparaison : répétition en erreur comptée fausse` ; `comparaison : item sans valeur écarté` ; `comparaison : baseline sans valeur` ; `comparaison : un seul item` ; `comparaison : autre split ignoré`
- **verdict à deux critères (§ 8.2)** : `verdict joint : b_better` ; `verdict joint : b_worse par le critère principal` ; `verdict joint : b_worse par la garde` ; `verdict joint : tradeoff` ; `verdict joint : inconclusive` ; `verdict joint : garde à la marge` ; `verdict joint : garde higher_better` ; `verdict joint : n < 2`
- **comparaisons multiples (§ 8.3)** : `holm : p-value` ; `holm : sans dispersion, delta nul` ; `holm : sans dispersion, delta non nul` ; `holm : plafond à 1` ; `holm : maximum cumulé` ; `holm : p-values égales` ; `holm : comparaison à n < 2` ; `holm : b_worse en lower_better` ; `holm : concluant avant correction seulement`
- **items exclus (§ 8.4)** : `exclusion : agrégats` ; `exclusion : comparaison` ; `exclusion : verdict joint`

## 10. Contenu d'un rapport

Chaque rapport doit citer :
- la version de cette spec, celle du golden set et celle des données du domaine ;
- le modèle et sa configuration (température, format de sortie imposé, raisonnement activé ou non) ;
- n (items `test`), le nombre d'items `dev`, et k ;
- les lockfiles (`uv.lock`, et ceux du build Java quand le scorer Java a servi) ;
- pour `correct` : la valeur de A, celle de B, le delta, son IC et le verdict ;
- quand le § 8.2 s'applique : les deux critères, leur sens, la marge, et le verdict à deux critères ;
- quand le § 8.3 s'applique : la famille, α, la p-value, la p-value ajustée et le verdict corrigé de chaque comparaison, et lequel des deux verdicts porte celui de l'étape ;
- la liste des items exclus et le motif de chaque exclusion (§ 8.4) ;
- les agrégats du § 7 pour chaque variante ;
- quand `cost_usd` est publié : le barème utilisé, sa source et sa date, et la liste des appels comptés ;
- quand `latency_s` est publié : ce que mesure la durée, la machine et la période du run.
