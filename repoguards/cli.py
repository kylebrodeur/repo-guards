"""CLI: `guv` - the guards' entry point.

guv check   <path> [--except parity,prose]   run every gate
guv release <path> <version> [--cut]         the release flow (dry by default)
guv init    <path>                           write a starter .repolice.toml
"""

import argparse
from pathlib import Path

from repoguards import ci, lockfile_parity, parity, prose, release, version_class
from repoguards.config import DEFAULT_CONFIG_NAMES, Config, version_on_disk

GUARDS = {
    "parity": parity,
    "version_class": version_class,
    "lockfile_parity": lockfile_parity,
    "prose": prose,
    "ci": ci,
}


def cmd_check(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    cfg = Config.load(repo)
    skip = set((args.except_ or "").split(",")) - {""}
    disk = version_on_disk(repo, cfg)
    failures = 0
    for name, guard in GUARDS.items():
        if name in skip:
            continue
        # version-class needs a REQUESTED version: in check-all mode it
        # runs only for a RELEASE CANDIDATE. Checking the disk version
        # against itself is meaningless (it IS the last tag); the finding
        # is a NOTE: unreleased content exists (release flow picks it).
        if name == "version_class":
            from repoguards.config import latest_tag

            if not disk or disk.lstrip("v") == (latest_tag(repo) or "").lstrip("v"):
                print("  version_class: (skipped: no release candidate; use the release flow)")
                continue
            result = guard.check(repo, cfg, disk)
        else:
            result = guard.check(repo, cfg)
        state = "ok" if result else "FAIL"
        print(f"  {name}: {state}")
        for finding in result.findings:
            print(f"    - {finding}")
        failures += 0 if result else 1
    return 1 if failures else 0


def cmd_release(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    cfg = Config.load(repo)
    ok = release.run(repo, cfg, args.version, dry_run=not args.cut, yes=args.cut)
    return 0 if ok else 1


def cmd_init(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    target = repo / DEFAULT_CONFIG_NAMES[0]
    if target.exists() and not args.force:
        print(f"refusing: {target} exists (--force to overwrite)")
        return 1
    target.write_text(_STARTER)
    print(f"wrote {target}; edit owner/notes_dir/version_files/ci to the repo's reality")
    return 0


_STARTER = """# repo-guards config (guv): edit to the repo's reality
owner = ""                # or derived from the origin remote
repo = ""                 # or the directory's GitHub name

notes_dir = "docs/releases"
notes_glob = "RELEASE-NOTES-{tag}.md"
version_files = ["pyproject.toml"]   # add server/pyproject.toml for multiproject
require_v_prefix = true

# ci = [                      # the VERBATIM commands from .github/workflows/ci.yml
#   "uv run pytest tests -q",
#   "uv run ruff check .",
# ]
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="guv", description="repo-guards: repo-discipline guards")
    sub = parser.add_subparsers(dest="command", required=True)
    check_p = sub.add_parser("check", help="run every gate")
    check_p.add_argument("path", nargs="?", default=".")
    check_p.add_argument("--except", dest="except_", help="comma-separated guard names to skip")
    check_p.set_defaults(func=cmd_check)
    release_p = sub.add_parser("release", help="the release flow (gates -> tag -> gh release -> parity)")
    release_p.add_argument("path")
    release_p.add_argument("version")
    release_p.add_argument("--cut", action="store_true", help="actually write (default: dry run)")
    release_p.set_defaults(func=cmd_release)
    init_p = sub.add_parser("init", help="write a starter config")
    init_p.add_argument("path")
    init_p.add_argument("--force", action="store_true")
    init_p.set_defaults(func=cmd_init)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
