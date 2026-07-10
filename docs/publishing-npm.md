---
name: publishing-npm-bootstrap
description: >-
  One-time npm setup for a package: the manual bootstrap publish that claims the
  package name, and the GitHub Actions Trusted Publisher (OIDC) configuration
  that lets every later release publish from CI with no token. Use when first
  publishing a package to npm, wiring trusted publishing, or when an agent is
  asked to help publish to npm. Covers npm auth options and the human-in-the-loop
  pattern: the agent prepares and verifies, while the user owns authentication
  and confirms every state-changing step.
---
# npm One-Time Bootstrap and Trusted Publisher Setup

> **TODO:** This runbook is written and validated for the **bun** toolchain
> (`bun install` and `bun run build`) with the **npm CLI** for auth and publish.
> Generalize it to cover **npm** and **pnpm** as well (their `install`, `build`, and
> `publish` equivalents and any auth differences, for example `bun publish` and
> `pnpm publish`). For now, follow the bun plus npm-CLI path documented here.

This runbook covers only the **one-time** npm setup: the first manual publish that
claims the package name on npm, and the Trusted Publisher configuration that lets every
later release publish from CI with no token.
For the ongoing, automated release flow (tagging a version and publishing on a bump),
see the project’s own release runbook; do not duplicate that here.

Substitute the placeholders for your project: `<package-name>` (the npm package name),
the GitHub `<org>/<repo>`, the publish workflow file `<workflow>.yml`, the package
directory (repo root, or a subdirectory such as `packages/<name>`), and the version
`X.Y.Z`.

## Why a Manual Bootstrap Is Needed

npm Trusted Publishing (OIDC) is configured on a package that **already exists**: you
select the package on npmjs.com and attach a GitHub Actions publisher.
A brand-new package is not on npm yet, so the trusted publisher cannot be set first.
The order is fixed:

1. Publish the first version by hand, authenticated as a maintainer.
2. Configure the trusted publisher on that now-existing package.
3. Every release after that publishes automatically from `<workflow>.yml` over OIDC.

Pick the bootstrap version deliberately: it is the first version that will exist on npm.
If the same package is also published to another registry (for example PyPI), bootstrap
at that registry’s current version so the two start in sync.

## Operating Mode (Agent and User Roles)

This is a human-in-the-loop runbook.
An agent does most of the work, but two things are always the user’s:

- **Authentication.** The agent never logs in or holds credentials.
  The user authenticates the npm CLI first (browser and 2FA), and the agent verifies the
  result.
- **Confirmation of every state-changing step.** The agent proposes the exact command,
  explains what it does and whether it is reversible, and waits for an explicit “yes”
  before that command runs.
  Read-only checks (for example `npm whoami`, `npm pack --dry-run`) may run as the agent
  narrates them; anything that writes to the registry is a hard stop.

**Publishing is irreversible and outward-facing.** A published version cannot be
re-published, and unpublishing is restricted and disruptive.
Treat `npm publish` as the highest-confirmation step: the agent prepares and presents
it, and by default the **user runs the publish command**. The agent runs it only if the
user explicitly authorizes that exact command and no one-time password is required (see
2FA below).

## npm Authentication Options (and Which to Use)

The npm CLI can authenticate several ways.
For a one-time manual bootstrap from a maintainer’s machine, prefer the first.

- **Web login (recommended): `npm login --auth-type=web`.** This is the default on npm 9
  and later. It opens a browser, authenticates through npmjs.com (including 2FA), and
  writes a session token to `~/.npmrc`. No long-lived secret to create or store, and it
  is revocable with `npm logout`. Best fit for an interactive, one-time publish.
- **Legacy login: `npm login --auth-type=legacy`.** Prompts for username, password, and
  OTP in the terminal.
  Avoid it: password-based auth is being retired and the web flow is cleaner.
- **Granular access token in `~/.npmrc` or `NODE_AUTH_TOKEN`.** A token created on
  npmjs.com (Access Tokens).
  An “automation” token bypasses 2FA, which suits CI but is a long-lived secret with
  real blast radius. Do not introduce a stored token for a one-time manual publish; the
  point of the trusted publisher is to avoid tokens afterward.
- **Trusted Publishing (OIDC).** No token at all; the GitHub Actions job proves its
  identity to npm. This is the end state configured in Phase 3, not a bootstrap option,
  because it needs the package to exist and runs only from CI.

Net: use `npm login` (web) for the bootstrap, then rely on OIDC for every release after.

## Phase 0: Pre-Flight (Agent, Read-Only)

The agent runs these and reports; none change anything.
Confirm each result before moving on.

1. **Name is free.**
   `curl -s -o /dev/null -w '%{http_code}' https://registry.npmjs.org/<package-name>`
   returns `404`. (A scoped name uses the URL-encoded form, for example
   `@scope%2Fname`.)

2. **Version is intended.** `node -p "require('./package.json').version"` (from the
   package directory) is the version you mean to claim.
   If dual-publishing, confirm it matches the other registry’s current version; verify
   that registry independently, do not assume.

3. **Build is clean and the tarball is right.** From the package directory:

   ```bash
   bun install --frozen-lockfile
   bun run check          # lint, types, tests (whatever the project's check script runs)
   bun run build          # produces the published dist/
   npm pack --dry-run --ignore-scripts  # inspect the already-built package inventory
   ```

4. **CLI or entry runs from the packed artifact** (recommended for a package with a
   `bin`). Pack, install into a throwaway directory, and run under plain node:

   ```bash
   tgz=$(npm pack --ignore-scripts | tail -1); abs="$PWD/$tgz"; tmp=$(mktemp -d)
   (cd "$tmp" && npm init -y >/dev/null && npm install --ignore-scripts "$abs" && node ./node_modules/<package-name>/<path-to-bin>.js --help); rm -rf "$tmp" "$abs"
   ```

   If a local supply-chain cool-off blocks installing recent dependencies, add
   `--before=2030-01-01` to that `npm install`. This affects only the local smoke test;
   Publishing the already packed tarball does not install dependencies, so the cool-off
   does not affect the real publish.

## Phase 1: Authenticate (User), Then Verify (Agent)

1. **Agent checks current state:** `npm whoami`. A `401`/`E401` means not logged in.

2. **User logs in** (the agent cannot do this; it is a browser and 2FA flow):

   ```bash
   npm login        # defaults to --auth-type=web
   ```

3. **Agent confirms:** `npm whoami` prints the maintainer account, and `npm profile get`
   shows the account details.

4. **Agent reads the 2FA mode** from `npm profile get` ("two-factor auth"), which
   decides who runs the publish:
   - **`auth-and-writes`:** `npm publish` requires a one-time password.
     The user runs the publish (or supplies `--otp=<code>`); the agent cannot enter the
     OTP.
   - **`auth-only` (or 2FA off):** the web session is enough; after explicit
     confirmation the agent may run the publish command, or the user runs it.

## Phase 2: Publish the First Version (Hard Confirmation Gate)

1. **Agent presents the exact command** and confirms scope and irreversibility.
   Run it **from the package directory, not the repo root**:

   ```bash
   cd <package-dir>          # e.g. packages/<name>; NOT the repo root
   tgz=$(npm pack --ignore-scripts | tail -1)
   npm publish "$tgz" --ignore-scripts --access public --no-provenance
   ```

   - **Directory matters.** `npm publish` packs the `package.json` in the current
     directory. In a monorepo the repo root is often a private tooling package
     (`"private": true`); publishing from there fails with `EPRIVATE` ("This package has
     been marked as private"). That error is a useful safety net, but it means you must
     `cd` into the actual package directory first.
     Keeping the repo root private is a deliberate guard against a wrong-directory
     publish.
   - `--access public` is required to publish a **scoped** package publicly and is
     harmless for an unscoped one.
   - `--no-provenance` is required here: provenance needs CI’s OIDC identity, which a
     local machine does not have.
     The automated releases add provenance later.
   - The explicit build and pack steps own the candidate bytes.
     `--ignore-scripts` keeps the publish from rebuilding or executing lifecycle code
     after review.

2. **Wait for explicit user confirmation.** Per the 2FA branch above, the user runs
   this, or authorizes the agent to run that exact command when no OTP is required.

3. **Agent verifies the publish:** `npm view <package-name> version` returns `X.Y.Z`,
   and `https://registry.npmjs.org/<package-name>` no longer returns `404`.

## Phase 3: Configure the Trusted Publisher (User, Web UI)

On npmjs.com, open the **package** then Settings then **Trusted Publishing**, add a
GitHub Actions publisher, and enter exactly:

| Field | Value |
| --- | --- |
| Publisher | GitHub Actions |
| Organization or user | `<org>` |
| Repository | `<repo>` |
| Workflow filename | `<workflow>.yml` |
| Environment | the exact protected environment used by the publish job |
| Allowed actions | `npm publish` only |

The workflow filename is the bare name, not a path, and it must match the file on the
default branch. The agent can confirm the repo side is correct (the publish job has
`id-token: write`, a pinned npm `>= 11.5.1`, and
`npm publish <tarball> --ignore-scripts --access public --provenance` gated to protected
tag pushes) but cannot fill in the npmjs.com form.

Optionally `npm logout` afterward if this was a shared machine.

## After the Bootstrap

The bootstrap version now exists on npm.
Do **not** re-run the release workflow for that same version; npm rejects a duplicate.
The next version bump is the first fully automated publish: it runs from
`<workflow>.yml` over OIDC (tokenless, with provenance), guarded so the tag and the
`package.json` version must match before anything uploads.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
