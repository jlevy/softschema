#!/usr/bin/env python3
"""Run the shared golden corpus against one implementation.

    SOFTSCHEMA_IMPL=py     ./tests/golden/run_golden_tests.py   # Python CLI (default)
    SOFTSCHEMA_IMPL=ts     ./tests/golden/run_golden_tests.py   # TypeScript CLI under Node
    SOFTSCHEMA_IMPL=ts-bun ./tests/golden/run_golden_tests.py   # TypeScript CLI under Bun

`ts` runs the built CLI under **Node**, the runtime npm users actually get via
`npx softschema`; `ts-bun` runs the same bundle under Bun. The shared journeys prove the
published runtime, while `cross-impl-diff.sh` compares machine JSON structurally.

The scenarios invoke `$SOFTSCHEMA`, and this script is what sets it. That indirection is
the whole switching mechanism: one corpus, three runtimes, nothing generated. It is also
tryscript's documented way to name an exact executable — `path:` can only prepend a
directory to `PATH`, so pointing the *name* `softschema` at a chosen build would take a
wrapper script written to a temp directory on every run.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests" / "golden"
TRYSCRIPT = "tryscript@0.2.1"

SCENARIO_GLOB = "*.tryscript.md"
"""Scenario files carry tryscript's own suffix.

Fixtures under `fixtures/` are plain `.md`, so this glob cannot pick one up by accident,
and a stray `README.md` in a scenario directory is not fed to tryscript as a test.
"""


@dataclass(frozen=True)
class Implementation:
    """One runtime under test: what `$SOFTSCHEMA` resolves to, and its scenarios.

    `perimpl_dirs` holds scenarios whose *invocation* differs by language (compile,
    `validate --model`) even though their output is identical. Both TypeScript runtimes
    share `scenarios-ts/`, which is Node-safe. Bun additionally runs `scenarios-ts-bun/`,
    whose `compile` scenario imports a TypeScript model module that only a TS-capable
    runtime can load — plain Node cannot import a `.ts` file's `.js`-specified deps, so
    compile is proven under Bun and by the cross-language conformance unit test, while
    every runtime command still runs under Node too.
    """

    command: list[str]
    perimpl_dirs: tuple[str, ...]
    missing_build: str

    @property
    def binary(self) -> Path:
        """The build artifact whose absence means "you have not built this yet"."""
        return Path(self.command[-1])


def fail(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def resolve(impl: str) -> Implementation:
    """The implementation named by `SOFTSCHEMA_IMPL`, or exit with what to run first."""
    if impl == "py":
        return Implementation(
            command=[str(REPO / ".venv/bin/softschema-py")],
            perimpl_dirs=("scenarios-py",),
            missing_build="run 'uv sync' first",
        )
    if impl in ("ts", "ts-bun"):
        return Implementation(
            command=[
                "node" if impl == "ts" else "bun",
                str(REPO / "packages/typescript/dist/cli.js"),
            ],
            perimpl_dirs=("scenarios-ts",)
            if impl == "ts"
            else ("scenarios-ts", "scenarios-ts-bun"),
            missing_build="run 'bun run build' in packages/typescript first",
        )
    fail(f"unknown SOFTSCHEMA_IMPL={impl} (expected py, ts, or ts-bun)")


def scenarios(directory: Path) -> list[Path]:
    """Every scenario in one directory, sorted so the run order is deterministic."""
    return sorted(directory.glob(SCENARIO_GLOB))


def collect(implementation: Implementation) -> list[Path]:
    """The corpus for this implementation: the neutral set plus its per-impl directories.

    Both sets are checked non-empty. tryscript itself exits non-zero when *nothing* matches,
    but it is handed one combined list and cannot know a directory was meant to contribute:
    a typo or a bad rename in `scenarios-ts/` alone would still leave the neutral set to
    report a healthy green.
    """
    neutral = scenarios(GOLDEN / "scenarios")
    if not neutral:
        fail(f"no scenarios found in tests/golden/scenarios (expected {SCENARIO_GLOB})")

    perimpl = [path for name in implementation.perimpl_dirs for path in scenarios(GOLDEN / name)]
    if not perimpl:
        joined = " ".join(implementation.perimpl_dirs)
        fail(f"no scenarios found in {joined} (expected {SCENARIO_GLOB})")

    return neutral + perimpl


def tryscript_runner() -> list[str]:
    """`bunx` when it is available, else `npx`, which needs `-y` to skip its prompt."""
    if shutil.which("bunx"):
        return ["bunx", TRYSCRIPT, "run"]
    return ["npx", "-y", TRYSCRIPT, "run"]


def main() -> int:
    impl = os.environ.get("SOFTSCHEMA_IMPL", "py")
    implementation = resolve(impl)

    if not implementation.binary.exists():
        fail(f"{implementation.binary} not found; {implementation.missing_build}")

    # `$SOFTSCHEMA` is expanded by the scenario's shell, so its words are split there and
    # a path containing whitespace would be read as two arguments. Say that here rather
    # than leaving a checkout under "My Documents" to fail as a mystery parse error.
    target = " ".join(implementation.command)
    if len(target.split()) != len(implementation.command):
        fail(f"repository path contains whitespace, which $SOFTSCHEMA cannot carry: {REPO}")

    files = collect(implementation)
    print(f"Running golden corpus against SOFTSCHEMA_IMPL={impl} ($SOFTSCHEMA={target})")

    environment = {**os.environ, "SOFTSCHEMA": target}
    command = [*tryscript_runner(), *(str(path) for path in files)]
    return subprocess.run(command, env=environment, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
