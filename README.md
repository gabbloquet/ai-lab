<p align="center">
  <img src=".github/assets/banner.svg" alt="ai-lab : une question, un golden set partagé, des variantes Java ou Python, un scorer conforme à la spec, des traces et scores dans Langfuse, un verdict chiffré" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Java-25-ED8B00?logo=openjdk&logoColor=white" alt="Java 25">
  <img src="https://img.shields.io/badge/Spring_Boot-4.1.1-6DB33F?logo=springboot&logoColor=white" alt="Spring Boot 4.1.1">
  <img src="https://img.shields.io/badge/Spring_AI-2.0.1-6DB33F?logo=spring&logoColor=white" alt="Spring AI 2.0.1">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white" alt="Python 3.13">
  <img src="https://img.shields.io/badge/FastAPI-0.159-009688?logo=fastapi&logoColor=white" alt="FastAPI 0.159">
  <img src="https://img.shields.io/badge/MCP-SDK_Java_%26_Python-111827" alt="MCP">
  <img src="https://img.shields.io/badge/DeepEval-4.3.1-6E56CF" alt="DeepEval 4.3.1">
  <img src="https://img.shields.io/badge/Langfuse-4.74-0A0A0A" alt="Langfuse 4.74">
  <img src="https://img.shields.io/badge/licence-MIT-blue" alt="Licence MIT">
</p>

# ai-lab

Laboratoire d'AI engineering : des expériences ciblées, mesurées et reproductibles sur les agents, le RAG et les LLM, en Java (Spring Boot, Spring AI) et en Python (SDK MCP, FastAPI).

Ce dépôt n'est pas un catalogue de démos. Chaque expérience pose une question, la teste contre une baseline et se conclut par un chiffre.

## Thèse

Les choix d'architecture d'un système à base de LLM (forme des outils, découpage des documents, stratégie de récupération, rédaction des prompts) se décident souvent à l'intuition. Ils se mesurent.

Ce lab traite ces choix comme des hypothèses : une question, un protocole écrit avant de lancer quoi que ce soit, un jeu d'évaluation versionné, et un verdict chiffré. Le verdict est publié même quand l'hypothèse est réfutée.

## Règles du lab

1. **Une expérience répond à une seule question.** Elle se conclut par un verdict chiffré (baseline, variante, delta), avec la dispersion mesurée sur plusieurs répétitions. Une expérience qui compare plusieurs leviers se découpe en étapes, une par levier, chacune jugée contre une baseline gelée ; son verdict est le tableau des deltas.
2. **Le protocole est écrit avant les résultats.** Chaque expérience suit le gabarit [`experiments/_template`](experiments/_template/README.md) : Question · Hypothèse · Protocole · Discipline d'itération · Mesures · Résultats · Verdict · Limites.
3. **On itère sur `dev`, on juge sur `test`.** Les variantes reçoivent le même effort d'itération, sont gelées par un commit, puis passent un seul run final sur le split `test`.
4. **Les domaines sont séparés des expériences.** Un domaine (`domains/<nom>/`) regroupe ses données et ses jeux d'évaluation. Plusieurs expériences peuvent tourner sur le même domaine, et chacune indique les siens dans son README.
5. **L'évaluation est commune par sa spec, pas par son code.** Voir [Évaluation](#évaluation).
6. **Un jeu de données publié ne change plus.** Pour le corriger, on crée `v2`. Une version est considérée comme publiée dès qu'un rapport de résultats la cite.
7. **Les données sont synthétiques ou publiques.** Synthétiques, elles sont produites par des scripts seedés et versionnés. Publiques, elles sont sous une licence compatible avec un dépôt public, et le README du domaine cite la source, la licence et la date d'extraction. Aucune donnée client, dans les deux cas.
8. **Les comparaisons se font à modèle constant.** Les deltas sont calculés modèle par modèle. Les tokens ne sont jamais comparés d'un fournisseur à l'autre, car leurs tokenizers diffèrent.
9. **Un « non concluant » n'est pas une égalité.** Le rapport dit si l'intervalle de confiance exclut le plus petit écart qui compte, en gain et en perte. Les leviers se classent par leur delta et leur intervalle, pas par leur verdict.

## Évaluation

Le principe est celui d'une suite de conformance, comme [JSON-Schema-Test-Suite](https://github.com/json-schema-org/JSON-Schema-Test-Suite) ou la [conformance MCP](https://github.com/modelcontextprotocol/conformance) : les données et les règles sont partagées, le code est propre à chaque langage.

- **Partagé :** les golden sets (JSONL validé par JSON Schema), les règles de notation (`SPEC.md`) et des **vecteurs de conformance**, c'est-à-dire des cas de notation accompagnés de leurs scores attendus.
- **Propre à chaque langage :** le scorer. En Java, il tourne dans JUnit. En Python, c'est une métrique personnalisée DeepEval. Les deux doivent passer les mêmes vecteurs : c'est ce qui garantit qu'ils notent de la même façon.
- **Restitution :** les traces et les scores remontent dans Langfuse (auto-hébergé) pour comparer les runs. Les rapports Markdown datés restent dans `results/`, pour que tout soit rejouable sans compte.

Une spec versionnée suit la même règle que les données : une fois publiée, elle ne change plus ; une correction donne une `v2`.

**Exemple de golden set : [`rag-qa`](domains/droit-consommation/golden/rag-qa/README.md)** (droit de la consommation, v5, 366 questions : 120 pour itérer, 246 pour juger). Il comprend neuf types de questions inspirés de benchmarks RAG publics (CRAG, MultiHop-RAG) : question directe, paraphrase, contexte perdu, plusieurs articles, comparaison, liste, fausse prémisse, question sans réponse… Les articles sont tirés par un script seedé, et non choisis par le LLM rédacteur. Chaque item est relu sur tout le corpus, preuves copiées mot pour mot à l'appui. Les questions sans réponse sont auditées, et les défauts connus sont écrits dans ses limites.

## Expériences

### Par aspect

| Aspect | Expérience | Statut |
|---|---|---|
| Design d'outils MCP | [001 — Outils par intention ou miroir REST ?](experiments/001-mcp-outils-par-intention/README.md) | Terminée ([rapport final](experiments/001-mcp-outils-par-intention/results/2026-11-19-rapport-final.md)) : B meilleure de +24,6 pts avec Mistral small ; non concluant (plafond) avec Gemini Flash-Lite et Claude Haiku 5.5 |
| RAG | [002 — Notre RAG répond mal : quels sont les plus gros leviers ?](experiments/002-leviers-rag/README.md) | Conclue le 2026-11-15 (run consolidé 2, golden set v5 ; [rapport final](experiments/002-leviers-rag/results/2026-11-19-rapport-final.md)) : le RAG naïf d'abord (+28 à +44 pts de `correct`) ; puis trois leviers du même ordre : 20 passages au lieu de 5 (+4,4 à +9,4 pts, concluant avec un modèle sur trois), un meilleur générateur (+5,6 et +7,1 pts, et 16 à 25 pts de réponses inventées en moins), le RAG agentique (+2,8 à +6,7 pts selon le modèle, concluant avec Gemini 4 Carbon) ; reformulation sans effet à 5 pts près avec deux modèles sur trois ; reclassement après 20 passages et abstention sous un score de reclassement non concluants ; consigne d'abstention utile ou nuisible selon le modèle |

### Par domaine

| Domaine | Contenu | Expériences |
|---|---|---|
| [magasin](domains/magasin/README.md) | Catalogue d'environ 50 produits, 5 magasins, stocks (synthétiques) | 001 |
| [droit-consommation](domains/droit-consommation/README.md) | Code de la consommation, 2 150 articles en vigueur au 13/07/2025 (LEGI, Licence Ouverte) ; golden set `rag-qa` de 200 questions (v1), étendu à 366 (v5) | 002 |

## Résultats clés

Chaque ligne renvoie au rapport daté qui l'a produite.

**001 — Outils par intention ou miroir REST ?** En une page : [rapport final](experiments/001-mcp-outils-par-intention/results/2026-11-19-rapport-final.md).

| Expérience | Modèle | Mesure | Baseline | Variante | Delta [IC 95 %] | Verdict |
|---|---|---|---|---|---|---|
| [001](experiments/001-mcp-outils-par-intention/results/2026-11-04-run-final-test.md) | `mistral-small-2603` | `success` | 0,742 | 0,988 | +0,246 [+0,160 ; +0,332] | B meilleure |
| [001](experiments/001-mcp-outils-par-intention/results/2026-11-04-run-final-test.md) | `gemini-3.5-flash-lite` | `success` | 0,994 | 1,000 | +0,006 [−0,006 ; +0,018] | non concluant |
| [001](experiments/001-mcp-outils-par-intention/results/2026-11-04-run-final-test.md) | `claude-haiku-5-5` | `success` | 0,996 | 1,000 | +0,004 [−0,002 ; +0,010] | non concluant |

**002 — Les leviers du RAG**, en une page : [rapport final](experiments/002-leviers-rag/results/2026-11-19-rapport-final.md). Détail du [run consolidé 2](experiments/002-leviers-rag/results/2026-11-15-run-consolide-2-test.md) : golden set `rag-qa` v5, spec `rag-qa/v2`, `test` 234 items valides, k = 3. Delta de `correct` (variante − baseline), IC à 95 % apparié. En gras : concluant, après correction de Holm quand plusieurs comparaisons forment une famille.

*Leviers à générateur constant (étapes 1 à 4)*

| Levier (étape) | Baseline | `mistral-small-2603` | `ministral-14b-2512` | `gemini-3.5-flash-lite` |
|---|---|---|---|---|
| RAG naïf, 5 passages (1) | modèle seul | **+0,359** [+0,288 ; +0,430] | **+0,440** [+0,372 ; +0,508] | **+0,276** [+0,206 ; +0,347] |
| Reformulation de la question (2) | RAG naïf | −0,001 [−0,037 ; +0,034] | +0,003 [−0,033 ; +0,039] | +0,014 [−0,023 ; +0,052] |
| 20 passages au lieu de 5 (3) | RAG naïf | +0,054 [+0,007 ; +0,101] | +0,044 [−0,002 ; +0,090] | **+0,094** [+0,053 ; +0,135] |
| Reclassement, 50 candidats vers 5 (4) | 20 passages | −0,016 [−0,059 ; +0,027] | +0,003 [−0,034 ; +0,040] | −0,011 [−0,052 ; +0,029] |
| Reclassement, 50 candidats vers 5 (4) | RAG naïf | +0,038 [−0,005 ; +0,082] | +0,047 [−0,002 ; +0,096] | **+0,083** [+0,036 ; +0,130] |

Ce que les non concluants excluent, par rapport au plus petit écart qui compte (5 points pour la reformulation, 3 pour les passages et le reclassement) :
- **Reformulation** : ni gain ni perte de 5 points avec les deux Mistral.
- **20 passages, et reclassement contre le RAG naïf** : une perte de 3 points est exclue, pas un gain. Ces leviers ne sont pas petits, ils sont mal mesurés.
- **Reclassement contre 20 passages** : un gain de 3 points est exclu avec Mistral Small et Gemini, pas une perte.

*Abstention (étapes 5 et 6)*, jugée sur les réponses inventées aux 51 questions sans réponse, avec une garde sur les abstentions à tort :
- **Consigne d'abstention**, selon le modèle :
  - Mistral Small : compromis, −8,5 points de réponses inventées contre +3,8 d'abstentions à tort.
  - Ministral : meilleure, −4,6 points [−8,8 ; −0,4], mais sous l'écart utile de 10 points.
  - Gemini : moins bonne, +14,2 points d'abstentions à tort et −8,7 de `correct`.
- **Abstention sous un score de reclassement** : non concluante pour les trois, ni baisse ni hausse de 10 points.

*Le générateur comme levier (étape 7)*, contre Mistral Small avec 20 passages (`correct` 0,815, réponses inventées 0,248, 0,0006 $ et 0,8 s par question). C'est la seule étape où le modèle change : il y est le levier.

| Générateur | `correct` | Delta [IC 95 %] | Réponses inventées | Delta [IC 95 %] | Coût par question | Latence médiane |
|---|---|---|---|---|---|---|
| Mistral Large 4 | 0,870 | **+0,056** [+0,014 ; +0,097] | 0,013 | **−0,235** [−0,351 ; −0,119] | 0,0032 $ | 4,5 s |
| Gemini 4 Carbon | 0,886 | **+0,071** [+0,025 ; +0,117] | 0,000 | **−0,248** [−0,365 ; −0,132] | 0,0092 $ | 5,5 s |
| Gemma 4 31B | 0,859 | +0,044 [−0,002 ; +0,091] | 0,000 | **−0,248** [−0,365 ; −0,132] | — (palier gratuit) | 2,9 s |
| Mistral Small en raisonnement | 0,813 | −0,001 [−0,044 ; +0,041] | 0,085 | **−0,163** [−0,263 ; −0,064] | 0,0008 $ | 2,2 s |

*RAG agentique (étape 8)* : recherche par outils MCP, contre 20 passages, à générateur constant.

| Générateur | `correct` | Delta [IC 95 %] | Coût par question | Latence médiane |
|---|---|---|---|---|
| Mistral Large 4 (verdict de l'étape) | 0,870 → 0,899 | +0,028 [−0,005 ; +0,062] : perte de 3 points exclue, pas un gain | 0,0032 → 0,0071 $ | 4,5 → 8,5 s |
| Gemini 4 Carbon (secondaire, déclarée d'avance) | 0,886 → 0,953 | **+0,067** [+0,032 ; +0,102] | 0,0092 → 0,0248 $ | 5,5 → 20,9 s |

**À retenir.** Le RAG lui-même est le premier levier. Viennent ensuite, du même ordre sur `correct`, les 20 passages, le générateur et le RAG agentique ; le générateur se détache sur les réponses inventées, qu'il fait presque disparaître.

**Limites.** Un seul corpus, où un article est indexé en un seul passage, sans découpage (seuls 3 articles sur 2 150, de plus de 12 000 caractères, sont coupés) ; avec 20 passages, 12 % des questions avec réponse n'ont pas encore tous leurs articles attendus ; un `test` lu trois fois en agrégat ; un plus petit effet détectable de 6 à 8 points sur `correct` et de 12 à 19 sur les réponses inventées, au-dessus de plusieurs écarts utiles.

Les verdicts antérieurs (golden sets v1 à v4, spec v1) restent dans leurs rapports : [run consolidé 1](experiments/002-leviers-rag/results/2026-11-09-run-consolide-test.md), étapes [1](experiments/002-rag-naif-vs-modele-seul/results/2026-11-07-run-final-test.md), [2](experiments/003-reformulation-de-requete/results/2026-11-08-run-final-test.md), [3](experiments/004-top-k-20/results/2026-11-08-run-final-test.md), [4](experiments/005-reclassement/results/2026-11-09-run-final-test.md), [5](experiments/006-consigne-abstention/results/2026-11-09-run-final-test.md) et [6](experiments/002-leviers-rag/results/2026-11-10-etape-6-test.md). Deux verdicts ont changé entre la v4 et la v5 : les 20 passages avec Ministral ne sont plus concluants (+6,8 puis +4,4), et la consigne d'abstention l'est devenue avec Ministral.

## Organisation du dépôt

```
ai-lab/
├── evals/
│   ├── spec/       # par famille et par version : SPEC.md, JSON Schema, vecteurs de conformance
│   ├── java/       # scorer Java (JUnit), testé contre les vecteurs
│   └── python/     # scorer Python (métrique DeepEval), testé contre les vecteurs
├── rag/python/     # briques RAG communes aux étapes de l'expérience 002 (corpus, embeddings, recherche) : baseline naïve, leviers en option
├── domains/        # un dossier par domaine : données versionnées, golden sets, générateur seedé
└── experiments/    # une expérience par dossier : cadrage, implémentations (java/, python/), results/
```

## Stack

**Java**

| Composant | Version |
|---|---|
| Java | 25 (LTS), via une toolchain Gradle |
| Build | Gradle 9.8.2, Kotlin DSL, multi-module |
| Spring Boot | 4.1.1 |
| Spring AI | 2.0.1 (starter MCP Server WebMVC, transport Streamable HTTP) |
| SDK MCP Java | 2.1.0, imposée à la place de la 2.0.0 tirée par Spring AI (compatibilité à valider par un test de démarrage) |
| Évaluation | JUnit, scorer conforme à la spec ; Apache Commons Statistics 1.3 (loi de Student) et ICU4J 78.3 (casefold Unicode complet) |

**Python**

Côté Python, aucune bibliothèque ne couvre seule le périmètre de Spring AI : chaque rôle a sa propre bibliothèque.

| Rôle | Choix | Version |
|---|---|---|
| Runtime et workspace | Python, uv | 3.13 |
| Serveurs MCP | SDK MCP Python officiel (embarque Starlette et uvicorn, sans FastAPI) | 2.3.0 |
| API HTTP, quand une expérience en expose une | FastAPI | 0.159.0 |
| Boucle d'agent, client LLM et MCP | Pydantic AI (Gemini, Mistral, Claude et MCP en extras), retenu pour la 001 après le test exploratoire | 2.65.0 |
| Tests et qualité | pytest, ruff | 9.1.1 · 0.17.1 |
| Évaluation | DeepEval, avec une métrique personnalisée conforme à la spec | 4.3.1 |

**Commun**

| Composant | Choix |
|---|---|
| Fournisseurs LLM | Gemini, Mistral, Claude (starters Spring AI côté Java ; Pydantic AI côté Python) ; Cohere pour le reclassement de la 002 |
| Golden sets et specs | JSONL et JSON Schema, lisibles depuis les deux langages |
| Traces et scores | Langfuse 4.74.0, auto-hébergé (`infra/langfuse/`, Docker Compose, sur `127.0.0.1`) |

Versions vérifiées le 2026-10-21 sur Maven Central, PyPI, GitHub et services.gradle.org.

Point d'attention sur la spec MCP : le SDK Python 2.3.0 supporte la révision `2026-07-28` (cœur sans état, `server/discover`). La pile Java s'arrête à la révision `2025-11-25`. Le détail est dans la section Limites de l'expérience 001.

Les serveurs MCP du laboratoire suivent un référentiel commun, sourcé et daté : [bonnes pratiques MCP](docs/mcp-bonnes-pratiques.md). Il sépare les exigences de la spec (conception des réponses et des erreurs, sécurité du transport, authentification OAuth 2.1) des recommandations de praticiens, que les expériences mettent à l'épreuve.

## Reproduire

Prérequis : un JDK 25 (sinon Gradle le télécharge) et [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env      # renseigner les clés API ; .env n'est jamais versionné
./gradlew build           # implémentations et scorer Java, dont les tests de conformance
uv sync                   # workspace Python
uv run pytest             # scorer Python (dont la conformance), générateurs de données, implémentations
uv run ruff check
```

La procédure propre à chaque expérience (lancement des variantes, notation, rapport) est décrite dans son README.

## Auteur

Gabin Bloquet, AI Engineer freelance : Java, Spring AI | Python, FastAPI | agents, RAG, LLM, MCP.

## Licence

[MIT](LICENSE)
