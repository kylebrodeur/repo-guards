#!/bin/sh
# Tag-without-release guard for a family of repos.
#
# Usage:  reference-tag-release-parity.sh <repo> [<repo> ...]
#
# The rule it enforces: every ANNOTATED release tag pushed to origin MUST
# have a GitHub release object carrying that tag, and a source notes file.
#
# Caught live: a lane pushed the tag and the code but never ran
# `gh release create`, so the "published" claim was false. The tag had no
# release body and nothing announced it. A fail-closed release discipline
# prevents a repeat.
#
# Exit 0 = every local release tag has (a) an origin tag, (b) a GitHub
#          release with a nonempty body, (c) a source notes file.
# Exit 1 = at least one violation (stderr explains). Fix it before claiming
#          anything was "released".
#
# ADAPT BEFORE USE. Two things are set to this repo's own conventions and
# a consumer swaps them for its own:
#
#   * NOTES_DIR       where the source notes live.
#   * OWNER           the GitHub owner, for the release lookup.
#   * SLUG_FUNCS      how a repo name maps to a notes directory name. The
#                     one here strips a product prefix and a "-server"
#                     suffix, and accepts any spelling that exists on disk,
#                     because a family's package names do not always match
#                     its repo names.
set -eu

OWNER="${OWNER:-kylebrodeur}"
NOTES_DIR="${NOTES_DIR:-docs/release/packages}"
SYSTEM="$(cd "$(dirname "$0")/../.." && pwd)"

if [ "$#" -eq 0 ]; then
  echo "usage: $0 <repo> [<repo> ...]" >&2
  echo "  pass the repos to check; this reference does not guess the family." >&2
  exit 2
fi

# The candidate directory names for a repo. A family strips a product
# prefix and a "-server" suffix in different places, and a repo whose
# folder name is not its package name needs the fallback, so every
# spelling that exists on disk is accepted.
SLUG_FUNCS='
slug_candidates() {
  base="$1"
  stripped="${base%-server}"
  echo "$base" "$stripped" "$base-server" "$stripped-server"
}'

notes_candidates() {
  # shellcheck disable=SC2086
  eval "$SLUG_FUNCS"
  slug_candidates "$1"
}

find_notes() {
  repo="$1"; tag="$2"
  for slug in $(notes_candidates "$repo"); do
    f="$SYSTEM/$NOTES_DIR/$slug/RELEASE-NOTES-$tag.md"
    [ -f "$f" ] && { echo "$f"; return 0; }
  done
  return 1
}

fail=0
for repo in "$@"; do
  case "$repo" in
    /*) dir="$repo" ;;
    *) dir="$PWD/$repo" ;;
  esac
  [ -d "$dir/.git" ] || dir="$SYSTEM/$repo"
  [ -d "$dir/.git" ] || { echo "tag-release-parity: $repo is not a git checkout, skipped" >&2; continue; }

  # Only the newest ANNOTATED release tag (vX.Y.Z).
  latest="$(git -C "$dir" tag -l 'v*' --sort=-v:refname | head -1)"
  [ -n "$latest" ] || { echo "tag-release-parity: $repo has no release tags, skipped" >&2; continue; }

  # (a) the tag resolves to a commit that is an ancestor of origin/main.
  #     A tag of unpushed work also counts as not published.
  target="$(git -C "$dir" rev-parse "$latest^{commit}" 2>/dev/null || true)"
  if ! git -C "$dir" fetch -q origin 2>/dev/null; then
    echo "tag-release-parity: $repo: cannot fetch origin - REFUSED" >&2; fail=1; continue
  fi
  if [ -z "$target" ] || ! git -C "$dir" merge-base --is-ancestor "$target" origin/main 2>/dev/null; then
    echo "tag-release-parity: $repo $latest: tag target is NOT on origin/main (unpushed work)" >&2
    fail=1
  fi

  # (b) a GitHub release object with a nonempty body.
  if ! command -v gh >/dev/null 2>&1; then
    echo "tag-release-parity: gh not available - cannot verify releases, REFUSED" >&2; fail=1; continue
  fi
  body_file="$(mktemp)"
  if ! gh release view "$latest" --repo "$OWNER/$repo" --json body >"$body_file" 2>/dev/null; then
    echo "tag-release-parity: $repo $latest: tag EXISTS but NO GitHub release - run gh release create $latest --repo $OWNER/$repo --notes-file ..." >&2
    fail=1
  else
    if ! jq -e '.body | length > 40' >/dev/null 2>&1 <"$body_file"; then
      echo "tag-release-parity: $repo $latest: GitHub release has an EMPTY/template body - fix with gh release edit $latest --notes-file ..." >&2
      fail=1
    fi
  fi
  rm -f "$body_file"

  # (c) a source notes file, at any candidate slug spelling.
  if ! find_notes "$repo" "$latest" >/dev/null; then
    echo "tag-release-parity: $repo $latest: no source notes file at $NOTES_DIR/{$(notes_candidates "$repo" | tr ' ' '|')}/RELEASE-NOTES-$latest.md (write notes here FIRST)" >&2
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  echo "tag-release-parity: FAIL - a tag exists without a real release; do not claim 'published'" >&2
  exit 1
fi
echo "tag-release-parity: OK - every release tag has a GitHub release with real notes"
