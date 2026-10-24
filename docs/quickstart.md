# Quickstart: from nothing to a guarded repo

Checked against `guv` 0.1.0 on 2026-10-22. Every command is real; every
output shown is real output from the commands above it.

You need: Python 3.11 or newer, `uv`, `git`, and (for the release flow
only) the `gh` CLI signed in to GitHub.

## 1. Get the kit

The kit is not published to a package registry yet. From a checkout or
a vendored copy:

```bash
uv tool install --from "git+https://github.com/kylebrodeur/repo-guards@v0.1.3" repo-guards
```

Or run it straight from a checkout without installing:

```bash
uv run --project /path/to/repo-guards guv --help
```

Expected output (the same for both forms):

```
usage: guv [-h] {check,release,init} ...

repo-guards: repo-discipline guards

positional arguments:
  {check,release,init}
    check               run every gate
    release             the release flow (gates -> tag -> gh release ->
                        parity)
    init                write a starter config

options:
  -h, --help            show this help message and exit
```

## 2. Generate a config in YOUR repo

```bash
guv init /path/to/your-repo
```

Expected output:

```
wrote /path/to/your-repo/.repolice.toml; edit owner/notes_dir/version_files/ci to the repo's reality
```

Running init again refuses (this is a guard, not an accident):

```
refusing: /path/to/your-repo/.repolice.toml exists (--force to overwrite)
```

## 3. Edit the config to the repo's truth

Open `<your-repo>/.repolice.toml` and set:

```toml
owner = "your-github-owner"      # or "" to derive it from the origin remote
repo = "your-repo-name"          # or "" to use the directory's name
version_files = ["pyproject.toml"]
ci = [
  "uv run pytest tests -q",
  "uv run ruff check .",
]
```

The `ci` entries must be the VERBATIM commands from your
`.github/workflows/ci.yml`, not similar ones. An empty `ci` list is a
gate failure by itself:

```
  ci: FAIL
    - no `ci` commands in the config (add them; mirror .github/workflows/ci.yml)
```

With `owner` empty and no GitHub origin remote, the config load fails
named:

```
ValueError: config: owner unset and origin remote does not name a GitHub owner
```

## 4. Run the gates

```bash
guv check /path/to/your-repo
```

A green repo (with the parity gate satisfied) looks like:

```
  parity: ok
  version_class: (skipped: no release candidate; use the release flow)
  lockfile_parity: ok
  prose: ok
  ci: ok
```

Exit code 0. Exit code 1 is "do not release".

Common first-run failures and what they mean:

```
  ci: FAIL
    - no `ci` commands in the config (add them; mirror .github/workflows/ci.yml)
```

Fill in the `ci` list (step 3).

```
FileNotFoundError: no config (.repolice.toml, repolice.toml) in /path/to/your-repo
```

Run `guv init` in that repo first (step 2).

## 5. Cut a release

Write the source notes first, at the notes location the config declares
(default `docs/releases/<repo-slug>/`):

```bash
mkdir -p docs/releases/your-repo-name
$EDITOR docs/releases/your-repo-name/RELEASE-NOTES-v0.1.1.md
```

Then the flow, dry run first (the default is dry; nothing writes):

```bash
guv release /path/to/your-repo v0.1.1
```

Expected output:

```
== gates ok
== tag: v0.1.1 at HEAD (be1b840)
== release notes source: docs/releases/your-repo-name/RELEASE-NOTES-v0.1.1.md
== dry run: stopping before the write
```

When every line is understood, cut:

```bash
guv release /path/to/your-repo v0.1.1 --cut
```

The flow tags HEAD, pushes the tag, runs
`gh release create --notes-file`, then reruns the parity gate. The final
line on success:

```
== published: your-github-owner/your-repo-name v0.1.1 (parity ok)
```

Two refusals you will meet early:

```
REFUSED: source notes missing (docs/releases/<slug>/RELEASE-NOTES-v0.1.1.md): write notes FIRST
```

```
REFUSED at gate: version-class:
  - docs-only content (2 files) but v0.2.0 changes major.minor (last v0.1.1): PATCH bump only
```

The second one is the content rule: docs-only changes take a PATCH
bump. Bump the patch number or add the code change the minor claims.

## 6. Where to go next

Day-to-day operation (the tasks you repeat):
[docs/how-to.md](how-to.md). The full command surface, every error
string, and the recovery procedures: [docs/RUNBOOK.md](RUNBOOK.md).