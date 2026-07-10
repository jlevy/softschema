# Coding-Agent Compatibility

softschema uses two open, complementary surfaces:

- `AGENTS.md` contains always-on repository development instructions.
- `SKILL.md` is an on-demand routing skill for authoring, consuming, and validating
  softschema artifacts.

Products overlap on these formats but differ in discovery roots, imports, precedence,
and activation. This document records the supported integration without treating a
documented path as proof of live activation.

**Last primary-source review:** 2026-07-09

**Target table:** `agent-targets-v1`

The full evidence, product versions, precedence details, home overrides, smoke results,
and primary sources are in the dated
[coding-agent discovery research](project/research/research-2026-07-09-coding-agent-discovery.md).

## Evidence Labels

- **Documented:** current first-party documentation states the behavior.
- **Observed:** a named local product version demonstrated the behavior on the research
  date.
- **Not observed:** the path may be documented, but no representative live discovery or
  activation smoke was run.

Documentation, installation, and activation are separate facts.
The matrix does not upgrade “Documented” to “Observed” by inference.

## Portable Project Default

A project install with no agent selector writes two managed copies:

<!-- BEGIN SOFTSCHEMA CLAIM agent-target-table -->
```text
.agents/skills/softschema/SKILL.md
.claude/skills/softschema/SKILL.md
```

The pair gives documented native skill discovery to every reviewed Agent Skills host
except Aider. The copies are byte-identical after their destination-independent managed
marker. A host that scans both may surface the name twice; divergent or unmanaged
duplicates are conflicts rather than candidates to overwrite.

Preview the resolved scope, ownership, and action for every target:

```bash
softschema skill --install --project --dry-run --text
```

One or more `--agent NAME` selectors replace the default pair.
`--all-agents` expands to the nine native skill hosts in the table and excludes Aider,
which has no documented Agent Skills target.

## Compatibility Matrix

| Product | Repository instructions | Project skill root | Integration status |
| --- | --- | --- | --- |
| Codex | Native root and nested `AGENTS.md` | `.agents/skills` | Instructions and project skill discovery observed with Codex CLI/app 0.135.0; automatic activation not separately observed |
| Claude Code | `CLAUDE.md` with native `@AGENTS.md` import | `.claude/skills` | Documented; Claude Code 2.1.202 was installed, but representative discovery and activation were not observed |
| Gemini CLI | `GEMINI.md` with native `@./AGENTS.md` import | `.gemini/skills` or portable `.agents/skills` | Portable project discovery observed with Gemini CLI 0.42.0 when workspace trust was enabled; activation not observed |
| GitHub Copilot cloud/CLI/IDE | Native `AGENTS.md` where supported | `.github/skills`, `.agents/skills`, or `.claude/skills` | Documented across product-specific surfaces; representative current activation not observed |
| GitHub Copilot code review | Generated `.github/copilot-instructions.md` | `.github/skills` | Native instruction file documented; generated content is drift-checked because code review does not document `AGENTS.md` support |
| Cursor | Native root and nested `AGENTS.md` | `.cursor/skills` or `.agents/skills` | Documented; Cursor 3.10.20 was installed, but discovery and activation were not observed |
| Windsurf / Devin Desktop | Native root and nested `AGENTS.md` | `.windsurf/skills` or `.agents/skills` | Documented; Windsurf 1.97.0 was installed, but discovery and activation were not observed |
| OpenCode | Native project `AGENTS.md` | `.opencode/skills`, `.claude/skills`, or `.agents/skills` | Documented, not observed locally |
| Aider | Explicit `--read` or `read:` configuration | None | Compatibility recipe only; always-loaded context is not Agent Skills activation |
| Cline | Native root `AGENTS.md` | `.cline/skills`, `.clinerules/skills`, or `.claude/skills` | Documented, not observed locally |
| Roo Code | Native root `AGENTS.md` or `AGENT.md` | `.roo/skills` or `.agents/skills` | Documented, not observed locally |

Product documentation moves independently of softschema.
Reverify primary sources and run current stable-version activation smokes before a
release claims more than the evidence above.

## Native Skill Selectors

Explicit selectors write the native high-priority location instead of fanning out to
every compatible alias:

| Selector | Project root | Personal root | Personal-home override |
| --- | --- | --- | --- |
| `codex` | `.agents/skills` | `<home>/.agents/skills` | None |
| `claude` | `.claude/skills` | `<home>/.claude/skills` | `CLAUDE_CONFIG_DIR` replaces `<home>/.claude` |
| `gemini` | `.gemini/skills` | `<home>/.gemini/skills` | `GEMINI_CLI_HOME` is the parent of `.gemini` |
| `copilot` | `.github/skills` | `<home>/.copilot/skills` | `COPILOT_HOME` replaces `<home>/.copilot` |
| `cursor` | `.cursor/skills` | `<home>/.cursor/skills` | None |
| `windsurf` | `.windsurf/skills` | `<home>/.codeium/windsurf/skills` | None |
| `opencode` | `.opencode/skills` | `<home>/.config/opencode/skills` | None |
| `cline` | `.cline/skills` | `<home>/.cline/skills` | None |
| `roo` | `.roo/skills` | `<home>/.roo/skills` | None |

Aider has no documented native Agent Skills target.
<!-- END SOFTSCHEMA CLAIM agent-target-table -->

Global installation is explicit, uses the process’s actual home, and requires one or
more selectors or `--all-agents`. An override used for a write must be absolute.
Each resolved base receives its own containment, ownership, and lock checks.

`CODEX_HOME`, `OPENCODE_CONFIG`, and `CLINE_DATA_DIR` affect other product state but are
not documented personal skill-root replacements in `agent-targets-v1`.

## Repository Instruction Adapters

`AGENTS.md` is the source.
The repository commits three adapters:

- `CLAUDE.md` contains Claude Code’s real `@AGENTS.md` import.
- `GEMINI.md` contains Gemini CLI’s real `@./AGENTS.md` import.
- `.github/copilot-instructions.md` is a generated copy for Copilot code review, whose
  current support matrix does not promise `AGENTS.md` discovery.

The Copilot file is generated rather than link-only because Markdown links are not an
instruction import. `devtools/sync_agent_instructions.py --check` fails if any adapter
drifts. Products that read `AGENTS.md` natively do not get redundant shims.

### Aider

Aider has no documented on-demand Agent Skills loader.
Add the repository instructions explicitly when desired:

```yaml
# .aider.conf.yml
read:
  - AGENTS.md
```

Do not call this automatic discovery.
Listing the skill itself under `read:` would load its complete body on every session
rather than selecting it on demand.

## Skill Activation and Safety

The source skill follows the Agent Skills contract: directory and `name` agree, the
description states capabilities and triggers, and the body routes to CLI help and
bundled docs.
It omits `allowed-tools` because no minimal portable grant covers the local
command plus all pinned fallback runtimes.

Skill content and tool output are executable influence.
Review third-party or modified copies, use `--dry-run`, and refuse any install plan that
targets an unexpected project or personal root.
softschema updates only absent, identical, or byte-exact known prior emissions.
It does not offer a force-overwrite flag for unmanaged content.

The repository’s activation fixture includes shared positive and negative prompts and
records availability or observations for all ten named products.
It records unavailable observations as unavailable; it does not turn a fixture into a
live product test.

## Primary Product Sources

- [Agent Skills specification](https://agentskills.io/specification)
- [Codex skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code skills](https://code.claude.com/docs/en/slash-commands)
- [Gemini CLI skills](https://geminicli.com/docs/cli/using-agent-skills/)
- [GitHub Copilot Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)
- [Cursor skills](https://cursor.com/docs/skills)
- [Windsurf / Devin Desktop skills](https://docs.devin.ai/desktop/cascade/skills)
- [OpenCode skills](https://opencode.ai/docs/skills/)
- [Aider conventions](https://aider.chat/docs/usage/conventions.html)
- [Cline skills](https://docs.cline.bot/customization/skills)
- [Roo Code skills](https://docs.roocode.com/features/skills)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
