#!/usr/bin/env bash
# Direct cross-implementation parity check: run the SAME neutral commands through the
# Python CLI (softschema-py) and the TypeScript CLI under Node (the published runtime),
# and compare stdout + exit code. JSON output is compared structurally; human-readable
# output remains exact. This attributes a parity break directly instead of surfacing as
# one side drifting from the golden files.
#
#   ./tests/golden/cross-impl-diff.sh
#
# Requires `.venv/bin/softschema-py` (uv sync) and a built TypeScript dist
# (bun run build in packages/typescript).
set -uo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$REPO"

PY="$REPO/.venv/bin/softschema-py"
TS=(node "$REPO/packages/typescript/dist/cli.js")

if [ ! -x "$PY" ]; then
  echo "error: $PY not found; run 'uv sync' first" >&2
  exit 1
fi
if [ ! -f "$REPO/packages/typescript/dist/cli.js" ]; then
  echo "error: TypeScript CLI not built; run 'bun run build' in packages/typescript first" >&2
  exit 1
fi

export NO_COLOR=1
fail=0

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required for structural JSON comparison" >&2
  exit 1
fi

normalize_json() {
  jq --sort-keys --compact-output . 2>/dev/null
}

outputs_match() {
  local left="$1" right="$2" left_json right_json
  if left_json=$(printf '%s\n' "$left" | normalize_json) &&
    right_json=$(printf '%s\n' "$right" | normalize_json); then
    [ "$left_json" = "$right_json" ]
  else
    [ "$left" = "$right" ]
  fi
}

render_for_diff() {
  local output="$1" normalized
  if normalized=$(printf '%s\n' "$output" | normalize_json); then
    printf '%s\n' "$normalized"
  else
    printf '%s\n' "$output"
  fi
}

# Guard the comparison rule itself: JSON object order is not part of the public
# contract, including for integer-like keys whose host ordering rules differ.
if ! outputs_match '{"10":"ten","2":"two"}' '{"2":"two","10":"ten"}'; then
  echo "error: structural JSON comparison is not order-independent" >&2
  exit 1
fi

# Compare stdout + exit code of one neutral invocation across both CLIs.
diff_cmd() {
  local desc="$1"
  shift
  local pout pcode tout tcode
  pout=$("$PY" "$@" 2>/dev/null)
  pcode=$?
  tout=$("${TS[@]}" "$@" 2>/dev/null)
  tcode=$?
  if outputs_match "$pout" "$tout" && [ "$pcode" = "$tcode" ]; then
    echo "ok   (exit $pcode)  $desc"
  else
    echo "DIFF (py exit $pcode, ts exit $tcode)  $desc"
    diff <(render_for_diff "$pout") <(render_for_diff "$tout") | head -40
    fail=1
  fi
}

MOVIE=examples/movie_page/spirited-away.md
SCHEMA=examples/movie_page/movie-page.schema.yaml
BAD=tests/golden/fixtures/bad-movie.md

diff_cmd "validate (structural ok)"          validate "$MOVIE" --schema "$SCHEMA" --envelope movie
diff_cmd "validate (structural fail)"        validate "$BAD" --schema "$SCHEMA" --contract example.movies:MoviePage/v1 --envelope movie
diff_cmd "validate (status override warn)"   validate "$MOVIE" --schema "$SCHEMA" --envelope movie --status permissive
diff_cmd "validate (envelope mismatch)"      validate "$MOVIE" --schema "$SCHEMA" --envelope nope
diff_cmd "inspect (movie)"                   inspect "$MOVIE"
diff_cmd "inspect (plain doc)"               inspect tests/golden/fixtures/plain-doc.md
diff_cmd "inspect (no frontmatter)"          inspect tests/golden/fixtures/no-frontmatter.md
diff_cmd "docs --list"                       docs --list
diff_cmd "docs --list --json"                docs --list --json
diff_cmd "docs guide"                        docs guide
diff_cmd "docs spec"                         docs spec
diff_cmd "skill"                             skill
diff_cmd "skill --brief"                     skill --brief
diff_cmd "prime"                             prime
diff_cmd "generate --check (no drift)"       generate examples/movie_page/README.md --check
diff_cmd "generate --check (drift)"          generate tests/golden/fixtures/stale-generated.md --check
diff_cmd "generate (missing file, exit 2)"   generate tests/golden/fixtures/does-not-exist.md
diff_cmd "validate (metadata-only, soft stage)" validate tests/golden/fixtures/extra-field-permissive.md
diff_cmd "validate (enforced overlay rejects extras)" validate tests/golden/fixtures/extra-field-permissive.md --schema tests/golden/fixtures/lenient.schema.yaml --status enforced
diff_cmd "validate (document-declared enforced)" validate tests/golden/fixtures/extra-field-enforced.md --schema tests/golden/fixtures/lenient.schema.yaml

if [ "$fail" -ne 0 ]; then
  echo "cross-impl parity FAILED" >&2
  exit 1
fi
echo "cross-impl parity OK (Python vs TypeScript/Node semantically equal)"
