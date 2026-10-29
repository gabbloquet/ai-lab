# Scorers Java

Implémentation Java des specs d'évaluation partagées (`evals/spec/`). Chaque scorer doit passer tous les vecteurs de conformance de sa spec, comme son équivalent Python : une divergence entre les deux se corrige en ajoutant un vecteur, jamais en ajustant un seul scorer.

## `tool-selection` v1

Paquet `io.github.gabbloquet.ailab.evals.toolselection` :

- `ToolSelectionScorer.score(expectation, calls, error)` note une exécution (SPEC.md § 6) : `expectation` est l'entrée `expected[variante]` d'un item du golden set, `calls` les appels émis.
- `Aggregation.of(scores)` calcule le delta apparié, l'IC à 95 % et le verdict sur les seuls items `test` (§ 7).
- `ValueEquality` applique l'égalité de la spec (§ 5). Deux points n'ont pas d'équivalent direct en Java et sont couverts par des vecteurs :
  - le casefold Unicode complet (`Straße` égale `STRASSE`), fait avec ICU4J : `toLowerCase` ne le fait pas (cv-025) ;
  - les espaces retirés aux deux bouts incluent l'espace insécable, comme `str.strip()` en Python : `String.strip()` ne le retire pas (cv-026).

Le scorer n'utilise pas Spring ; le BOM Spring Boot sert seulement à aligner les versions de Jackson, JUnit et AssertJ sur le reste du dépôt.

```bash
./gradlew :evals-java:test
```

Unicode (vérifié le 2026-10-29) : ICU4J 78.3 suit Unicode 17.0, le `unicodedata` de Python 3.13.14 suit Unicode 15.1. Les deux peuvent diverger sur des caractères ajoutés entre ces versions ; aucun n'apparaît dans les données du laboratoire (non vérifié au-delà des vecteurs).
