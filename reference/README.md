# Reference guards

Reference implementations of the release guards, for re-use in other
repos. Adapt in place per repo: they hardcode the system folder layout
and the GitHub slugs, so they need the paths swapped before use.

- `reference-tag-release-parity.sh` - the "published is testable" oracle:
  a tag without a release object/notes/version parity = exit 1.
- `reference-version-class.py` - the docs-only-bump rule: content class
  pins the bump class; the release script calls it before the squash.
- `reference-docs-guard.py` - the "rulings are testable" ledger:
  one `Check(rule, source, why, kind, targets, pattern)` row per ruling;
  kinds `absent` / `require` / `forbid` (require = plain path-exists;
  `glob().exists()` is an iterator bug). Exit-code oracle wired as a
  fail-closed pre-commit step. GUARD-PATTERNS GENERAL §9 + §10 carry the
  extraction notes + the vendored-config trap.

The prose gate + guide-drift patterns live as prose in
GUARD-PATTERNS-GENERAL.md: their reference implementations are too
family-shaped to copy cleanly.
