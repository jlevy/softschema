#!/usr/bin/env bash
# Direct cross-implementation parity check: run the SAME neutral commands through the
# Python CLI (softschema-py) and the TypeScript CLI under Node (the published runtime),
# and byte-compare stdout + exit code. Unlike the golden corpus (which compares each
# implementation against committed expected files), this reports a divergence AS a
# py-vs-ts difference, so a parity break is attributed directly rather than surfacing as
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

# Compare stdout + exit code of one neutral invocation across both CLIs.
diff_cmd() {
  local desc="$1"
  shift
  local pout pcode tout tcode
  pout=$("$PY" "$@" 2>/dev/null)
  pcode=$?
  tout=$("${TS[@]}" "$@" 2>/dev/null)
  tcode=$?
  if [ "$pout" = "$tout" ] && [ "$pcode" = "$tcode" ]; then
    echo "ok   (exit $pcode)  $desc"
  else
    echo "DIFF (py exit $pcode, ts exit $tcode)  $desc"
    diff <(printf '%s\n' "$pout") <(printf '%s\n' "$tout") | head -40
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
echo "cross-impl parity OK (Python vs TypeScript/Node byte-identical)"
