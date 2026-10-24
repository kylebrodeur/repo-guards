# repo-guards: repo-discipline guards + release flow

A config-driven kit for repos where agents (and humans) write code and
releases: every "trusted" claim about a repo becomes an exit code.

**Start with [docs/quickstart.md](docs/quickstart.md)**: from nothing to
a guarded repo. Day-to-day operation: [docs/how-to.md](docs/how-to.md).
The full command surface and every error string with its fix:
[docs/RUNBOOK.md](docs/RUNBOOK.md).

## Install

The kit is not in a package registry yet. From a checkout or a vendored
copy (facts checked 2026-10-22 against `uv` and `guv` 0.1.0):

```bash
uv tool install --from <path-to-kit> repo-guards   # package name, not the script name
# or, editable (what the composite Actions use):
uv tool install -e <path-to-kit>
# or run without installing:
uv run --project <path-to-kit> guv check .
```

`<path-to-kit>` is the directory holding this repo's `pyproject.toml`.

    guv check <path> [--except ...]       every gate, red = do not release
    guv release <path> vX.Y.Z [--cut]     the flow (dry run default)
    guv init <path>                       a starter config to edit

## The gates

| Gate | Refuses when |
|---|---|
| `parity` | the latest tag is not pushed or not on main, has no GitHub release body, no source notes, or the version on disk disagrees (a tag beyond HEAD is an info note, not a failure) |
| `version_class` | docs-only content claims minor or major; code claims a lower or equal version |
| `lockfile_parity` | a lockfile's self-version lags its pyproject; version files disagree |
| `prose` | banned characters or words in tracked markdown (rule-citation lines exempt via skip patterns) |
| `ci` | the config's VERBATIM CI commands fail |

## The release flow

`guv release <repo> vX.Y.Z` runs the gates in order, verifies the
release notes exist FIRST, then (only with `--cut`) tags + pushes +
`gh release create` + the parity oracle. Dry by default: nothing writes
on red and nothing writes without `--cut`.

## Config (`<repo>/.repolice.toml`)

```toml
owner = ""                       # or derived from origin
repo = ""                        # or the dir's GitHub name
notes_dir = "docs/releases"      # absolute paths OK (a central notes home)
notes_glob = "RELEASE-NOTES-{tag}.md"
version_files = ["pyproject.toml", "server/pyproject.toml"]
require_v_prefix = true
docs_paths = [...]               # version-class's docs set (defaults sane)
prose_banned = [...]             # chars/words (defaults: em/en/minus + slop words)
prose_skip_patterns = [...]      # rule-citation lines that NAME the words
ci = ["uv run pytest tests -q"]  # the VERBATIM ci.yml commands
notes_candidates = [...]         # extra slugs for the notes search
```

## Actions (see actions/)

- `release-gates`: the gates as a PR required-check composite action.
- `tag-parity`: the oracle on `release: published` + dispatch.
- `example-workflow.yml`: the full wiring (fetch-depth 0 REQUIRED: the
  parity + version-class guards need tags + history).
- **Delivery model (the supported path): vendor it.** Copy the kit into
  `tools/repo-guards/` and the actions into `.github/actions/`, then
  `uses: ./.github/actions/release-gates`. Cross-repo `uses:` refs are
  NOT supported (Actions cannot check out a private kit without an
  access token). The composites resolve the kit vendored-first and fail
  LOUD on a missing source (never a swallowed install followed by a
  command-not-found); installs are uv-native
  (`astral-sh/setup-uv@v7`, the family CI standard).

## Tests

40 contract tests (no gh, no network; synthetic git repos via a
fixture):

```bash
uv run pytest tests -q
```

Live-verified against the family's real repos (both repo shapes) with
the same config.

## Config loading

`Config.load` resolves, in order: the `REPOLICE_CONFIG` env var (a
missing env-named file is a clear error), then `.repolice.toml` /
`repolice.toml` at the repo root. A real-world example (the
central-notes-home pattern with an absolute path) is in
[examples/](examples/).

## The skills

Two, each teaching one boundary:

- [skills/repo-guards/SKILL.md](skills/repo-guards/SKILL.md): operating
  the gates in a wired repo (this repo ships it).
- the `repo-guards-setup` MANAGED skill (`~/.omp/agent/managed-skills/`):
  wiring a repo onto the guards (config generation, gate verification,
  Actions wiring, the real-wave traps).

## Family

This kit is a member of the AI Engineering Control Plane (AI ECP)
family: independent kit repos whose rules are executable. Siblings:
[ecp-toolkit](https://github.com/kylebrodeur/ecp-toolkit) (the `ecp`
control-plane CLI), [actions-runner](https://github.com/kylebrodeur/actions-runner)
(the `arun` local agent-pipeline runner), and
[omp-rpc-cli](https://github.com/kylebrodeur/omp-rpc-cli) (persistent
`omp` RPC sessions). The family's standard:
the family documentation standard (in the private control-plane repo).

## Origin

Proven in this family's ops layer (guards born 2026-10-09
through 2026-10-14, each after a real failure); generalized
2026-10-15. The patterns' WHY: GUARD-PATTERNS-GENERAL.md (the parent
workshop's index).