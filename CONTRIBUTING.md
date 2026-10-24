# Contributing to repo-guards

## The setup

The kit is Python 3.11+, stdlib only, tooling via `uv`:

```bash
git clone https://github.com/kylebrodeur/repo-guards
cd repo-guards
uv sync --group dev
uv run pytest tests -q
```

Expected output:

```
........................................                                 [100%]
40 passed in 6s (timing varies)
```

No network and no `gh` are needed: the tests build synthetic git repos
in temporary directories through a fixture (`tests/conftest.py`).

## The gates (this repo guards itself)

```bash
uv run guv check . --except parity
```

(`parity` needs the network and a published state; everything else runs
locally. Expected: every gate `ok`, with `version_class` self-skipped
and `parity` excepted.)

```bash
uv run ruff check .
```

Expected: `All checks passed!`

## Ground rules

- **Stdlib only.** No runtime dependencies; `gh` and `uv` are invoked
  as CLIs. A dependency needs a written reason, not convenience.
- **Every guard is a pure function** over `(repo_path, config)`
  returning `CheckResult(ok, findings)`. Guard functions do not print;
  the CLI prints.
- **Fail-closed.** A missing file, an empty config field, or an
  unavailable tool is a finding, never a silent pass.
- **Findings carry their fix.** A finding names the command that
  resolves it (`git push origin <tag>`, `uv lock in <dir>`).
- **No AI slop in comments or docs.** Describe why code exists, not
  what it does. Prose carries no em/en dashes and none of the banned
  filler words; the kit's own prose gate enforces this fail-closed on
  every tracked markdown file, including these.
- **Tests are contracts.** A guard change lands with a test that fails
  before and passes after (the 40-test suite is the kit's own
  acceptance).

## Workflow

1. Fork, create a feature branch.
2. Set up per the block above.
3. Run the repo's CI commands locally before submitting; they are
   exactly what `.github/workflows/ci.yml` runs (`pytest` + `ruff`).
4. Open a pull request against `main` describing what and why.

## Doc changes

This repo follows the AI ECP documentation standard (README, AGENTS.md,
the skill, quickstart, how-to, runbook, and the health files). Before a
commit that adds or moves a doc:

```bash
uv run pytest tests -q
uv run ruff check .
```

Require every `repo-guards:` line to read PASS.

## Security

Do not open public issues for security vulnerabilities. See
[SECURITY.md](SECURITY.md) for the private reporting path.

## License

Apache-2.0. By contributing you agree your contributions are licensed
under the project's license.