# Spec de notation — famille `tool-selection`, v1

> **Statut : brouillon.** Cette version n'est pas encore publiée et peut donc changer. Elle sera figée dès qu'un rapport de `results/` la citera ; toute correction passera ensuite par une `v2`.

## 1. Objet

Cette spec note **les appels d'outils** qu'un modèle effectue pour répondre à une question, en les comparant aux appels attendus. Elle ne note pas la réponse finale rédigée par le modèle.

Les scorers Java et Python l'implémentent tous les deux et doivent passer tous les vecteurs de `conformance.jsonl` (§ 8).

## 2. Vocabulaire

| Terme | Définition |
|---|---|
| **Item** | Une question du golden set |
| **Variante** | Une configuration testée, par exemple `intent` ou `rest` |
| **Exécution** | Une tentative de réponse du modèle à un item, pour une variante et un modèle donnés |
| **Appel observé** | Un appel d'outil effectivement émis par le modèle : `{"tool": str, "args": object}` |
| **Motif d'appel** | La description d'un appel acceptable : un nom d'outil et des contraintes sur ses arguments (§ 4) |
| **Appel requis** | Un motif qui doit être satisfait pour que l'item soit réussi |
| **Appel toléré** | Un motif qui n'est pas exigé, mais qui n'est pas pénalisé s'il apparaît |

## 3. Entrées

### 3.1 Item du golden set

Fichier `items.jsonl`, un objet par ligne, validé par `golden.schema.json` :

```json
{
  "id": "ts-001",
  "split": "test",
  "question": "Le casque Veldric K8 est en rupture ici, tu as un équivalent dispo ?",
  "context": {"storeId": "S02"},
  "tags": ["alternative"],
  "expected": {
    "intent": {
      "required": [
        {"tool": "find_in_stock_alternative", "args": {"sku": ["P-15695"], "storeId": ["S02"]}}
      ],
      "tolerated": []
    },
    "rest": {
      "required": [
        {"tool": "get_similar", "args": {"sku": ["P-15695"]}},
        {"tool": "get_stock", "args": {"sku": ["P-26361", "P-44671"], "storeId": ["S02"]}}
      ],
      "tolerated": [
        {"tool": "get_product", "args": {"sku": ["P-15695"]}}
      ]
    }
  }
}
```

- `split` vaut `dev` ou `test`. Le générateur l'attribue de façon seedée, stratifiée par intention (tag), et il ne change jamais une fois le golden set publié. Les items `dev` servent à itérer, par exemple sur les descriptions d'outils. Les items `test` portent seuls le verdict (§ 7).
- `context` est transmis au modèle avec la question. Le protocole de l'expérience précise sous quelle forme.
- Les listes de valeurs acceptables qui dépendent des données (par exemple les alternatives valides) sont **calculées par le générateur du domaine** à partir des règles métier. Elles ne sont jamais écrites à la main.

### 3.2 Exécution observée

C'est la forme canonique, utilisée aussi par les vecteurs de conformance et les rapports :

```json
{
  "item_id": "ts-001",
  "variant": "rest",
  "model": "<fournisseur>/<modèle>",
  "repeat": 0,
  "calls": [
    {"tool": "get_similar", "args": {"sku": "P-15695"}},
    {"tool": "get_stock", "args": {"sku": "P-26361", "storeId": "S02"}}
  ],
  "usage": {"input_tokens": 1234, "output_tokens": 210},
  "error": null
}
```

`calls` suit l'ordre d'émission. Il contient **tous** les appels émis, y compris ceux que le serveur a rejetés (outil inconnu, arguments invalides).

## 4. Correspondance entre un appel observé et un motif

Un appel observé **satisfait** un motif si et seulement si les trois conditions suivantes sont réunies :

1. `tool` est identique au nom d'outil du motif. La comparaison est sensible à la casse et se fait sans normalisation.
2. Chaque argument du motif est présent dans l'appel, et sa valeur est **égale** (§ 5) à l'une des valeurs acceptables du motif.
3. L'appel ne contient **aucun argument absent du motif**. Un argument halluciné est une erreur.

**Arguments facultatifs.** Un motif peut déclarer `"optional": {"category": ["audio"]}`. Un argument facultatif peut être omis ; s'il est présent, sa valeur doit être acceptable.

**Argument non contraint.** À la place d'une liste, on peut écrire `{"any": true}` : l'argument doit être présent, mais n'importe quelle valeur est acceptée. Cette forme est réservée au texte libre, par exemple une requête de recherche. Le rapport indique combien d'arguments non contraints compte le golden set.

## 5. Égalité de deux valeurs

| Type | Règle |
|---|---|
| Chaîne | Égales après normalisation Unicode NFC, suppression des espaces en début et en fin, puis *casefold*. Aucune autre transformation. Les serveurs normalisent leurs identifiants (casse, espaces) : `p-15695` équivaut donc à `P-15695`, mais `P-1569` reste faux. |
| Nombre | Égalité numérique : `2` égale `2.0`. Une chaîne n'est jamais égale à un nombre : `"2"` diffère de `2`. |
| Booléen, `null` | Égalité stricte |
| Liste | Même longueur, éléments égaux deux à deux, dans le même ordre |
| Objet | Mêmes clés, valeurs égales récursivement |

## 6. Métriques par exécution

On note R le nombre d'appels requis et O le nombre d'appels observés.

1. **Classement des appels observés.** Un appel qui satisfait un motif toléré est classé *toléré*. Pour que ce classement soit sans ambiguïté, le golden set ne doit pas contenir d'item où un même outil serait à la fois requis et toléré ; le schéma le vérifie.
2. **Couplage complet** : le couplage maximum entre les motifs requis et les appels observés non tolérés. Une arête relie un motif et un appel quand l'appel satisfait le motif (§ 4). On note **M** sa cardinalité. Quel que soit l'algorithme utilisé, la cardinalité d'un couplage maximum est la même.
3. **Couplage par nom** : on compte, pour chaque outil, le minimum entre le nombre de motifs requis de cet outil et le nombre d'appels observés non tolérés de cet outil, puis on fait la somme. On note **N** ce total.
4. **Appels en trop** : E = appels observés non tolérés − M.

| Métrique | Formule | Remarque |
|---|---|---|
| `tool_recall` | N / R | Le modèle a-t-il appelé les bons outils, quels que soient les arguments ? |
| `args_recall` | M / R | Le modèle a-t-il fait les bons appels, arguments compris ? |
| `precision` | M / (M + E) | `null` si M + E = 0 |
| `extra_calls` | E | |
| `n_calls` | O | Compte aussi les appels tolérés |
| **`success`** | `args_recall == 1` | **Métrique principale.** Les appels en trop sont permis. |
| `strict_success` | `success` et E = 0 | |

**Erreur d'exécution** (exception, délai dépassé, nombre maximal d'étapes atteint) : `success = false`, et l'item **reste compté**. L'exclure biaiserait le résultat en faveur de la variante qui échoue.

**Tokens** : ils ne sont pas notés. On les agrège (moyenne par item de `input_tokens + output_tokens`) et on ne les compare qu'à modèle constant.

## 7. Agrégation et verdict

On compare une variante B à une baseline A, avec un même modèle, sur les mêmes n items **du split `test`**, chaque item étant exécuté k fois par variante.

Les items `dev` sont exclus du calcul. Leurs résultats peuvent figurer dans le rapport, dans une section séparée et signalée comme telle, mais ils ne portent jamais le verdict. Les résultats détaillés des items `test` (échecs item par item) ne se consultent pas avant le run final : sinon, le split `test` devient lui aussi un jeu d'itération.

1. Pour chaque item i : pᵢ(V) = moyenne de `success` sur les k répétitions de la variante V.
2. Différence appariée : dᵢ = pᵢ(B) − pᵢ(A).
3. **Delta** = moyenne des dᵢ. **IC à 95 %** = delta ± t(0,975 ; n−1) × s(d) / √n, où s est l'écart-type empirique (dénominateur n − 1).
4. **Verdict**, avec une règle fixée avant le run :
   - borne basse > 0 : **B meilleure** ;
   - borne haute < 0 : **B moins bonne** ;
   - sinon : **non concluant**.

Les autres métriques (`args_recall`, `tool_recall`, `precision`, `n_calls`, tokens) sont publiées avec le même calcul de delta et d'IC, mais **elles ne portent pas le verdict**.

**Taille du golden set.** Ce n'est pas cette spec qui la fixe. Le protocole de chaque expérience la justifie avant le run, par un calcul d'effet minimal détectable : MDE = (t₀,₉₇₅ + t₀,₈₀) × s_d / √n, avec une puissance de 80 %. L'intervalle de Student n'étant qu'une approximation pour des proportions, on n'utilise jamais moins de 30 items.

## 8. Conformance

`conformance.jsonl` contient deux types de vecteurs :

- `"kind": "execution"` : un item, une exécution observée, et les métriques attendues (§ 6) ;
- `"kind": "aggregate"` : des séries de pᵢ(A) et pᵢ(B) avec leur split, accompagnées du delta, des bornes de l'IC et du verdict attendus. Au moins un vecteur mélange des items `dev` et `test`, pour vérifier que les `dev` sont bien ignorés.

Une implémentation est conforme si elle reproduit exactement les entiers, les booléens et les verdicts, et les nombres réels à 1e-9 près.

Les cas à couvrir au minimum : appel parfait ; outil faux ; argument faux ; argument halluciné ; argument facultatif omis ; argument facultatif présent mais faux ; argument non contraint ; appel requis manquant ; appel en double ; appel toléré ; outil inconnu ; erreur d'exécution ; aucun appel ; plusieurs motifs du même outil dont les valeurs acceptables se recouvrent ; égalités de chaînes (casse, espaces, NFC ; `P-15695` contre `p-15695` contre `P-1569`) ; `2` contre `2.0` contre `"2"`.

## 9. Contenu d'un rapport

Chaque rapport doit citer :
- la version de cette spec et celle du golden set ;
- le modèle et sa configuration (température, nombre maximal d'étapes) ;
- n (items `test`), le nombre d'items `dev`, et k ;
- les lockfiles (`uv.lock`, catalogue de versions Gradle) ;
- pour chaque métrique : la valeur de A, la valeur de B, le delta et son IC ;
- le verdict sur `success`.
