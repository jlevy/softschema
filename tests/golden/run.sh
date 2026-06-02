#!/usr/bin/env bash
# Run the shared golden corpus against one implementation.
#
#   SOFTSCHEMA_IMPL=py ./tests/golden/run.sh      # default: the Python CLI
#   SOFTSCHEMA_IMPL=ts ./tests/golden/run.sh      # the TypeScript CLI (once built)
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

case "$IMPL" in
  py)
    target="$REPO/.venv/bin/softschema-py"
    if [ ! -x "$target" ]; then
      echo "error: $target not found; run 'uv sync' first" >&2
      exit 1
    fi
    ;;
  ts)
    target="bun $REPO/packages/typescript/dist/cli.js"
    if [ ! -f "$REPO/packages/typescript/dist/cli.js" ]; then
      echo "error: TypeScript CLI not built; run 'bunup' in packages/typescript first" >&2
      exit 1
    fi
    ;;
  *)
    echo "error: unknown SOFTSCHEMA_IMPL=$IMPL (expected py or ts)" >&2
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
# Shared neutral scenarios run on both implementations; scenarios-$IMPL/ holds
# the per-implementation scenarios (e.g. compile, whose invocation differs by
# language even though its output is identical). nullglob so an empty per-impl
# directory simply contributes no files.
shopt -s nullglob
files=("$REPO"/tests/golden/scenarios/*.md "$REPO"/tests/golden/scenarios-"$IMPL"/*.md)
if command -v bunx >/dev/null 2>&1; then
  exec bunx tryscript@latest run "${files[@]}"
fi
exec npx -y tryscript@latest run "${files[@]}"
