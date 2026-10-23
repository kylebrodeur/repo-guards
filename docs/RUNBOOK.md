# RUNBOOK: the operator's reference

Everything in this runbook is verified against `guv` 0.1.0
(`repoguards/`, Python 3.11+, stdlib only) on 2026-10-22. The tutorial
path lives in [quickstart.md](quickstart.md); repeated tasks live in
[how-to.md](how-to.md). This file is the complete surface: every
command, every config key, every error string, and the recovery
procedures.

## The full command surface

```
guv [-h] {check,release,init} ...
```

### `guv check [path] [--except EXCEPT]`

Runs every gate against the repo at `path` (default `.`). Prints one
line per gate: `ok`, `FAIL` with findings, or a skip note. Exit 0 when
every (non-skipped) gate is green, 1 otherwise.

- `path`: the repo directory. Config resolution order:
  1. `REPOLICE_CONFIG` env var (a missing env-named file errors
     immediately)
  2. `.repolice.toml`, then `repolice.toml`, at the repo root
- `--except`: comma-separated gate names to skip (`parity`,
  `version_class`, `lockfile_parity`, `prose`, `ci`).

Gate order in output: `parity`, `version_class`, `lockfile_parity`,
`prose`, `ci`. Without a release candidate (the disk version equals the
latest tag, or no version resolves), `version_class` self-skips:

```
  version_class: (skipped: no release candidate; use the release flow)
```

### `guv release <path> <version> [--cut]`

The release flow: gates in the fixed order (prose, version-class,
lockfile-parity, CI), then the source-notes check, then (dry run by
default) tag + push + `gh release create` + the parity oracle.

- `version`: a `vX.Y.Z` string. The `v` prefix requirement comes from
  `require_v_prefix` (default true). An invalid version is refused:
  `'notaversion' is not a valid vX.Y.Z`
- `--cut`: actually write. Without it the flow stops after printing the
  plan: `== dry run: stopping before the write`

On success: `== published: <owner>/<repo> <tag> (parity ok)`.

Writes performed by `--cut` (in order): `git tag -a <tag>`,
`git push origin <tag>`,
`gh release create <tag> --repo <owner>/<repo> --notes-file <notes>
--title "<repo> <tag>"`. The tag annotation message is `<repo> <tag>`.

### `guv init <path> [--force]`

Writes the starter `.repolice.toml`. Refuses to overwrite:

```
refusing: /path/to/your-repo/.repolice.toml exists (--force to overwrite)
```

`--force` overwrites without backup.

## The full config surface (`.repolice.toml`)

| Key | Default | Meaning |
|---|---|---|
| `owner` | derived from the origin remote | the GitHub owner for `gh` calls |
| `repo` | the directory's name | the GitHub repo name |
| `notes_dir` | `"docs/releases"` | where source notes live; absolute paths allowed (central notes home) |
| `notes_glob` | `"RELEASE-NOTES-{tag}.md"` | the notes filename pattern; `{tag}` is filled |
| `version_files` | `["pyproject.toml"]` | every pyproject the guards read; each needs a `[project].version` |
| `require_v_prefix` | `true` | tags must be `v`-prefixed (latest-tag check at parity, tag writes at release) |
| `docs_paths` | see below | the version-class docs set |
| `prose_banned` | the four words + em/en/minus dashes | chars/words the prose gate fails on |
| `prose_skip_patterns` | two rule-citation regexes | lines matching one are exempt (definitions, not instances) |
| `ci` | `[]` (an empty list fails the gate) | the VERBATIM commands from `.github/workflows/ci.yml` |
| `squash` | none (no-squash default) | `"always"` or `"never"` recorded for the release flow |
| `notes_candidates` | `[]` | extra slug spellings the notes search tries |

Default `docs_paths`: `docs/`, `README.md`, `CONTRIBUTING.md`,
`SECURITY.md`, `FUNDING.yml`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`,
`AGENTS.suggested.md`, `llms.txt`, `.github/ISSUE_TEMPLATE/`,
`.github/PULL_REQUEST_TEMPLATE.md`.

The notes search: `notes_dir` itself, then one subdirectory per slug
candidate (the repo name; the repo name with the `modal-` prefix and
`-server` suffix peeled and re-composed; then `notes_candidates`
extras).

Config loading is exact:

```bash
REPOLICE_CONFIG=/path/to/config.toml guv check .
```

## Every error string, with its fix

An agent-facing harness checks READMEs and docs for these; this table
is the exhaustive list from the source and the live runs above.

| Error string | Emitted by | The fix |
|---|---|---|
| `no config (.repolice.toml, repolice.toml) in <repo>` (FileNotFoundError) | every command | `guv init <repo>` and edit the config |
| `REPOLICE_CONFIG names a missing file: <path>` (FileNotFoundError) | config load with the env var set | fix the path or unset `REPOLICE_CONFIG` |
| `config: owner unset and origin remote does not name a GitHub owner` (ValueError) | config load | set `owner =` in the config, or add a GitHub origin remote |
| `refusing: <path> exists (--force to overwrite)` | `guv init` | edit the existing config, or pass `--force` |
| `no \`ci\` commands in the config (add them; mirror .github/workflows/ci.yml)` | the `ci` gate | fill in the `ci` list with the workflow's verbatim commands |
| `CI FAILED: <command>` | the `ci` gate | make the repo's own CI green; the finding carries the failing output's last 5 lines |
| `<tag> is not a valid vX.Y.Z` (as `'notaversion' is not a valid vX.Y.Z`) | version-class | pass a real `vX.Y.Z` |
| `docs-only content (N files) but <v> changes major.minor (last <tag>): PATCH bump only` | version-class | bump the patch number, or ship the code change the minor claims |
| `<v> decreases <tag> with code changes` | version-class | never release a lower version with code changes; pick a higher one |
| `<v> does not increase <tag> for a code release` | version-class | a code change needs a higher major.minor.patch than the last tag |
| `REFUSED: source notes missing (<notes_dir>/<slug>/<glob>): write notes FIRST` | the release flow | write the notes file first (the path in the message is the pattern) |
| `REFUSED at <gate name>:` + findings | the release flow | fix the named gate's findings; nothing was written |
| `<repo>: no release tags at all` | parity | make the first release: notes, tag, push, `gh release create` |
| `<repo>: latest tag '<tag>' is not v-prefixed` | parity | use v-prefixed tags (or set `require_v_prefix = false`) |
| `<repo>: tag <tag> missing locally` | parity | fetch tags: `git fetch --tags` |
| `<repo>: tag <tag> is not pushed to origin (push it: git push origin <tag>)` | parity | run the printed push |
| `<repo>: remote tag <tag> (<sha>) != local (<sha>): re-pointed locally but not force-pushed` | parity | force-push the re-pointed tag or delete and recreate it; then rerun `gh release create` if the release object must follow |
| `<repo>: tag <tag> is NOT on origin/main` | parity | merge the tagged commit to main (or re-tag main's tip) |
| `<repo>: tag <tag> exists but NO GitHub release - gh release create <tag> --notes-file ...` | parity | create the release object from the source notes |
| `<repo>: release <tag> has no real notes body (<= 40 chars)` | parity | write real release notes (over 40 chars) |
| `<repo>: no source notes at <notes_dir>/<slug>/<glob> (write notes first)` | parity | write the source notes file |
| `<repo>: no resolvable version across <files>` | parity | give every `version_files` entry a `[project].version` |
| `<repo>: version on disk (<v>) != tag (<tag>)` | parity | bump so the pyproject version equals the tag, sync `uv lock`, re-tag |
| `<repo>: (note) tag <tag> is NOT at HEAD (there are commits beyond it)` | parity (informational) | none required; commits past a tag are normal iteration |
| `NOT PUBLISHED (parity failed after the push):` | the release flow after `--cut` | fix the listed parity findings; the tag is pushed, so finish the release |
| `version files disagree: [<versions>]` | lockfile-parity | make every `version_files` project carry the same version |
| `<proj>: lockfile self-version <v> != pyproject <v> (fix: uv lock in <proj>)` | lockfile-parity | run `uv lock` in that project dir and commit the lock diff |
| `<proj>: no [project].version (not releasable)` | lockfile-parity | add the version field |
| `<rel>:<line>: '<term>'` | prose | fix the prose at that location |

Two failure shapes that are NOT in this list: a non-`guv` crash (a
traceback) is a config-load failure handled above, and a shell
`command not found` means the kit is not installed (`uv tool install`,
see the quickstart).

## Recovery procedures

### A tag was pushed and the flow died before `gh release create`

The state: an annotated tag on origin with no release object. Fix
forward with the same commands the flow would have run:

```bash
git push origin <tag>        # already true if the push step succeeded
gh release create <tag> --repo <owner>/<repo> \
  --notes-file docs/releases/<slug>/RELEASE-NOTES-<tag>.md \
  --title "<repo> <tag>"
guv check .                  # parity must be green now
```

Never leave it as a silent handoff: if you stop here, say "tag pushed,
release NOT cut".

### The version moved after the tag was cut

The parity finding `version on disk ... != tag` is the live symptom.

1. Bump the pyproject to the tagged version.
2. `uv lock` and commit the lockfile diff.
3. Re-point the tag: delete it locally and remotely, re-tag the new
   commit, force-push, and re-run `gh release create` with the same
   notes.

```bash
git tag -d <tag> && git push origin :refs/tags/<tag>
guv release . <tag> --cut
```

The guard's finding names this state exactly (`re-pointed locally but
not force-pushed`) when local and remote tags disagree.

### A gate is green locally but red in CI (or the opposite)

The `ci` gate runs the config's commands, not the workflow's
environment. Differences that matter:

- Python version: the workflow pins one (`astral-sh/setup-uv@v7` +
  `uv sync`); local runs use the checkout's `.venv`.
- Network and secrets: parity calls `gh` and `git ls-remote`, which
  need credentials and the network. In CI without them, parity fails
  and `--except parity` is the honest local shape; the `tag-parity`
  Action is the parity-enforcing surface.

### The prose gate flags a line that is itself the rule

A line that names a banned word as its own rule (for example a doc
listing the banned words) is a definition. Add (or reuse) a skip
pattern in `prose_skip_patterns`:

The defaults: one pattern matching rule-citation lines (the ones that
say which words are not allowed, or name them as their own rule), plus
a pattern for the parenthesized two-word citation line. The exact
literals are in `repoguards/config.py` (`prose_skip_patterns`). A skip
pattern is an explicit, scoped carve-out, never a way to hide ordinary
prose that trips a term.

### The kit source is missing in CI (`::error::No kit source found`)

The composite Actions resolve the kit vendored-first:

1. `tools/repo-guards/` (the consumer's vendored copy)
2. the kit tree beside the action (`$GITHUB_ACTION_PATH/../..`)
3. `repo-guards/` beside the workflow (monorepo shape)

Any miss fails LOUD with that exact message. Fix the layout: vendor the
kit (the delivery model), or fix the checkout shape. Cross-repo
`uses:` references to a private kit home are not the supported path.

## The Actions surface

| Action | Input | Default | Runs |
|---|---|---|---|
| `release-gates` | `config` | `.repolice.toml` | `guv check .` |
| `release-gates` | `python-version` | `3.12` | the kit's Python |
| `tag-parity` | `config` | `.repolice.toml` | `guv check . --except version_class,prose,ci,lockfile_parity` with `REPOLICE_CONFIG` set |

Both resolve the kit vendored-first (the resolution ladder above),
install uv-native (`astral-sh/setup-uv@v7`), and install with
`uv tool install --from "$KIT_DIR" guv || uv tool install -e
"$KIT_DIR"`. The
[example workflow](../actions/example-workflow.yml) shows the full
wiring, including the required `fetch-depth: 0`.

## Library surface (for scripts that need the verdicts)

Every guard is a pure function over `(repo_path, config)` returning
`CheckResult(ok, findings)`:

```python
from repoguards import parity, prose, ci, lockfile_parity, version_class
from repoguards.config import Config
from repoguards.release import run, plan  # run: the flow; plan/notes_path: helpers

cfg = Config.load(repo)
result = prose.check(repo, cfg)
print(result.ok, result.findings)
```

## Verification of this repo's own docs

The doc harness (the AI ECP standard) plus this repo's own gates:

```bash
uv run pytest tests -q
uv run ruff check .
uv run pytest tests -q
uv run guv check . --except parity
```

Expected: every check PASS, `40 passed`, and every gate `ok` except the
parity gate's remote checks, which need network and a published state.