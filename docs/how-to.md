# How-to: the tasks you repeat

Checked against `guv` 0.1.0 on 2026-10-22. One question per section.
The one-time setup lives in [quickstart.md](quickstart.md); every
frequent task lives here. The full command surface and recovery
procedures live in [RUNBOOK.md](RUNBOOK.md).

## How do I check the repo's discipline right now?

```bash
guv check .
```

Run from the repo root (the `path` argument is optional and defaults to
`.`). Read each line; every gate prints `ok`, `FAIL` with findings, or
a skip note. Exit 0 means "release-safe", exit 1 means "do not
release".

A gate that cannot apply prints a note instead of failing:

```
  version_class: (skipped: no release candidate; use the release flow)
```

## How do I skip gates that cannot run in this context?

```bash
guv check . --except parity,prose
```

The argument is a comma-separated list of gate names (`parity`,
`version_class`, `lockfile_parity`, `prose`, `ci`). Use it for the
gates whose environment is absent (no network for `parity`, no release
candidate for `version_class`). The Action wiring uses the same spelling
for its oracle-only run:

```bash
guv check . --except version_class,prose,ci,lockfile_parity
```

Do not use `--except` to silence a red gate at release time; the release
flow runs all gates itself and does not accept skips.

## How do I cut a release?

Write the source notes first, then dry run, then cut:

```bash
mkdir -p docs/releases/<repo-slug>
$EDITOR docs/releases/<repo-slug>/RELEASE-NOTES-v0.1.1.md
guv release . v0.1.1
guv release . v0.1.1 --cut
```

The dry run prints the tag, the commit, and the notes path it found, and
stops before any write. `--cut` tags (`git tag -a`), pushes the tag,
creates the GitHub release from the notes file, and re-runs the parity
gate. A failure after the push prints:

```
NOT PUBLISHED (parity failed after the push):
```

followed by the parity findings. "Published" is claimed only when the
flow ends with `== published: ... (parity ok)`.

## How do I bump a docs-only change?

The version-class guard reads the changed paths between the last tag
and HEAD (plus the dirty worktree) and requires: docs-only content takes
a PATCH bump (same major.minor, bigger patch), code may bump minor or
major but never a lower or equal version.

```bash
guv release . v0.1.2          # docs-only: patch
guv release . v0.2.0          # allowed only when code changed
```

A docs-only minor refusal looks like:

```
REFUSED at gate: version-class:
  - docs-only content (2 files) but v0.2.0 changes major.minor (last v0.1.1): PATCH bump only
```

What counts as docs: by default the paths `docs/`, `README.md`,
`CONTRIBUTING.md`, `SECURITY.md`, `FUNDING.yml`, `SUPPORT.md`,
`CODE_OF_CONDUCT.md`, `AGENTS.suggested.md`, `llms.txt`,
`.github/ISSUE_TEMPLATE/`, and `.github/PULL_REQUEST_TEMPLATE.md`.
A code-extension file (`.py`, `.toml`, `.lock`, `.ts`, `.js`, `.sh`)
under a docs path is CODE, not docs: a generator script under `docs/`
does not make a release docs-only. `docs_paths` in the config
customizes the set.

## How do I fix a lockfile-parity finding?

```
    - .: lockfile self-version 0.1.0 != pyproject 0.2.0 (fix: uv lock in .)
```

Run the fix the finding names:

```bash
uv lock
git add uv.lock
```

For a multiproject layout (a `server/pyproject.toml` too), every
project's lock must be regenerated when its version moves, and every
`version_files` entry must agree. Version files that disagree print:

```
    - version files disagree: ['0.1.0', '0.3.0']
```

## How do I fix a prose finding?

```
  prose: FAIL
    - BAD.md:1: '<banned term 1>'
    - BAD.md:1: '<banned term 2>'
```

Fix the prose at `file:line`. The banned defaults are the em dash, the
en dash, the minus sign, and four filler words (the exact list lives in
the guard config's `prose_banned`, not in this sentence) and they are
policy, not physics: `prose_banned` and
`prose_skip_patterns` in the config change them. Two rules govern the
change:

- Lengthen the list only when the repo genuinely needs the term banned;
  the skip patterns exist for lines that DEFINE the rule (a doc that
  names the banned words as its own rule is a definition, not an
  instance).
- Never weaken the list to make a finding go away. The finding is the
  evidence; the prose is the bug.

## How do I fix a parity finding?

Each parity finding carries its fix inline:

```
  parity: FAIL
    - myrepo: tag v0.1.0 is not pushed to origin (push it: git push origin v0.1.0)
    - myrepo: tag v0.1.0 exists but NO GitHub release - gh release create v0.1.0 --notes-file ...
    - myrepo: no source notes at docs/releases/<slug>/RELEASE-NOTES-v0.1.0.md (write notes first)
```

Work them top down: push the tag, create the release object from the
source notes, and keep the notes file where the config looks for it.
An informational note rides along but does not fail the gate:

```
    - myrepo: (note) tag v0.1.0 is NOT at HEAD (there are commits beyond it)
```

## How do I keep release notes where I want them?

`notes_dir` accepts an absolute path, so notes can live in a central
docs home outside the repo (the central-notes-home pattern; a real
example is [examples/modal-victoriametrics-server.repolice.toml](../examples/modal-victoriametrics-server.repolice.toml)):

```toml
notes_dir = "/absolute/path/to/docs/release/packages/<slug>"
```

The guard searches `notes_dir` itself and one subdirectory per slug
(candidate spellings derive from the repo name, with `notes_candidates`
adding extras). `notes_glob` is the file pattern, default
`RELEASE-NOTES-{tag}.md`.

## How do the gates run in CI?

Two composite Actions ship with the kit
([actions/](../actions/)):

- `release-gates`: the gates as a PR required check.
- `tag-parity`: the published-state oracle on `release: published` and
  workflow dispatch.

The delivery model is vendoring: copy the kit into `tools/repo-guards/`
and the actions into `.github/actions/`, then
`uses: ./.github/actions/release-gates`. Cross-repo `uses:` references
to a private kit home are unsupported. Workflows must check out with
`fetch-depth: 0`: the parity and version-class guards need tags and
history.