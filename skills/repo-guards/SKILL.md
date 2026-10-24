---
name: repo-guards
description: Use when running, reading, or fixing the guv repo-discipline guards in a repo wired with repo-guards, when a gate goes red before a release, or when deciding what a parity, version-class, lockfile-parity, prose, or CI finding means and its exact fix.
---

# Operating guv (the repo-guards gates)

The kit: one config file per repo (`.repolice.toml`), one CLI (`guv`),
five gates. Every "trusted" claim about a repo becomes an exit code.

## The gates and what each refuses

| Gate | Refuses when | First fix |
|---|---|---|
| `parity` | the latest tag is unpushed, or has no GitHub release body, or no source notes file, or the version on disk does not match the tag | push the tag / `gh release create <tag> --notes-file <notes>` / write the notes / bump + `uv lock` |
| `version_class` | docs-only content claims minor or major; code claims a lower or equal version | reclassify the bump (docs-only = patch) or ship a real code change |
| `lockfile_parity` | a lockfile's self-version lags its pyproject; version files disagree | `uv lock` in every project dir named by `version_files` |
| `prose` | banned characters or words in tracked markdown | fix the prose; never weaken the banned list |
| `ci` | the config's VERBATIM CI commands fail | make the repo's own CI green, then re-run |

## The commands

```bash
guv check <repo>                     # every gate; red = do not release
guv check <repo> --except parity     # skip gates that cannot run here
guv release <repo> vX.Y.Z            # the flow, dry run (default)
guv release <repo> vX.Y.Z --cut      # actually tag + push + gh release
guv init <repo>                      # starter .repolice.toml to edit
```

## The rules an agent obeys

1. **Dry run first.** `guv release` writes nothing without `--cut`.
   Read every refusal before cutting.
2. **Notes before flow.** The release refuses without the source notes
   at `{notes_dir}/<slug>/RELEASE-NOTES-{tag}.md`. Write them first.
3. **Findings are evidence.** Never weaken the config to get green: no
   dropping a banned word, no emptying `ci`, no widening
   `prose_skip_patterns`.
4. **`ci` entries are verbatim.** They must mirror
   `.github/workflows/ci.yml`, or the gate passes a repo that CI would
   fail.
5. **`--except` is for gates that cannot run in the current context**,
   not for gates that are red. A red `prose` or `ci` gate is never
   skipped at release time.
6. **Docs-only content takes a PATCH bump.** The guard reads the changed
   paths between the last tag and HEAD plus the dirty worktree; an
   empty diff counts as docs class.

## Reading a finding

Every finding is `file:line: 'term'` (prose) or a sentence with the fix
inline (everything else). The finding text is the contract: it names the
exact command that resolves the mismatch, for example
`git push origin <tag>` or `uv lock in <dir>`. Apply that command; do
not improvise a nearby one.

## Wiring a NEW repo onto the guards

That is a different skill: the `repo-guards-setup` managed skill (config
generation, gate verification, Actions wiring). This skill teaches
operating a repo that is already wired.

## Not this kit's job

- It does not lint code files (its prose gate reads tracked markdown
  only).
- It does not replace the repo's CI; its `ci` gate runs the repo's own
  commands.
- It is not a cross-repo Action source; the composites are vendored.

## Verifying a state claim

"Published" means the parity gate is green: tag pushed and on main, a
GitHub release object with a real body, source notes in the repo, and
the pyproject version equal to the tag. Anything less is "not
published", whatever the chat says.