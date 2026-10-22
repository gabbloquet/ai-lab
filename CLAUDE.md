# Règles de travail — ai-lab

Dépôt public : le laboratoire et la vitrine d'un AI Engineer freelance (Java / Spring AI, Python, agents, RAG, MCP). Voir le README pour la thèse et l'index des expériences.

## Rôle de Claude

- Le propriétaire du dépôt code lui-même la logique des expériences. Claude propose, explique, relit, et écrit les tests quand on le lui demande. Il n'implémente ni les outils ni la logique d'une expérience sans accord explicite, donné dans la session en cours.
- Le code s'écrit **ensemble**, y compris le squelette, les classes de données, les signatures, la configuration applicative et les tests. Claude propose et explique une étape à la fois ; le propriétaire écrit, ou valide avant que Claude n'écrive. Claude ne produit jamais un lot de fichiers de code d'un coup, même quand un plan a été validé. Seule exception : la configuration de build sans choix d'expérience (Gradle, uv), une fois le plan validé.
- Avant toute implémentation, on discute des choix. Claude expose les compromis, donne une recommandation, puis attend le feu vert. Le but est que le propriétaire apprenne et maîtrise chaque décision.
- Sur une question ouverte, Claude part du besoin et non de sa première idée. Il cherche des alternatives réelles avant de recommander quoi que ce soit.

## Méthode

- TDD : test rouge, implémentation minimale, refactor.
- Un commit par étape. Le message donne le motif (pourquoi), pas seulement le quoi. Montrer `git status` avant chaque commit. Ne jamais pousser sans demande explicite.
- Chaque expérience répond à UNE question et se conclut par un verdict chiffré (baseline / variante / delta, avec la dispersion sur plusieurs répétitions). Elle suit le gabarit `experiments/_template/README.md`, et son protocole est écrit avant les résultats.
- Le README d'une expérience indique le ou les domaines sur lesquels elle tourne.
- Discipline d'itération : même budget d'itération sur `dev` pour chaque variante, commit de gel avant le run `test`, un seul run final. Claude signale tout écart, par exemple une variante plus travaillée que l'autre ou une demande de relancer le `test`.
- Les comparaisons se font à modèle constant. Les tokens ne se comparent jamais d'un fournisseur à l'autre.

## Évaluation : spec partagée, implémentations par langage

- Sont partagés, et neutres vis-à-vis du langage : les golden sets (`domains/<domaine>/golden/<famille>/vN/`), et sous `evals/spec/<famille>/vN/` les règles de notation (`SPEC.md`), le JSON Schema et les vecteurs de conformance (des cas accompagnés de leurs scores attendus).
- Chaque langage a son scorer : JUnit en Java (`evals/java/`), métrique personnalisée DeepEval en Python (`evals/python/`). Les deux doivent passer tous les vecteurs de conformance.
- Une divergence entre langages se corrige en ajoutant un vecteur, jamais en ajustant un seul des deux scorers.
- On ne s'appuie pas sur une métrique DeepEval prête à l'emploi si ses règles diffèrent de la spec. Exemple : `ToolCorrectnessMetric` calcule une précision.
- Chaque golden set a un split `dev` (pour itérer) et un split `test` (seul à porter le verdict). En aidant à itérer, Claude n'utilise que le `dev` : il n'affiche ni n'analyse les échecs item par item du `test` avant le run final.
- Les traces et les scores remontent dans Langfuse (auto-hébergé). Les rapports Markdown datés vont dans `experiments/<exp>/results/` et citent la version du golden set, celle de la spec et les lockfiles utilisés.

## Données

- Un jeu de données ou une spec publiés sont immuables : pour les corriger, on crée `v2`. Une version est publiée dès qu'un rapport de `results/` la cite.
- Les données des domaines sont 100 % synthétiques, générées par un script seedé et versionné.

## Dépôt public

- Aucun secret, jamais. Les secrets passent par `.env` (ignoré par git) ; `.env.example` documente les noms, sans valeurs.
- Aucune donnée client, aucune référence à une mission, une enseigne ou une société réelle, aucun code repris d'un projet existant.

## Preuves

- Ne rien affirmer sans preuve : sortie de commande, lien, mesure. Écrire « non vérifié » plutôt que supposer, et dater les vérifications.
- Pour les versions de bibliothèques, vérifier sur Maven Central, PyPI ou GitHub, jamais de mémoire.

## Langue

- Documentation et README en français ; identifiants de code en anglais.
