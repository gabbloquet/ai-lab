# Spec de notation — famille `rag-qa`, v1

> **Statut : publiée** le 2026-11-07, citée par le [run final de la 002](../../../../experiments/002-rag-naif-vs-modele-seul/results/2026-11-07-run-final-test.md). Elle ne change plus ; toute correction passe par une `v2`.

## 1. Objet

Cette spec note **la réponse** d'un système à une question posée sur un corpus de documents, avec ou sans récupération (RAG). Quand le système fournit un contexte au modèle, elle note aussi ce contexte : y trouvait-on les documents nécessaires ? Elle classe enfin chaque échec, selon qu'il vient de la récupération ou de la génération.

La notation est **déterministe**, sans juge LLM : une réponse est juste si elle contient les faits attendus (§ 5).

Seul un scorer Python l'implémente pour l'instant : une métrique DeepEval personnalisée, dans `evals/python/`. Un scorer dans un autre langage devra passer les mêmes vecteurs de `conformance.jsonl` (§ 9).

## 2. Vocabulaire

| Terme | Définition |
|---|---|
| **Item** | Une question du golden set |
| **Article** | Un document du corpus, identifié par un `id` et cité par son numéro (`num`) |
| **Fait attendu** | Une information courte que la réponse doit contenir, donnée sous une ou plusieurs **formes acceptées** |
| **Item avec réponse** | Item dont le corpus contient la réponse (`answerable: true`) |
| **Item sans réponse** | Item auquel le corpus ne répond pas (`answerable: false`) : la bonne réponse est l'abstention |
| **Variante** | Une configuration testée, par exemple « modèle seul » ou « RAG naïf » |
| **Exécution** | Une tentative de réponse à un item, pour une variante, un modèle et une répétition |
| **Contexte** | Les articles réellement donnés au modèle pour une exécution, dans l'ordre du classement |
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

- `split` vaut `dev` ou `test`. Les items `dev` servent à itérer ; seuls les items `test` portent le verdict (§ 8).
- `mode` dit quel mode d'échec l'item sollicite. Les valeurs possibles sont définies par le golden set du domaine. Le scorer ne s'en sert que pour ventiler les résultats.
- Pour un item avec réponse, `expected.facts` et `expected.articles` contiennent chacun au moins un élément. Pour un item sans réponse, ils sont tous deux vides.
- `evidence` justifie les faits : c'est un extrait copié du corpus. Le golden set le vérifie à sa construction, et le scorer ne le lit pas.
- `source_article`, facultatif, donne l'`id` de l'article à partir duquel un item sans réponse a été construit. Il sert à l'analyse, et le scorer ne le lit pas.

### 3.2 Exécution observée

C'est la forme canonique, utilisée aussi par les vecteurs de conformance et les rapports. Chaque expérience convertit la sortie de son système vers cette forme. Le format que le modèle doit produire est fixé par le protocole de l'expérience, avec une contrainte : il doit permettre de remplir `answer`, `abstained` et `cited`.

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
  "error": null
}
```

| Champ | Type | Règle |
|---|---|---|
| `answer` | chaîne | Réponse rédigée par le modèle. Elle peut être vide |
| `abstained` | booléen | Vrai si le modèle déclare que le corpus ne répond pas à la question |
| `cited` | liste de chaînes | Numéros d'article cités par le modèle, tels qu'il les écrit, **un numéro par élément**. Le format de sortie fixé par le protocole doit l'exiger : une plage ou une liste dans un seul élément (« L. 221-23 à L. 221-25 ») ne correspond à aucun article (§ 6) |
| `context` | liste d'`id`, ou `null` | Articles donnés au modèle, dans l'ordre du classement. Il vaut `null` pour une variante sans récupération. Quand la récupération renvoie des passages, chaque passage est remplacé par l'`id` de son article, et seule la première occurrence d'un article est gardée. Le scorer applique aussi cette règle avant tout calcul |
| `error` | chaîne ou `null` | Non nul en cas d'erreur d'exécution : exception, délai dépassé, ou sortie impossible à lire dans le format fixé par le protocole |

## 4. Normalisation du texte

Les faits sont recherchés dans `answer` (§ 5) après une même normalisation **N**, appliquée à la réponse comme à chaque forme acceptée. Les étapes s'appliquent dans cet ordre :

1. Normalisation Unicode NFC.
2. Les apostrophes `’` (U+2019), `‘` (U+2018) et `ʼ` (U+02BC) deviennent `'` (U+0027).
3. Tout caractère d'espacement Unicode (`str.isspace`, y compris les espaces insécables U+00A0 et U+202F) devient une espace U+0020.
4. *Casefold* Unicode complet.
5. Suppression des accents : décomposition NFD, suppression des marques de catégorie `Mn`, puis recomposition NFC.
6. Les ligatures `œ` et `æ` deviennent `oe` et `ae`.
7. Suppression des espaces situées entre deux chiffres décimaux (`1 500` devient `1500`).
8. Les suites d'espaces sont réduites à une seule, et les espaces en début et en fin sont retirées.

Exemples : N(« Délai de 1 500 €. ») = « delai de 1500 €. », et N(« L’Œuvre ») = « l'oeuvre ».

N ne touche ni à la ponctuation ni aux nombres écrits en lettres. « Quatorze jours » et « 14 jours » sont deux formes distinctes : le golden set doit lister les deux.

## 5. Faits retrouvés et réponse juste

**Fait retrouvé.** Un fait est retrouvé dans une réponse si l'une de ses formes acceptées, une fois normalisée (f = N(forme)), apparaît dans N(`answer`) à une position où elle est **délimitée** :
- le caractère qui précède f, s'il y en a un, n'est pas une lettre ou un chiffre ;
- le caractère qui suit f, s'il y en a un, n'est pas une lettre ou un chiffre.

Est « lettre ou chiffre » tout caractère de catégorie Unicode `L*` ou `N*`. Si f apparaît plusieurs fois, une seule occurrence délimitée suffit. Ainsi, « 14 jours » est retrouvé dans « sous 14 jours. », mais pas dans « 114 jours » ni dans « 14 joursx ».

**Réponse juste (`correct`)**, pour une exécution sans erreur (`error` nul) :

| Item | `correct` vaut vrai si… |
|---|---|
| avec réponse | `abstained` est faux **et** chaque fait attendu est retrouvé |
| sans réponse | `abstained` est vrai |

Une abstention l'emporte sur le texte : si `abstained` est vrai, la réponse est traitée comme une abstention, quel que soit le contenu de `answer`.

**Limite assumée.** La recherche ne détecte pas la négation : « pas 14 jours mais 7 » contient « 14 jours ». Le golden set réduit ce risque en demandant des valeurs, jamais un oui ou un non.

## 6. Métriques par exécution

On note G l'ensemble des `id` de `expected.articles`. Pour un entier k, Cₖ désigne les k premiers éléments de `context`, ou tout `context` s'il en contient moins de k.

| Métrique | Définition | Vaut `null` si… |
|---|---|---|
| **`correct`** | § 5 ; faux en cas d'erreur | jamais |
| `facts_found` | nombre de faits attendus retrouvés, sans tenir compte de `abstained` | l'item est sans réponse |
| `false_abstention` | `abstained` est vrai | l'item est sans réponse, ou il y a une erreur |
| `hallucination` | `abstained` est faux | l'item a une réponse, ou il y a une erreur |
| `evidence_recall@k`, k ∈ {1, 3, 5, 10} | \|G ∩ Cₖ\| / \|G\| | `context` est nul, ou l'item est sans réponse |
| `all_evidence@k`, k ∈ {1, 3, 5, 10} | G ⊆ Cₖ | même condition |
| `context_size` | nombre d'articles distincts de `context` | `context` est nul |
| **`failure`** | voir ci-dessous | l'item est sans réponse, ou `context` est nul |
| `citation_precision` | \|P ∩ E\| / \|P\| (voir ci-dessous) | l'item est sans réponse, ou P est vide |
| `citation_recall` | \|P ∩ E\| / \|E\| | l'item est sans réponse |

**Diagnostic `failure`.** Il classe chaque exécution sur un item avec réponse, quand la variante fournit un contexte :
- `error` si l'exécution a échoué (quand `context` est nul, `failure` reste nul, même en cas d'erreur) ;
- sinon `correct` si la réponse est juste ;
- sinon `generation_miss` si G ⊆ `context` : tout ce qu'il fallait était sous les yeux du modèle ;
- sinon `retrieval_miss` : au moins un article attendu manquait au contexte.

Le diagnostic porte sur le **contexte complet**, c'est-à-dire ce que le modèle a réellement reçu, et non sur un top-k fixe.

**Citations.** Un numéro d'article est normalisé par la fonction **C** :
1. N (§ 4) ;
2. suppression des préfixes `articles`, `article` et `art.` en début de chaîne ;
3. suppression des espaces et des points ;
4. passage en majuscules.

Ainsi, C(« Article L. 221-18 ») = C(« l221-18 ») = « L221-18 ». P est l'ensemble des C(c) pour c dans `cited`, et E l'ensemble des C(`num`) des articles attendus. Les doublons de `cited` ne comptent qu'une fois.

**Erreur d'exécution.** `correct` vaut faux et l'item **reste compté** : l'exclure avantagerait la variante qui échoue. `failure` vaut `error`. Les métriques de contexte se calculent sur le `context` émis avant l'erreur, s'il y en a un. Les métriques de réponse (`facts_found`, citations) se calculent sur les champs reçus.

**Tokens.** Ils ne sont pas notés. On les agrège (moyenne par item de `input_tokens + output_tokens`) et on ne les compare qu'à modèle constant.

## 7. Agrégats par variante

Ces agrégats, calculés sur le `test`, sont publiés sans porter le verdict :
- les moyennes de `correct`, et de `correct` restreint aux items avec réponse ;
- le taux de `false_abstention`, sur les items avec réponse ;
- le taux de `hallucination`, sur les items sans réponse ;
- le taux d'erreur ;
- la moyenne de chaque métrique de contexte, sur les exécutions où elle n'est pas nulle ;
- la **répartition de `failure`** : part de `correct`, `retrieval_miss`, `generation_miss` et `error` ;
- `correct` ventilé par `mode`.

## 8. Comparaison et verdict

On compare une variante B à une baseline A, avec un même modèle, sur les mêmes n items **du split `test`**, chaque item étant exécuté k fois par variante.

Les items `dev` sont exclus du calcul. Leurs résultats peuvent figurer dans le rapport, dans une section séparée et signalée comme telle, mais ils ne portent jamais le verdict. Les résultats détaillés des items `test` (échecs item par item) ne se consultent pas avant le run final.

1. Pour chaque item i : pᵢ(V) = moyenne de `correct` sur les k répétitions de la variante V.
2. Différence appariée : dᵢ = pᵢ(B) − pᵢ(A).
3. **Delta** = moyenne des dᵢ. **IC à 95 %** = delta ± t(0,975 ; n−1) × s(d) / √n, où s est l'écart-type empirique (dénominateur n − 1).
4. **Verdict**, avec une règle fixée avant le run :
   - borne basse > 0 : **B meilleure** ;
   - borne haute < 0 : **B moins bonne** ;
   - sinon : **non concluant**.

Les métriques secondaires suivent le même calcul de delta et d'IC, sur les items où elles ne sont nulles pour aucune des deux variantes. Quand une métrique est nulle pour toute la baseline, par exemple les métriques de contexte d'une variante sans récupération, on publie la valeur de B seule, sans delta.

**Taille du golden set.** Ce n'est pas cette spec qui la fixe. Le protocole de chaque expérience la justifie avant le run, par un calcul d'effet minimal détectable : MDE = (t₀,₉₇₅ + t₀,₈₀) × s_d / √n, avec une puissance de 80 %. On n'utilise jamais moins de 30 items `test`.

## 9. Conformance

`conformance.jsonl` contient deux types de vecteurs :
- `"kind": "execution"` : un item, une exécution observée, et les métriques attendues (§ 6) ;
- `"kind": "aggregate"` : des séries de pᵢ(A) et pᵢ(B) avec leur split, accompagnées du delta, des bornes de l'IC et du verdict attendus.

Une implémentation est conforme si elle reproduit exactement les entiers, les booléens, les chaînes et les `null`, et les nombres réels à 1e-9 près.

```json
{"id": "cv-001", "kind": "execution", "covers": ["réponse juste"], "description": "…",
 "item": {…item valide selon golden.schema.json…},
 "execution": {…exécution observée, forme canonique du § 3.2…},
 "expected": {"correct": true, "facts_found": 1, "false_abstention": false, "hallucination": null,
              "evidence_recall@1": 1.0, "…": "…", "failure": "correct",
              "citation_precision": 1.0, "citation_recall": 1.0}}
```

`covers` relie chaque vecteur aux cas à couvrir ci-dessous, et un test vérifie que chaque cas en a au moins un.

Cas à couvrir au minimum :
- **réponse** : réponse juste ; fait manquant ; un fait retrouvé sur deux ; plusieurs formes acceptées ; abstention sur un item avec réponse ; abstention qui l'emporte sur une réponse juste ; abstention juste sur un item sans réponse ; hallucination ; réponse vide ; erreur d'exécution ;
- **normalisation** : casse ; accents ; apostrophe typographique ; espace insécable ; espaces entre chiffres ; ligature ; délimitation (« 114 jours », « 14 joursx », fait en début et en fin de réponse, fait suivi d'une ponctuation) ;
- **contexte** : `context` nul ; contexte plus court que k ; article attendu au rang 1, au rang 4, absent ; deux articles attendus dont un seul présent ; `retrieval_miss` ; `generation_miss` ; erreur avec contexte ;
- **contexte** (suite) : article en double dans `context` ;
- **citations** : formes « Article L. 221-18 », « art. L. 221-18 », « L221-18 » et « l. 221-18 » ; citation en double ; aucune citation ; citation fausse ; plage dans un seul élément ;
- **verdict** : B meilleure ; B moins bonne ; non concluant ; items `dev` ignorés.

## 10. Contenu d'un rapport

Chaque rapport doit citer :
- la version de cette spec, celle du golden set et celle des données du domaine ;
- le modèle et sa configuration (température, format de sortie imposé) ;
- n (items `test`), le nombre d'items `dev`, et k ;
- les lockfiles (`uv.lock`) ;
- pour `correct` : la valeur de A, celle de B, le delta, son IC et le verdict ;
- les agrégats du § 7 pour chaque variante.
