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
  <img src="https://img.shields.io/badge/Langfuse-4.67-0A0A0A" alt="Langfuse 4.67">
  <img src="https://img.shields.io/badge/licence-MIT-blue" alt="Licence MIT">
</p>

# ai-lab

Laboratoire d'AI engineering : des expériences ciblées, mesurées et reproductibles sur les agents, le RAG et les LLM, en Java (Spring Boot, Spring AI) et en Python (SDK MCP, FastAPI).

Ce dépôt n'est pas un catalogue de démos. Chaque expérience pose une question, la teste contre une baseline et se conclut par un chiffre.

## Thèse

Les choix d'architecture d'un système à base de LLM (forme des outils, découpage des documents, stratégie de récupération, rédaction des prompts) se décident souvent à l'intuition. Ils se mesurent.

Ce lab traite ces choix comme des hypothèses : une question, un protocole écrit avant de lancer quoi que ce soit, un jeu d'évaluation versionné, et un verdict chiffré. Le verdict est publié même quand l'hypothèse est réfutée.

## Règles du lab

1. **Une expérience répond à une seule question.** Elle se conclut par un verdict chiffré (baseline, variante, delta), avec la dispersion mesurée sur plusieurs répétitions.
2. **Le protocole est écrit avant les résultats.** Chaque expérience suit le gabarit [`experiments/_template`](experiments/_template/README.md) : Question · Hypothèse · Protocole · Discipline d'itération · Mesures · Résultats · Verdict · Limites.
3. **On itère sur `dev`, on juge sur `test`.** Les variantes reçoivent le même effort d'itération, sont gelées par un commit, puis passent un seul run final sur le split `test`.
4. **Les domaines sont séparés des expériences.** Un domaine (`domains/<nom>/`) regroupe ses données et ses jeux d'évaluation. Plusieurs expériences peuvent tourner sur le même domaine, et chacune indique les siens dans son README.
5. **L'évaluation est commune par sa spec, pas par son code.** Voir [Évaluation](#évaluation).
6. **Un jeu de données publié ne change plus.** Pour le corriger, on crée `v2`. Une version est considérée comme publiée dès qu'un rapport de résultats la cite.
7. **Les données sont 100 % synthétiques.** Elles sont produites par des scripts seedés et versionnés.
8. **Les comparaisons se font à modèle constant.** Les deltas sont calculés modèle par modèle. Les tokens ne sont jamais comparés d'un fournisseur à l'autre, car leurs tokenizers diffèrent.

## Évaluation

Le principe est celui d'une suite de conformance, comme [JSON-Schema-Test-Suite](https://github.com/json-schema-org/JSON-Schema-Test-Suite) ou la [conformance MCP](https://github.com/modelcontextprotocol/conformance) : les données et les règles sont partagées, le code est propre à chaque langage.

- **Partagé :** les golden sets (JSONL validé par JSON Schema), les règles de notation (`SPEC.md`) et des **vecteurs de conformance**, c'est-à-dire des cas de notation accompagnés de leurs scores attendus.
- **Propre à chaque langage :** le scorer. En Java, il tourne dans JUnit. En Python, c'est une métrique personnalisée DeepEval. Les deux doivent passer les mêmes vecteurs : c'est ce qui garantit qu'ils notent de la même façon.
- **Restitution :** les traces et les scores remontent dans Langfuse (auto-hébergé) pour comparer les runs. Les rapports Markdown datés restent dans `results/`, pour que tout soit rejouable sans compte.

Une spec versionnée suit la même règle que les données : une fois publiée, elle ne change plus ; une correction donne une `v2`.

## Expériences

### Par aspect

| Aspect | Expérience | Statut |
|---|---|---|
| Design d'outils MCP | [001 — Outils par intention ou miroir REST ?](experiments/001-mcp-outils-par-intention/README.md) | Cadrage |

### Par domaine

| Domaine | Contenu | Expériences |
|---|---|---|
| [magasin](domains/magasin/README.md) | Catalogue d'environ 50 produits, 5 magasins, stocks (synthétiques) | 001 |

## Résultats clés

Aucun résultat publié pour l'instant. Chaque ligne renverra au rapport daté qui l'a produite.

| Expérience | Modèle | Mesure | Baseline | Variante | Delta | Verdict |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

## Organisation du dépôt

```
ai-lab/
├── evals/
│   ├── spec/       # par famille et par version : SPEC.md, JSON Schema, vecteurs de conformance
│   ├── java/       # scorer Java (JUnit), testé contre les vecteurs
│   └── python/     # scorer Python (métrique DeepEval), testé contre les vecteurs
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
| Spring AI | 2.0.1 (starter MCP Server) |
| SDK MCP Java | 2.1.0, imposée à la place de la 2.0.0 tirée par Spring AI (compatibilité à valider par un test de démarrage) |
| Évaluation | JUnit, scorer conforme à la spec |

**Python**

Côté Python, aucune bibliothèque ne couvre seule le périmètre de Spring AI : chaque rôle a sa propre bibliothèque.

| Rôle | Choix | Version |
|---|---|---|
| Runtime et workspace | Python, uv | 3.13 |
| Serveurs MCP | SDK MCP Python officiel (embarque Starlette et uvicorn, sans FastAPI) | 2.3.0 |
| API HTTP, quand une expérience en expose une | FastAPI | 0.159.0 |
| Boucle d'agent, client LLM et MCP | Pydantic AI (Gemini, Mistral, Claude et MCP en extras), retenu pour la 001 sous réserve d'un test exploratoire | 2.59.0 |
| Tests et qualité | pytest, ruff | 9.1.1 · 0.17.1 |
| Évaluation | DeepEval, avec une métrique personnalisée conforme à la spec | 4.3.1 |

**Commun**

| Composant | Choix |
|---|---|
| Fournisseurs LLM | Gemini, Mistral, Claude (starters Spring AI côté Java ; SDK côté Python à choisir) |
| Golden sets et specs | JSONL et JSON Schema, lisibles depuis les deux langages |
| Traces et scores | Langfuse 4.67.0, auto-hébergé |

Versions vérifiées le 2026-10-21 sur Maven Central, PyPI, GitHub et services.gradle.org.

Point d'attention sur la spec MCP : le SDK Python 2.3.0 supporte la révision `2026-07-28` (cœur sans état, `server/discover`). La pile Java s'arrête à la révision `2025-11-25`. Le détail est dans la section Limites de l'expérience 001.

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
