#!/bin/sh
# A runnable example: run the gates against a throwaway repo and show
# what a green run and a red run look like.
#
# It creates its own repo in a temp directory, so it touches nothing
# outside it and needs no network.
#
# Usage:  sh examples/demo-run.sh
set -eu

KIT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

REPO="$WORK/demo-repo"
mkdir -p "$REPO"
cd "$REPO"

# A minimal repo the gates can read.
git init -q .
git config user.email "demo@example.invalid"
git config user.name "Demo"

cat > pyproject.toml <<'EOF'
[project]
name = "demo-repo"
version = "0.1.0"
EOF

cat > .repolice.toml <<'EOF'
owner = "demo-owner"
repo = "demo-repo"
notes_dir = "docs/releases"
version_files = ["pyproject.toml"]
ci = ["git log --oneline -1"]
EOF

# A doc with a forbidden character, so the prose gate has something to
# find. The prose gate is the one gate that needs no network and no
# published tag, so it is the one this example exercises.
#
# The character is an em dash, written with a printf escape so this
# file itself does not carry one.
printf '# demo-repo\n\nA demo repo with an em dash \xe2\x80\x94 in its README,\nso the prose gate finds it.\n' > README.md

git add -A
git commit -qm "initial"

echo "== the gates, on a repo with a forbidden character"
set +e
uv run --project "$KIT" guv check "$REPO" --except parity
CODE=$?
set -e
echo "   the exit: $CODE"
echo
echo "The prose gate found the em dash, named the file and the line, and"
echo "refused. The exit code is non-zero, so a release flow stops there."
echo
echo "== the same repo, with the character removed"
printf '# demo-repo\n\nA demo repo with a comma, in its README,\nso the prose gate finds nothing.\n' > README.md
git add -A
git commit -qm "fix the prose"
set +e
uv run --project "$KIT" guv check "$REPO" --except parity
CODE=$?
set -e
echo "   the exit: $CODE"
echo
echo "Same repo, same gates, one character changed: the run is green."
echo
echo "The parity gate is excluded because it checks a PUBLISHED tag on"
echo "GitHub, and this demo repo has never been published. Run it"
echo "against a real repo to exercise it."
