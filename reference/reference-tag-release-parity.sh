#!/bin/sh
# Tag-without-release guard for a family of repos (PRIVATE system tooling).
#
# Usage:  tools/guards/tag-release-parity.sh [repo ...]
#         (bare: checks ALL tracked family repos)
#
# The rule it enforces (AGENTS.md convention 8, hardened 2026-10-11):
# every ANNOTATED release tag pushed to origin MUST have a GitHub
# release object carrying that tag, and a source notes file in
# docs/release/packages/<slug>/RELEASE-NOTES-<tag>.md.
#
# Caught live (2026-10-10): vault v1.5.0 landed as tag-only; the writing-duo
# lane pushed the tag + code but never ran `gh release create`, so the
# "published" claim was false - the tag had no release body and nothing
# announced it. Fail-closed release discipline prevents a repeat.
#
# Exit 0 = every local release tag has (a) origin tag, (b) GH release with
#          a nonempty body, (c) a source notes file.
# Exit 1 = at least one violation (stderr explains). Fix before claiming
#          anything was "released".
set -eu

SYSTEM="$(cd "$(dirname "$0")/../.." && pwd)"
REPOS="${*:-}"

if [ -z "$REPOS" ]; then
  for r in example-embedding-server example-inference-server example-vision-server \
           example-finetune-server example-vault-server example-toolkit example-shared-libs; do
    [ -d "$SYSTEM/$r" ] && REPOS="$REPOS $r"
  done
fi

fail=0
notes_candidates() {
  # Family convention: strip BOTH "example-" and "-server" - but the on-disk
  # packages/ home is MIXED (embedding/inference/vision/finetune use the
  # bare stripped word; vault exists as BOTH "vault" and "vault-server";
  # shared-libs keeps "example-shared-libs"), so accept any spelling that
  # exists on disk.
  base="${1#example-}"
  stripped="${base%-server}"
  echo "$base" "$stripped" "$base-server" "example-$base" "$stripped-server" "example-$stripped"
}
find_notes() {
  repo="$1"; tag="$2"
  for slug in $(notes_candidates "$repo"); do
    f="$SYSTEM/docs/release/packages/$slug/RELEASE-NOTES-$tag.md"
    [ -f "$f" ] && { echo "$f"; return 0; }
  done
  return 1
}

for repo in $REPOS; do
  case "$repo" in
    /*) dir="$repo" ;;
    *) dir="$PWD/$repo" ;;
  esac
  [ -d "$dir/.git" ] || dir="$SYSTEM/$repo"   # family-name form (example-vault-server)
  [ -d "$dir/.git" ] || { echo "tag-release-parity: $repo is not a git checkout, skipped" >&2; continue; }

  # Only ANNOTATED tags that are also local release tags (vX.Y.Z).
  tags="$(git -C "$dir" tag -l 'v*' --sort=-v:refname | head -1)"
  [ -n "$tags" ] || { echo "tag-release-parity: $repo has no release tags, skipped" >&2; continue; }

  latest="$(printf '%s' "$tags" | sed -n 1p)"

  # (a) tag resolves to a commit that is an ancestor of origin/main
  #     (tag-of-unpushed-work also counts as not published).
  objtype="$(git -C "$dir" cat-file -t "$latest" 2>/dev/null || true)"
  target="$(git -C "$dir" rev-parse "$latest^{commit}" 2>/dev/null || true)"
  if ! git -C "$dir" fetch -q origin 2>/dev/null; then
    echo "tag-release-parity: $repo: cannot fetch origin - REFUSED" >&2; fail=1; continue
  fi
  if [ -z "$target" ] || ! git -C "$dir" merge-base --is-ancestor "$target" origin/main 2>/dev/null; then
    echo "tag-release-parity: $repo $latest: tag target is NOT on origin/main (unpushed work)" >&2
    fail=1
  fi

  # (b) GitHub release object with a nonempty body.
  if ! command -v gh >/dev/null 2>&1; then
    echo "tag-release-parity: gh not available - cannot verify releases, REFUSED" >&2; fail=1; continue
  fi
  if ! gh release view "$latest" --repo "kylebrodeur/$repo" --json body >/tmp/trp-body.$$ 2>/dev/null; then
    echo "tag-release-parity: $repo $latest: tag EXISTS but NO GitHub release - run gh release create $latest --repo kylebrodeur/$repo --notes-file ..." >&2
    fail=1
  else
    if ! jq -e '.body | length > 40' >/dev/null 2>&1 </tmp/trp-body.$$; then
      echo "tag-release-parity: $repo $latest: GitHub release has an EMPTY/template body - fix with gh release edit $latest --notes-file ..." >&2
      fail=1
    fi
    rm -f /tmp/trp-body.$$
  fi

  # (c) source notes file (any candidate slug spelling).
  if ! notes_dir="$(find_notes "$repo" "$latest")"; then
    echo "tag-release-parity: $repo $latest: no source notes file at docs/release/packages/{$(notes_candidates "$repo" | tr ' ' '|')}/RELEASE-NOTES-$latest.md (write notes here FIRST)" >&2
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  echo "tag-release-parity: FAIL - a tag exists without a real release; do not claim 'published'" >&2
  exit 1
fi
echo "tag-release-parity: OK - every release tag has a GitHub release with real notes"