# Reference guards

Reference implementations of the release guards, for re-use in other
repos. Adapt in place per repo: they carry this repo's own folder layout
and GitHub slugs, so they need the paths swapped before use.

- `reference-tag-release-parity.sh` - the "published is testable" oracle:
  a tag without a release object/notes/version parity = exit 1. Pass the
  repos to check; it does not guess the family. `OWNER` and `NOTES_DIR`
  are the two knobs.
- `reference-version-class.py` - the docs-only-bump rule: content class
  pins the bump class; the release script calls it before the squash.
  `DOC_PATHS` is the knob.
- `reference-docs-guard.py` - the "rulings are testable" ledger:
  one `Check(rule, source, why, kind, targets, pattern)` row per ruling;
  kinds `absent` / `require` / `forbid` (require = plain path-exists;
  `glob().exists()` is an iterator bug). Exit-code oracle wired as a
  fail-closed pre-commit step. The checks in it are EXAMPLES: they show
  the shape of a ruling ledger, and a consumer replaces them with its own
  rulings.

The prose gate and the guide-drift patterns live as prose in
`GUARD-PATTERNS-GENERAL.md`: their reference implementations are too
family-shaped to copy cleanly.
