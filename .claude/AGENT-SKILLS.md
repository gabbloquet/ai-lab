# agent-skills (Addy Osmani) — provenance

- Source : https://github.com/addyosmani/agent-skills
- Commit : aeac41d4d005999432bb7312f7ff06383a91d59d (2026-10-13), version 0.6.13
- Licence : MIT, voir `AGENT-SKILLS-LICENSE`
- Installé le 2026-10-27

## Copié

- `skills/` : 24 skills sur 25
- `commands/` : code-simplify, constraints, plan, review, ship, spec, test, webperf
- `agents/` : les 4 agents
- `references/` : les checklists partagées (les skills y renvoient via `../../references/`)

## Exclu

- skill `incremental-implementation` et commande `/build` (y compris `/build auto`) : contraires à la règle « le code s'écrit ensemble » du CLAUDE.md.
- hooks : l'amont ne les branche pas sur Claude Code.

## Modifié localement

- `commands/*.md` : préfixe `agent-skills:` retiré des noms de skills (installation hors plugin, donc sans espace de noms).

## Références orphelines connues

`incremental-implementation` et `/build` restent cités dans `using-agent-skills`, `spec-driven-development`, `planning-and-task-breakdown`, `constraint-driven-development` et `deprecation-and-migration`.
