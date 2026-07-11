---
title: Coding-Agent Discovery and Installer Targets
description: Dated primary-source and smoke-tested compatibility matrix for softschema instructions and Agent Skills across major coding agents.
author: Joshua Levy with Codex
---
# Research: Coding-Agent Discovery and Installer Targets

**Date:** 2026-07-09

**Author:** Joshua Levy with Codex

**Status:** Complete research and installer implementation; full activation testing
pending

**Normative target table:** `agent-targets-v1`

## Overview

softschema publishes repository instructions in `AGENTS.md` and an on-demand skill in
`SKILL.md`. Coding agents now overlap substantially on those formats, but they do not
agree on discovery roots, precedence, personal configuration, activation, or instruction
imports. An installer that treats every product as interchangeable will create silent
gaps or conflicting copies.

This brief defines a versioned installer target table and records the evidence behind
it. It covers Codex, Claude Code, Gemini CLI, GitHub Copilot cloud agent, code review,
CLI, and IDE surfaces, Cursor, Windsurf/Devin Desktop, OpenCode, Aider, Cline, and Roo
Code. The findings use current primary documentation reviewed on 2026-07-09 and bounded
local smoke checks where the corresponding product was installed.

The following labels are deliberate:

- **Documented** means a current first-party product or format source directly states
  the behavior.
- **Observed** means a local command or this repository demonstrated the behavior on the
  listed product version and operating system.
- **Decision** means the normative softschema installer or documentation behavior
  derived from the evidence.
- **Inference** means a reasoned interoperability conclusion that a vendor does not
  promise.

Documentation and an installed version are not activation tests.
An untested cell remains untested even when the underlying path is documented.

### Verification Inventory

Most vendors publish rolling documentation rather than a versioned compatibility
contract. The “documented surface” column therefore records the surface reviewed, while
“local version” records only software actually present on the research machine.

| Product | Documented surface reviewed | Local version or status | Last verified |
| --- | --- | --- | --- |
| Codex | CLI/app skills and hierarchical instructions | `codex-cli 0.135.0` | 2026-07-09 |
| Claude Code | CLI skills, memory, and configuration | `2.1.202` | 2026-07-09 |
| Gemini CLI | CLI skills, context files, and configuration | `0.42.0` | 2026-07-09 |
| GitHub Copilot | Cloud agent, code review, app, CLI, and IDE support matrix | Copilot CLI not installed; `gh 2.83.2`; VS Code `1.124.0`; local Copilot extensions not representative of current skills | 2026-07-09 |
| Cursor | Editor skills and rules | App `3.10.20` | 2026-07-09 |
| Windsurf / Devin Desktop | Editor skills, `AGENTS.md`, and global memory | Windsurf app `1.97.0` | 2026-07-09 |
| OpenCode | CLI skills, rules, and configuration | Not installed | 2026-07-09 |
| Aider | CLI conventions and configuration | Not installed | 2026-07-09 |
| Cline | IDE-extension skills, rules, and configuration | Not installed | 2026-07-09 |
| Roo Code | IDE-extension skills and custom instructions | Not installed | 2026-07-09 |

## Executive Conclusion

The current implicit project installation pair is the best portable default:

```text
.agents/skills/softschema/SKILL.md
.claude/skills/softschema/SKILL.md
```

The pair reaches every reviewed product with documented native Agent Skills support
except Aider:

- `.agents/skills` is documented by Codex, Gemini CLI, GitHub Copilot, Cursor,
  Windsurf/Devin Desktop, OpenCode, and Roo Code.
- `.claude/skills` is native to Claude Code and is also documented by GitHub Copilot,
  OpenCode, and Cline.
- Aider has no documented on-demand Agent Skills discovery surface.
  Its `--read` mechanism is an always-loaded convention file, not a skill.

**Inference:** this is documentation-level reach, not proof that every current product
build activates the skill correctly.
The observed subset and remaining activation work are recorded below.

Keep `AGENTS.md` as the canonical repository-instruction source.
Codex, GitHub Copilot cloud agent and current VS Code agent mode, Cursor, Windsurf/Devin
Desktop, OpenCode, Cline, and Roo Code read it directly.
Claude Code and Gemini CLI need deterministic native import files.
Aider needs explicit `read:` configuration.
GitHub Copilot code review is a separate surface and does not document `AGENTS.md`
support, so its native instruction file must be generated and drift-checked when that
surface matters.

**Decision:** implicit installation keeps the portable `.agents` plus `.claude` pair.
One or more explicit `--agent` selectors replace that pair with the selected native
targets. `--all-agents` means the nine documented native skill hosts in
`agent-targets-v1`; it does not include Aider.

## Normative Skill Targets

### `agent-targets-v1`

Every root below receives `softschema/SKILL.md`. For example, the Codex project
destination is `.agents/skills/softschema/SKILL.md`. `<home>` means the operating
system’s resolved user home, not a literal tilde.

| Selector | Project root | Personal root | Honored home override | Support note |
| --- | --- | --- | --- | --- |
| `codex` | `.agents/skills` | `<home>/.agents/skills` | None | Native, documented |
| `claude` | `.claude/skills` | `${CLAUDE_CONFIG_DIR}/skills`, otherwise `<home>/.claude/skills` | `CLAUDE_CONFIG_DIR` | Native, documented |
| `gemini` | `.gemini/skills` | `${GEMINI_CLI_HOME}/.gemini/skills`, otherwise `<home>/.gemini/skills` | `GEMINI_CLI_HOME` | Native, documented |
| `copilot` | `.github/skills` | `${COPILOT_HOME}/skills`, otherwise `<home>/.copilot/skills` | `COPILOT_HOME` | Native; personal root is local CLI/IDE only |
| `cursor` | `.cursor/skills` | `<home>/.cursor/skills` | None | Native, documented |
| `windsurf` | `.windsurf/skills` | `<home>/.codeium/windsurf/skills` | None | Native, documented; current docs redirect to Devin Desktop |
| `opencode` | `.opencode/skills` | `<home>/.config/opencode/skills` | None | Native, documented |
| `cline` | `.cline/skills` | `<home>/.cline/skills` | None | Native, documented |
| `roo` | `.roo/skills` | `<home>/.roo/skills` | None | Native, documented |
| `aider` | — | — | — | No documented native Agent Skills target |

The target choices favor each host’s native or highest-priority project root rather than
the widest portable root.
They are based on the official skill documentation for
[Codex](https://learn.chatgpt.com/docs/build-skills),
[Claude Code](https://code.claude.com/docs/en/slash-commands),
[Gemini CLI](https://geminicli.com/docs/cli/using-agent-skills/),
[GitHub Copilot](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills),
[Cursor](https://cursor.com/docs/skills),
[Windsurf/Devin Desktop](https://docs.devin.ai/desktop/cascade/skills),
[OpenCode](https://opencode.ai/docs/skills/),
[Cline](https://docs.cline.bot/customization/skills), and
[Roo Code](https://docs.roocode.com/features/skills).
Aider documents convention files and `--read`, but not Agent Skills; see
[Aider conventions](https://aider.chat/docs/usage/conventions.html) and
[configuration](https://aider.chat/docs/config/aider_conf.html).

### Target Semantics

The installer should implement these semantics as data, not conditionals dispersed
through CLI code:

- No selector and project scope writes the two implicit portable roots, `.agents/skills`
  and `.claude/skills`.
- Explicit selectors replace the implicit roots.
  `--agent codex --agent cursor`, for example, writes only `.agents/skills` and
  `.cursor/skills`.
- `--all-agents` expands to the nine supported selectors and canonicalizes destinations
  before writing. A destination is written once even if future target aliases converge.
- Global installation is explicit.
  It never follows from project installation and does not modify a cloud account.
- `--agent aider` is rejected with a stable unsupported-target diagnostic.
  The message points to the compatibility recipe described below.
- Target table version `agent-targets-v1` is recorded in installer output and a managed
  manifest so later path changes are auditable.
- Managed copies are byte-identical after the destination-specific managed marker.
  The installer should not rely on symlinks: support and trust behavior varies by host,
  version, operating system, and enterprise policy.

### Home and Operating-System Rules

**Decision:** resolve the actual user home through the host runtime and join the suffix
with native path APIs.
Do not hard-code `/Users`, `/home`, a drive letter, or literal `~` expansion.
Project destinations remain relative to the selected project root on every operating
system.

Only the three documented whole-home overrides in the target table affect managed
personal skill destinations:

- `CLAUDE_CONFIG_DIR` replaces Claude Code’s normal `~/.claude` directory, so the skill
  root is `<value>/skills`.
- `GEMINI_CLI_HOME` is the parent within which Gemini creates `.gemini`, so the skill
  root is `<value>/.gemini/skills`.
- `COPILOT_HOME` replaces Copilot CLI’s normal `~/.copilot` directory, so the skill root
  is `<value>/skills`.

Require an override used for writes to be an absolute, normalized path.
Resolve symlinks for containment checks where the platform permits it, refuse a
destination that escapes its selected root, and present the resolved path before a
global write.

Do not reinterpret unrelated variables:

- `CODEX_HOME` controls Codex configuration and instruction discovery, but current Codex
  skill documentation still names `$HOME/.agents/skills` as the personal skill root.
- `OPENCODE_CONFIG` selects a config file; it is not a documented skill-home override.
  The OpenCode config docs do not currently connect skill discovery to an alternate XDG
  home, so `agent-targets-v1` stays conservative.
- `CLINE_DATA_DIR` replaces Cline’s data directory, not `~/.cline/skills`.

These are target-table decisions, not claims that the products ignore those variables
for every other purpose.

## Instruction Compatibility

The project-instruction matrix separates native discovery from an adapter.
“Personal path” names a file-backed user surface where one is documented; a UI-only
surface is called out rather than invented as a filesystem path.

| Product surface | Project instructions | Personal instructions | Precedence or import behavior | softschema adapter decision |
| --- | --- | --- | --- | --- |
| Codex CLI/app | Root and nested `AGENTS.md`; optional `AGENTS.override.md` | `${CODEX_HOME}/AGENTS.md`, otherwise `<home>/.codex/AGENTS.md` | Global first, then repository root toward current directory; nearer files override | Use canonical `AGENTS.md`; no shim |
| Claude Code | Root/ancestor `CLAUDE.md` and `.claude/CLAUDE.md` | `${CLAUDE_CONFIG_DIR}/CLAUDE.md`, otherwise `<home>/.claude/CLAUDE.md` | `@path` imports are deterministic and relative to the importing file | Commit root `CLAUDE.md` containing `@AGENTS.md` |
| Gemini CLI | Hierarchical `GEMINI.md` by default | `${GEMINI_CLI_HOME}/.gemini/GEMINI.md`, otherwise `<home>/.gemini/GEMINI.md` | `@file` imports are supported; `context.fileName` can add alternate names | Commit root `GEMINI.md` containing `@./AGENTS.md` |
| Copilot cloud agent | Root or nested `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md`; also `.github/copilot-instructions.md` and path-specific instructions | GitHub account/organization surfaces, not a portable repository file | Nearest `AGENTS.md` wins for scoped agent instructions | Use canonical `AGENTS.md` |
| Copilot CLI / VS Code agent mode | `AGENTS.md`, `.github/copilot-instructions.md`, and path-specific instructions | `${COPILOT_HOME}/copilot-instructions.md`, otherwise `<home>/.copilot/copilot-instructions.md`, for CLI; IDE personal settings vary | Nearest `AGENTS.md` wins in supported IDE scope; CLI loads repository and personal instruction sources | Use canonical `AGENTS.md`; do not require a Copilot shim for agent mode |
| Copilot code review | `.github/copilot-instructions.md`; support for path-specific instructions varies by host | Organization policy and supported account surfaces | Current support matrix does not list `AGENTS.md` | Generate and drift-check `.github/copilot-instructions.md` when review coverage is required |
| Cursor | Root and nested `AGENTS.md`; Cursor project rules also supported | User Rules UI; no documented portable user-rule file | Parent instructions combine with nested instructions; more specific rules win | Use canonical `AGENTS.md`; no shim |
| Windsurf / Devin Desktop | Root and nested `AGENTS.md`; native Rules also supported | `<home>/.codeium/windsurf/memories/global_rules.md` | Root `AGENTS.md` is always on; nested files are scoped to their directories | Use canonical `AGENTS.md`; no shim |
| OpenCode | Project `AGENTS.md`; `CLAUDE.md` fallback | `<home>/.config/opencode/AGENTS.md`; `<home>/.claude/CLAUDE.md` fallback | Local category, then global, then Claude fallback; first matching file wins in each category | Use canonical `AGENTS.md`; no shim |
| Aider | Any file explicitly listed by `--read` or `read:` | `<home>/.aider.conf.yml` may configure `read:` | Config files load from home through repository/current directory, with later settings taking precedence | Document `.aider.conf.yml` with `read: AGENTS.md`; do not call it automatic discovery |
| Cline | Root `AGENTS.md`; native `.clinerules/` also supported | OS-specific Cline Rules directory, normally `<home>/Documents/Cline/Rules` | Workspace and global rules combine; workspace rules win conflicts | Use canonical root `AGENTS.md`; no shim |
| Roo Code | Root `AGENTS.md` or `AGENT.md`; native `.roo/rules/` also supported | `<home>/.roo/rules/` | Project instructions override global instructions | Use canonical root `AGENTS.md`; no shim |

Primary instruction sources are
[Codex `AGENTS.md`](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[Claude Code memory](https://code.claude.com/docs/en/memory),
[Gemini context files](https://geminicli.com/docs/cli/gemini-md/),
[GitHub’s feature-by-feature support matrix](https://docs.github.com/en/copilot/reference/custom-instructions-support),
[Copilot CLI’s configuration directory](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference),
[Cursor rules](https://cursor.com/docs/rules),
[Windsurf/Devin Desktop `AGENTS.md`](https://docs.windsurf.com/windsurf/cascade/agents-md),
[Windsurf global memories](https://docs.windsurf.com/windsurf/cascade/memories),
[OpenCode rules](https://opencode.ai/docs/rules/),
[Aider conventions](https://aider.chat/docs/usage/conventions.html),
[Cline rules](https://docs.cline.bot/customization/cline-rules), and
[Roo Code custom instructions](https://docs.roocode.com/features/custom-instructions).

### Adapter Consequences

Claude and Gemini have real import syntax, so their adapters can stay thin and
deterministic:

```markdown
<!-- CLAUDE.md -->
@AGENTS.md
```

```markdown
<!-- GEMINI.md -->
@./AGENTS.md
```

An instruction such as “please read `AGENTS.md`” is not equivalent to transclusion.
For OpenCode, the documented deterministic alternatives are native `AGENTS.md` or the
`instructions` array in `opencode.json`; Markdown references inside `AGENTS.md` are not
automatically parsed.

The GitHub support matrix is unusually important because “Copilot” is not one behavior.
Cloud agent and current VS Code agent mode document `AGENTS.md`; code review does not.
VS Code can include referenced Markdown instructions under its own settings, but that is
not evidence that GitHub’s cloud review service follows the same link.
**Decision:** do not ship a link-only `.github/copilot-instructions.md` and describe it
as code-review compatible.
Generate the relevant canonical content with a managed marker and fail a drift check
instead.

The Aider recipe is compatibility, not skill installation:

```yaml
# .aider.conf.yml
read:
  - AGENTS.md
```

Projects may instead list `.agents/skills/softschema/SKILL.md`, but Aider then loads the
entire file as a convention on each session rather than selecting it on demand.
That changes context cost and activation semantics, so the installer should not create
this configuration automatically.

## Skill Discovery and Activation

All native targets use the Agent Skills `SKILL.md` shape, but discovery and collisions
remain product-specific.

| Host | Documented project roots | Documented personal roots | Activation | Duplicate-name or precedence behavior |
| --- | --- | --- | --- | --- |
| Codex | `.agents/skills` from current directory through repository root | `<home>/.agents/skills` | Model selection from description; explicit skill UI/invocation also available | Same-named discoveries are not merged; duplicates can be surfaced separately |
| Claude Code | `.claude/skills` | `<home>/.claude/skills` or configured Claude home | Automatic selection or `/skill-name`; nested project skills discover as files enter scope | Enterprise > personal > project for same-name managed sources |
| Gemini CLI | `.gemini/skills`, `.agents/skills` | `<gemini-home>/.gemini/skills`, `<home>/.agents/skills` | Model selects, then Gemini asks the user before each activation | Built-in < extension < user < workspace; higher-precedence duplicate wins |
| Copilot cloud / review / app / CLI / IDE | `.github/skills`, `.agents/skills`, `.claude/skills` | `<copilot-home>/skills`, `<home>/.agents/skills` for local surfaces | Automatic selection; `/skills` is available on documented interactive surfaces | CLI order begins project `.github`, `.agents`, `.claude`, then parents, personal, plugins, built-ins |
| Cursor | `.cursor/skills`, `.agents/skills` | `<home>/.cursor/skills`, `<home>/.agents/skills` | Automatic selection or `/skill-name`; recursive discovery | Duplicate-name precedence is not documented in the reviewed source |
| Windsurf / Devin Desktop | `.windsurf/skills`, `.agents/skills`; `.claude/skills` when Claude compatibility is enabled | `<home>/.codeium/windsurf/skills`, `<home>/.agents/skills` | Automatic selection or `@` mention | Duplicate-name precedence is not documented in the reviewed source |
| OpenCode | `.opencode/skills`, `.claude/skills`, `.agents/skills` while walking to worktree root | `<home>/.config/opencode/skills`, `<home>/.claude/skills`, `<home>/.agents/skills` | On demand through the native `skill` tool, subject to permissions | Names must be unique; cross-root duplicate precedence is not documented in the reviewed source |
| Cline | `.cline/skills`, `.clinerules/skills`, `.claude/skills` | `<home>/.cline/skills` | Automatic selection or `/skill-name`; skills can be toggled | A same-named global skill overrides the project skill |
| Roo Code | `.roo/skills`, `.agents/skills`, including optional mode-specific subdirectories | `<home>/.roo/skills`, `<home>/.agents/skills` | Model selection from description; no direct manual skill invocation is documented | Project `.roo` mode, project `.roo`, project `.agents` mode, project `.agents`, then equivalent global roots |
| Aider | None | None | `--read` is always-loaded context, not on-demand activation | Not applicable |

The portable pair can be visible twice to Copilot and OpenCode because both scan
`.agents` and `.claude`. The current copies are intentionally identical, which reduces
behavioral risk but does not make undocumented collision handling portable.
**Decision:** the installer manifest records every managed copy and its content digest;
`doctor` treats identical managed duplicates as expected and reports divergent or
unmanaged duplicates as conflicts.

The [Agent Skills specification](https://agentskills.io/specification) requires `name`
and `description`, encourages progressive disclosure, and defines `allowed-tools` as an
experimental space-delimited string when a host supports it.
The reviewed source skill used a YAML list for `allowed-tools`. That was a portability
defect, not a target-table difference.
The current portable source omits the field; add it only if the project deliberately
adopts the standard string form and tests host behavior.

## Practical Smoke Evidence

The local environment was macOS in `/Users/levy/wrk/github/softschema`. These checks
demonstrate bounded discovery or file integrity; they do not replace the documented
matrix.

| Check | Product/version | Result | Evidence classification |
| --- | --- | --- | --- |
| Repository instruction discovery in the active task | Codex CLI/app `0.135.0` | This task received the repository `AGENTS.md` instructions | Observed instruction discovery |
| Project skill listing in the active task | Codex CLI/app `0.135.0` | `.agents/skills/softschema` appeared in the available-skills list | Observed discovery; activation not separately exercised |
| `gemini skills list --all` with workspace trust enabled | Gemini CLI `0.42.0` | Listed `.agents/skills/softschema/SKILL.md` from this repository | Observed discovery |
| Same Gemini command without workspace trust | Gemini CLI `0.42.0` | Skipped project skill discovery | Observed trust gate |
| Mirror integrity | Local files | `.agents/skills/softschema/SKILL.md` and `.claude/skills/softschema/SKILL.md` were byte-identical | Observed integrity |
| Managed source integrity | Local files | After removing the expected managed marker and its following blank line, the `.agents` copy matched `skills/softschema/SKILL.md` | Observed integrity |
| Installed but not activated | Claude Code `2.1.202` | Version recorded; no live discovery or activation result claimed | Environment inventory only |
| Installed but not activated | Cursor `3.10.20` | Application version recorded; no live discovery or activation result claimed | Environment inventory only |
| Installed but not activated | Windsurf `1.97.0` | Application version recorded; no live discovery or activation result claimed | Environment inventory only |
| Installed extension not used as current evidence | VS Code `1.124.0`; older local Copilot extensions | Versions recorded; extensions were too old for a representative current skill smoke | Environment inventory only |
| CLI too old for `gh skill` smoke | GitHub CLI `2.83.2` | Current GitHub docs require `gh` 2.90 or later for the public-preview command | Explicitly untested |
| Not installed locally | OpenCode, Aider, Cline, Roo Code | No local activation smoke | Explicitly untested |

The Gemini documentation currently notes a product transition for some user tiers, and
the Windsurf URLs currently redirect into Devin Desktop documentation.
Those are signs of product-surface volatility, not reasons to invent stable paths.
Re-run primary-source verification and the activation suite immediately before a release
that claims these targets.

## Required Follow-Up Tests

Path existence is not enough for a compatibility claim.
The release gate should run a small, non-destructive skill whose activation returns a
unique nonce and no filesystem mutation.
For each supported host and current stable version, capture:

1. clean-profile project discovery at the native explicit root;
2. clean-profile personal discovery at the documented personal root;
3. automatic activation from an unambiguous prompt;
4. manual activation where the host documents it;
5. collision behavior for identical and divergent same-name copies;
6. project-versus-personal precedence;
7. workspace trust or approval prompts;
8. the three supported home overrides, including spaces in paths;
9. macOS/Linux and Windows path resolution; and
10. uninstall behavior that preserves unmanaged files.

Record product version, operating system, invocation, exit status, redacted output, and
verification date.
Mark a target “documented, not observed” until the corresponding smoke
exists. Do not automate acceptance of destructive permissions merely to make activation
pass.

Claude Code’s current docs describe project-skill symlink support only in versions newer
than the local `2.1.202`, so the local inventory cannot validate that behavior.
GitHub’s `gh skill` command is public preview and requires a newer CLI than the local
one; it also adds provenance metadata.
If softschema later interoperates with `gh skill`, it should not let that metadata
silently break byte-exact managed copies.

## Strategic Improvements

### Make Compatibility Data-Driven

Keep the target table in the small versioned
`conformance/skill-installer/agent-targets-v1.yaml` artifact checked by both runtimes
and documentation. Each row records selector, project root, personal-root template, and
override semantics; the research records status, evidence URL, and verification date.
Python and TypeScript execute the same golden cases for expansion and errors.

This structure makes product churn a data review instead of duplicated control-flow
changes.
It also lets `softschema skill targets --json` report exactly what the installer
would do without writing.

### Separate Portable Defaults from Native Explicit Targets

The implicit pair optimizes reach and source control simplicity.
An explicit selector communicates a different intent: install into that product’s
native, high-priority location.
Keeping those modes distinct avoids surprising fan-out while preserving a strong
zero-configuration default.

Do not add a generic “every directory any host happens to scan” mode.
It creates many copies, amplifies collision ambiguity, and makes uninstall ownership
harder. `--all-agents` should remain the finite, versioned native target expansion.

### Add Explainable Diagnostics

`softschema skill doctor` should report, without mutating:

- the target-table version and sources last verified;
- resolved project and personal roots;
- which roots exist and which copies are managed;
- source and destination digests;
- duplicate names classified as identical managed, divergent managed, or unmanaged;
- unsupported selectors and compatibility recipes; and
- trust, version, or preview caveats known for the selected host.

Diagnostics should say “documented path found” or “content matched,” not “agent can use
the skill,” unless an activation smoke actually ran.

### Keep Instruction Adapters Deterministic

Use native `AGENTS.md` wherever documented.
Use real imports for Claude and Gemini.
For surfaces without verified imports, generate content and check drift rather than
depending on an agent to follow a prose link.
This distinction is especially important for GitHub Copilot code review, which runs
outside the local IDE configuration.

### Keep the Skill Portable and Small

Follow the common Agent Skills contract: strict `name` and `description`, ordinary
Markdown instructions, progressive references, and no host-only frontmatter in the
portable source. Move large examples and runtime-specific command tables into referenced
files that an agent loads only when needed.
Keep commands non-interactive, pin expected CLI behavior by softschema version, state
trust boundaries, and provide verification commands with observable success criteria.

The skill should distinguish three jobs clearly:

- author a contract or artifact;
- validate or consume an artifact; and
- change the softschema implementation itself.

The third path should route to repository development instructions and parity tests; it
should not burden ordinary artifact authors with package internals.

### Reverify Volatile Products at Release Time

Treat the verification date as release metadata, not prose that can silently age.
A release job should fail or require an explicit waiver when a target has neither a
recent primary-source review nor a supported-version activation smoke.
Preview commands, renamed products, and host-specific compatibility toggles should be
reported as capabilities, not assumed stable contracts.

## Primary Sources

The following primary sources were reviewed on 2026-07-09:

- Agent Skills: [format specification](https://agentskills.io/specification).
- Codex: [build skills](https://learn.chatgpt.com/docs/build-skills) and
  [`AGENTS.md` configuration](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
- Claude Code: [memory and instruction files](https://code.claude.com/docs/en/memory),
  [skills and slash commands](https://code.claude.com/docs/en/slash-commands), and
  [Claude directory configuration](https://code.claude.com/docs/en/claude-directory).
- Gemini CLI: [using Agent Skills](https://geminicli.com/docs/cli/using-agent-skills/),
  [creating skills](https://geminicli.com/docs/cli/creating-skills/),
  [context files](https://geminicli.com/docs/cli/gemini-md/), and
  [configuration](https://geminicli.com/docs/get-started/configuration-v1/).
- GitHub Copilot:
  [Agent Skills concept](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills),
  [add skills to cloud agent](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills),
  [custom-instruction support matrix](https://docs.github.com/en/copilot/reference/custom-instructions-support),
  [CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference),
  and
  [CLI configuration directory](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference).
- Cursor: [skills](https://cursor.com/docs/skills),
  [rules](https://cursor.com/docs/rules), and
  [2.4 changelog](https://cursor.com/changelog/2-4).
- Windsurf/Devin Desktop: [skills](https://docs.devin.ai/desktop/cascade/skills),
  [`AGENTS.md`](https://docs.windsurf.com/windsurf/cascade/agents-md), and
  [global memories](https://docs.windsurf.com/windsurf/cascade/memories).
- OpenCode: [skills](https://opencode.ai/docs/skills/),
  [rules](https://opencode.ai/docs/rules/), and
  [configuration](https://opencode.ai/docs/config/).
- Aider: [conventions](https://aider.chat/docs/usage/conventions.html) and
  [configuration files](https://aider.chat/docs/config/aider_conf.html).
- Cline: [skills](https://docs.cline.bot/customization/skills),
  [rules](https://docs.cline.bot/customization/cline-rules), and
  [configuration](https://docs.cline.bot/getting-started/config).
- Roo Code: [skills](https://docs.roocode.com/features/skills) and
  [custom instructions](https://docs.roocode.com/features/custom-instructions).

The community [AGENTS.md compatibility site](https://agents.md/) was used only as a
cross-check, not as primary evidence for a vendor capability.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
