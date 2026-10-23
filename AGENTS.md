# repo-guards: the agent boundary (guv)

`guv` turns repo-discipline claims into exit codes. This file is the
boundary an agent obeys when operating it; the tutorial prose lives in
[docs/quickstart.md](docs/quickstart.md) and
[docs/how-to.md](docs/how-to.md).

## The boundary

1. **A gate finding is evidence, not noise.** Fix the repo or the config
   to make the gate honestly green. NEVER weaken a config (dropping a
   banned word, emptying `ci`, widening `prose_skip_patterns`) to turn a
   gate green. The prose gate is fail-closed on purpose.
2. **Dry run first, always.** `guv release` writes nothing without
   `--cut`. Run the dry run, read every line, and only then cut. A gate
   that is red at dry-run time is still red at cut time.
3. **Release notes are written BEFORE the flow.** `guv release` refuses
   without the source notes file at
   `{notes_dir}/<slug>/RELEASE-NOTES-{tag}.md`. Write them first; the
   flow does not draft them for you.
4. **The version-class rule is content, not mood.** Docs-only changes
   take a PATCH bump. Code changes may take minor or major, and never a
   lower or equal version than the last tag. Do not argue with the
   finding; reclassify the changes or the bump.
5. **`ci` config entries are the VERBATIM commands from
   `.github/workflows/ci.yml`**, not similar commands. Copying
   "equivalent" commands is how a red repo gets released.
6. **Do not skip gates to get green.** `--except` exists for gates that
   cannot run in a context (no release candidate, no network). Skipping
   `parity`, `prose`, or `ci` at release time is forbidden; skipping
   `version_class` in a plain `guv check` is the normal case (it self
   skips without a release candidate).
7. **Never edit a vendored copy of this kit.** The delivery model is
   vendoring: a consumer copies this kit into `tools/repo-guards/` and
   the actions into `.github/actions/`, pinned to a tag. Fixes belong in
   an upstream release, not in the vendored tree.
8. **A red repo does not release.** Any lane that pushes a tag must
   either finish the release (the flow does it) or hand back explicitly
   as "tag pushed, release NOT cut".
9. **Secrets and network are the operator's, not the guards'.** The kit
   shells out to `git` and `gh` with the ambient credentials. Pass no
   tokens in argv or config values.

## What this kit is NOT

- NOT a hosted service and NOT a SaaS release pipeline. It is a local
  CLI plus two composite Actions.
- NOT a formatter and NOT a linter for code. Its prose gate reads only
  tracked markdown.
- NOT a replacement for the repo's own CI. Its `ci` gate RUNS the
  repo's CI commands; it does not replace them.
- NOT a cross-repo Action source. Cross-repo `uses:` references to a
  private kit home need an access token and are unsupported; vendor the
  composites.

## When an agent is asked to wire a repo

Use the `repo-guards-setup` skill (the managed copy in
`~/.omp/agent/managed-skills/`): config generation, gate verification,
and Actions wiring, with the real-wave traps inline. This repo's own
skill in [skills/repo-guards/SKILL.md](skills/repo-guards/SKILL.md)
teaches using and operating the guards, not wiring.