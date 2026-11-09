# 006 — Renforcer la consigne d'abstention ?

> **Statut :** gelée le 2026-11-09, run final en cours
> **Domaines :** [`droit-consommation`](../../domains/droit-consommation/README.md)
> **Spec de notation :** [`rag-qa/v1`](../../evals/spec/rag-qa/v1/SPEC.md) (publiée)
> **Golden set :** [`rag-qa/v3`](../../domains/droit-consommation/golden/rag-qa/README.md#v3--plus-de-questions-sans-réponse-dans-le-test-2026-11-09)

Cinquième expérience de la série « notre RAG répond mal, quels sont les plus gros leviers ? ». Les 004 et 005 ont agi sur la récupération ; aucune n'a fait moins inventer les modèles sur les questions auxquelles le code ne répond pas. Avec 20 passages, Mistral Small et Ministral 14B inventent encore une réponse à environ trois questions sans réponse valides sur dix (0,30 et 0,27 au `test` de la 005, sur 11 items valides seulement). La 006 teste un levier de génération : une consigne d'abstention plus exigeante.

Les sections Question, Hypothèse, Protocole, Discipline d'itération et Mesures sont écrites avant le premier run.

## Pourquoi un nouveau golden set

L'audit des questions sans réponse de la v1 (2026-11-09) a montré que 12 des 23 questions sans réponse du `test` ont en fait une réponse dans le code : sur elles, un modèle qui répond juste est compté comme ayant inventé, ce qui récompense l'abstention. Il ne restait que 11 questions sans réponse valides : même parfaite, une consigne d'abstention n'aurait pu faire gagner que 2 à 3 points de `correct`. La v2 a porté le `dev` à 30 questions sans réponse, la v3 le `test` à 51 questions sans réponse valides ([README du golden set](../../domains/droit-consommation/golden/rag-qa/README.md)).

## Question

Sur le Code de la consommation, **une consigne qui demande de vérifier qu'un extrait donne exactement la valeur demandée, pour la situation de la question,** fait-elle baisser les réponses inventées aux questions sans réponse, sans faire augmenter les abstentions à tort sur les questions qui ont une réponse, à générateur constant ?

## Hypothèse

- **H1 :** B invente moins que A sur les questions sans réponse valides, et ne s'abstient pas à tort plus souvent que A de plus de 3 points sur les questions avec réponse.
- **H0 :** pas de baisse mesurable des réponses inventées.
- **Plus petite baisse qui compte : 10 points de `hallucination`.** En dessous, le changement de prompt ne change pas l'expérience d'un utilisateur qui pose une question hors du code.
- **Hausse tolérée des abstentions à tort : 3 points au plus.** Au-delà, la consigne fait perdre des réponses justes à des utilisateurs dont la question a une réponse.

**Attentes secondaires**, qui ne portent pas le verdict : `correct` stable ou en hausse sur les items valides ; effet plus faible pour Gemini Flash-Lite, qui invente déjà peu (0,09) ; tokens quasi identiques (une phrase de plus).

## Protocole

| Élément | Valeur |
|---|---|
| Baseline (A) | Le **RAG à 20 passages de la 004**, gelé : un passage par article, texte seul indexé, `mistral-embed`, cosinus exact, top-k = 20, prompts du gel de la 002 |
| Variante (B) | A, avec une **phrase d'ancrage plus exigeante** (point de départ ci-dessous, mis au point en 2 cycles au plus) |
| Ce qui change entre A et B | La phrase d'ancrage du message (`GROUNDING`), et elle seule |
| Ce qui est fixé | Le générateur, le prompt système, le format de sortie, la température (0), l'index, la recherche, le nombre de passages, les données (`data/v1`) |
| Générateurs | Un verdict par modèle : `mistral:mistral-small-2603`, `mistral:ministral-14b-2512`, `google:gemini-3.5-flash-lite`, ceux des 002 à 005. Identifiants vérifiés le 2026-11-09 (API Mistral `/v1/models`, API Google `v1beta/models`) |
| Golden set | `domains/droit-consommation/golden/rag-qa/v3` : `dev` 74 items (30 sans réponse, dont 28 valides) ; `test` 190 items (178 valides, dont 51 sans réponse et 127 avec réponse) |
| Items écartés | Les 14 items sans réponse que l'audit de la v1 trouve répondus par le code (`golden/rag-qa/audit/v1-unanswerable.jsonl`) : 12 au `test`, 2 au `dev` (`rq-129`, `rq-146`). Ils sont écartés de toutes les mesures, et ne sont pas lus pendant l'itération |
| Répétitions | k = 3 |
| Implémentation | `python/`, sur les briques partagées `ailab_rag` |

**Point de départ de B** (phrase d'ancrage, avant cycle) : la phrase d'ancrage de A, plus « Avant de répondre, vérifie qu'un extrait donne exactement la valeur demandée, pour la situation de la question. Un extrait sur un cas voisin (autre acteur, autre procédure, autre contrat) ne suffit pas : mets alors `abstained` à vrai. » Elle vise l'échec observé au run 0 du `dev` de la 005 (`rq-146`, un plafond d'amende voisin repris comme réponse) ; elle n'a été écrite à partir d'aucun item du `test`.

**Taille de l'échantillon.** Critère principal : 51 items, avec un écart type de la différence par item supposé de 0,45 (à estimer au run 0) : MDE ≈ (2,01 + 0,85) × 0,45 / √51 ≈ **18 points**, au-dessus des 10 points qui comptent. **Une baisse modeste peut passer inaperçue.** Garde : 127 items, abstentions à tort rares (1 à 9 % pour A dans la 005) : l'intervalle sera étroit. Gemini Flash-Lite part de 0,09 : une baisse de 10 points lui est presque impossible (effet plancher). Écrit avant le premier run. **Mesuré au run 0 du `dev` : s_d = 0,192**, soit un MDE d'environ 8 points sur les 51 questions du `test`, sous les 10 points qui comptent.

**Lancer un run** (depuis `python/`) :

```sh
uv run --env-file ../../../.env python -m exp006_rag.campaign \
    --split dev --model mistral:mistral-small-2603 --k 3 --run-dir ../runs/<nom>
```

Les items écartés par l'audit ne tournent pas. Le run final ajoute `--split test --final --langfuse` et refuse de partir si l'arbre git n'est pas propre ; le `summary.json` donne le verdict à deux critères dans `abstention`.

## Discipline d'itération

1. **Même effort pour chaque variante.** A est le RAG à 20 passages de la 004 : deux cycles reçus dans la 002, aucun dans la 004. B a droit à 2 cycles sur le `dev`. A ne change pas.
2. **Gel avant le run final**, puis **un seul run sur le `test`**. Un run raté pour une raison technique se relance en entier, et l'incident est noté dans les Limites.
3. **Le `test` n'inspire pas la consigne.** L'audit de la v1 et la relecture de la v3 ont lu des questions du `test` (leur contenu, pas des réponses de modèle) ; la consigne de B ne s'écrit qu'à partir du `dev`.

**Budget d'itération :** A, 2 cycles reçus, gelé ; B, N = 2 cycles sur le `dev`, avec Mistral Small. Un cycle est mesuré avec les deux critères du verdict, sur les 28 questions sans réponse valides et les 44 questions avec réponse du `dev`.

**Journal d'itération**, sur le `dev` uniquement (Mistral Small, k = 3) :

| # | Date | Variante | Modification | Motif | `hallucination` dev (valides) | `false_abstention` dev |
|---|---|---|---|---|---|---|
| 0 | 2026-11-09 | A et B | aucune : mesure de départ, B avec le point de départ (commit `4ae9382`, sans Langfuse) | vérifier la chaîne, estimer s_d | A 0,238 · B 0,226 ; delta −0,012 [−0,086 ; +0,063]. s_d = 0,192. Les réponses inventées sont des règles d'un cas voisin appliquées au mauvais cas (frais de dossier d'un crédit immobilier pour un produit à distance, corps huit du crédit pour la multipropriété, même moyen de paiement hors services financiers) : la consigne ne les arrête pas | A 0,015 · B 0,045 ; delta +0,030 [−0,018 ; +0,078] (2 items : une référence, une paraphrase) |
| 1 | 2026-11-09 | B seulement (phrase d'ancrage) ; A garde ses exécutions du run 0 | « La valeur doit valoir pour la situation exacte de la question : même type de contrat ou de produit, même professionnel, même étape… » avec deux exemples tirés des échecs du run 0 (commits `d0a0a3b`, `fa5edcd`) | Au run 0, les réponses inventées appliquaient la règle d'un cas voisin | A 0,238 · B 0,238 ; delta 0,000 [−0,093 ; +0,093]. Seul `rq-223`, l'un des deux exemples, est corrigé ; `rq-219` et `rq-203` empirent | A 0,015 · B 0,061 ; delta +0,045 [−0,006 ; +0,097] (3 items : deux paraphrases, une référence). `correct` 0,843 → 0,815 |

**Règle de gel** (fixée le 2026-11-09, après le cycle 1 et avant tout run sur le `test`) : B est gelée sur la version qui a le meilleur verdict à deux critères au `dev`. Le run 0 (−0,012 de réponses inventées, +0,030 d'abstentions à tort) est meilleur que le cycle 1 (0,000 et +0,045) : **B est gelée sur le point de départ**, sans le cycle 1.

**Arrêt de l'itération** (décision du propriétaire, 2026-11-09) : le cycle 2 n'est pas utilisé. Au `dev`, demander plus de prudence fait s'abstenir Mistral Small sur des questions qui ont une réponse sans l'arrêter sur les autres ; un troisième essai sur 28 questions aurait surtout ajusté B au `dev`. Budget utilisé : 1 cycle sur 2.

**Commit de gel :** le commit « Geler la 006 avant le run final sur le test » (2026-11-09). Son hash est enregistré dans le `summary.json` de chaque run (`run.commit`).

**Configuration gelée :** A, le RAG à 20 passages de la 004, inchangé ; B, A avec la phrase d'ancrage du point de départ (`exp006_rag.campaign.STRICT_GROUNDING`, identique au run 0 du `dev`, commit `4ae9382`).
**Run final sur le `test` :** à venir

## Mesures

Écart à la règle de verdict de la spec (§ 8), qui ne regarde que `correct`, fixé le 2026-11-09 avant tout run par décision du propriétaire : avec 29 % de questions sans réponse au `test` de la v3, `correct` calculé sur tout le `test` donnerait plus de poids à l'abstention qu'un usage réel ; une pondération reprenant la proportion de la v1 (85/15) n'en refléterait pas davantage l'usage.

- **Critère principal :** delta apparié de `hallucination` (B − A), par item, sur les 51 questions sans réponse valides du `test` ; IC 95 % de Student, comme la spec (§ 8).
- **Critère de garde :** delta apparié de `false_abstention` (B − A), sur les 127 questions avec réponse du `test`.
- **Règle conjointe**, par générateur :
  - **B meilleure** : borne haute du critère principal sous 0, et borne haute de la garde sous +0,03 ;
  - **B moins bonne** : borne basse du critère principal au-dessus de 0 (B invente davantage), ou borne basse de la garde au-dessus de +0,03 ;
  - **compromis** : borne haute du critère principal sous 0, mais garde non tenue (borne haute au-dessus de +0,03) sans être franchement dépassée ;
  - **non concluant** sinon.
- **Métriques secondaires, publiées sans porter le verdict :** `correct` sur les 178 items valides, `correct` sur les 150 items `test` de la v1 (comparaison avec les 002 à 005), `correct` sur les items avec réponse, `correct` par mode, répartition de `failure`, citations, tokens et temps de génération.

## Résultats

À venir.

## Verdict

À venir.

## Limites

Déjà connues avant le run :
- **Version de B choisie au `dev` entre deux versions** (run 0 et cycle 1) : un peu optimiste.
- **B, telle que gelée, ne faisait pas mieux que A au `dev`** pour Mistral Small (verdict non concluant) : le run final mesure surtout si la consigne agit sur les deux autres générateurs et sur un `test` plus large.
- **Puissance limitée sur le critère principal** (voir Taille de l'échantillon), et effet plancher pour Gemini Flash-Lite.
- **Questions sans réponse relues par des relecteurs IA**, arbitrées par le propriétaire sur des propositions réunies en une page : il peut rester des questions auxquelles le code répond.
- **Le `test` de la v3 a été lu pendant sa construction** (audit, relecture) ; la consigne de B ne s'appuie que sur le `dev`.
- **Les limites de la 002 s'appliquent** : un seul corpus, questions rédigées par un LLM.
