#!/usr/bin/env bash
# Run the shared golden corpus against one implementation.
#
#   SOFTSCHEMA_IMPL=py     ./tests/golden/run.sh   # the Python CLI (default)
#   SOFTSCHEMA_IMPL=ts     ./tests/golden/run.sh   # the TypeScript CLI under Node
#   SOFTSCHEMA_IMPL=ts-bun ./tests/golden/run.sh   # the TypeScript CLI under Bun
#
# `ts` runs the built CLI under **Node**, the runtime npm users actually get via
# `npx softschema`; `ts-bun` runs the same bundle under Bun. The shared journeys prove
# the published runtime, while cross-impl-diff.sh compares machine JSON structurally.
#
# The scenarios invoke the neutral `softschema` command. This script builds a
# one-file shim directory that points `softschema` at the chosen implementation
# and exposes it to tryscript via $SOFTSCHEMA_BIN_DIR (referenced in each
# scenario's `path:` frontmatter).
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
IMPL=${SOFTSCHEMA_IMPL:-py}

SHIM=$(mktemp -d)
trap 'rm -rf "$SHIM"' EXIT

# Per-implementation scenario directories (beyond the neutral set). The TS
# runtimes share scenarios-ts/ (per-impl scenarios that are Node-safe, e.g.
# `validate --model` against a plain .mjs Zod model). Bun additionally runs
# scenarios-ts-bun/, whose `compile` scenario imports a TypeScript model module
# that only a TS-capable runtime (Bun, tsx) can load; plain Node cannot import a
# `.ts` file's `.js`-specified deps, so compile is proven under Bun and by the
# cross-language conformance unit test, while every runtime command (validate,
# inspect, docs, skill, generate, --version) runs under Node too.
perimpl_dirs=()

case "$IMPL" in
  py)
    target="$REPO/.venv/bin/softschema-py"
    if [ ! -x "$target" ]; then
      echo "error: $target not found; run 'uv sync' first" >&2
      exit 1
    fi
    perimpl_dirs=("scenarios-py")
    ;;
  ts | ts-bun)
    if [ ! -f "$REPO/packages/typescript/dist/cli.js" ]; then
      echo "error: TypeScript CLI not built; run 'bun run build' in packages/typescript first" >&2
      exit 1
    fi
    if [ "$IMPL" = "ts" ]; then
      target="node $REPO/packages/typescript/dist/cli.js"
      perimpl_dirs=("scenarios-ts")
    else
      target="bun $REPO/packages/typescript/dist/cli.js"
      perimpl_dirs=("scenarios-ts" "scenarios-ts-bun")
    fi
    ;;
  *)
    echo "error: unknown SOFTSCHEMA_IMPL=$IMPL (expected py, ts, or ts-bun)" >&2
    exit 1
    ;;
esac

cat > "$SHIM/softschema" <<EOF
#!/usr/bin/env bash
exec $target "\$@"
EOF
chmod +x "$SHIM/softschema"

export SOFTSCHEMA_BIN_DIR="$SHIM"
echo "Running golden corpus against SOFTSCHEMA_IMPL=$IMPL ($target)"
# Shared neutral scenarios run on every runtime; the per-impl directories hold
# scenarios whose invocation differs by language (e.g. compile, validate --model)
# even though their output is identical. nullglob so an empty directory simply
# contributes no files.
shopt -s nullglob
neutral=("$REPO"/tests/golden/scenarios/*.md)
perimpl=()
for dir in "${perimpl_dirs[@]}"; do
  perimpl+=("$REPO"/tests/golden/"$dir"/*.md)
done
# Guard against a per-impl scenario set silently vanishing: the always-present neutral
# glob would otherwise keep the run non-empty and pass, hiding lost per-impl coverage.
if [ ${#perimpl[@]} -eq 0 ]; then
  echo "error: no scenarios found in ${perimpl_dirs[*]} (expected at least one)" >&2
  exit 1
fi
files=("${neutral[@]}" "${perimpl[@]}")
if command -v bunx >/dev/null 2>&1; then
  exec bunx tryscript@0.1.7 run "${files[@]}"
fi
exec npx -y tryscript@0.1.7 run "${files[@]}"
