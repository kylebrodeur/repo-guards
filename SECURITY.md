# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| latest tag | yes |
| older tags | best effort (backport security fixes as needed) |

## Reporting a Vulnerability

**Do not open a public issue for a security vulnerability.**

Use GitHub's **Private Vulnerability Reporting** to reach the
maintainer:

1. Go to the **Security** tab in this repository.
2. Click **"Report a vulnerability."**
3. Describe the issue, a reproduction path, and the affected version or
   tag.

You receive an acknowledgment within 72 hours. If you do not hear back,
follow up via the contact info on the maintainer's profile.

## Scope notes for repo-guards

The kit is a local CLI (`guv`) plus two GitHub Actions composites. Its
trust boundaries, and the reports that are most welcome:

- **Command execution:** the `ci` gate runs the config's commands with
  `shell=True` from the repo root, and the release flow shells out to
  `git` and `gh`. Anything that reaches those strings from an
  untrusted source (a config file, an env var, a repo you do not own)
  is in scope.
- **Config resolution:** `REPOLICE_CONFIG` and the repo-root config
  files determine what runs. A path where an attacker-supplied config
  gets loaded is in scope.
- **The Actions surfaces:** the vendored-first kit-source resolution in
  the composites, and anything that lets a third-party repo pull from
  the kit's home without credentials.
- **Git and `gh` invocation:** argument construction for the
  subprocess calls; every value the kit passes must be exactly the
  configured or user-supplied value, never interpolated from a
  surprising source.

The prose gate's banned-word list is a style gate, not a security
boundary; reports about it are style feedback, not vulnerabilities.

## Disclosure Process

- Reports are triaged, confirmed, and fixed.
- Coordinated disclosure applies (60 to 120 days typical embargo).
- The reporter is credited in the security advisory and release notes
  unless anonymity is preferred.