#!/usr/bin/env python3
"""Differential search: ruamel's C parser against pure ruamel, where the guards let it run.

``parse_yaml`` reads a text with libyaml only when ``_needs_pure_parser`` finds none of the
shapes on which libyaml is known to accept what pure ruamel rejects, or to read a different
value. That guard list is empirical, so it has to be searched again after any ruamel,
``ruamel.yaml.clib`` or libyaml bump. This script is that search: it generates block and
flow documents with every scalar style, indicator, escape and line-break form, mutates
them, mixes in short random strings, and compares the C reading with the pure reading of
every text the guard lets through. A divergence is a text libyaml read to a value that
pure ruamel rejects or reads differently; the fix is a new guard, never a change to the
pure result.

Run it from the repo root with the C extension installed (the dev group installs it).
``SOFTSCHEMA_PURE_YAML`` does not change the search: the two readers are called directly,
whichever one ``parse_yaml`` would use, and the summary line reports the build gate, not
the switch:

    uv run python devtools/yaml_parser_fuzz.py 200000
    uv run python devtools/yaml_parser_fuzz.py 1000000 --seed 7 --jobs 4

Exit status is 1 when any divergence is found, 2 without the C parser. The count is
split into batches of ``--batch`` texts, one seed each, with a partial last batch. The
unit tests in ``packages/python/tests/test_c_parser.py`` run a small deterministic
corpus of the same kind on every CI run; this script is the larger search behind them.

Pairs this search has been run on with no divergence: ruamel.yaml 0.19.1 with
ruamel.yaml.clib 0.2.15 (CPython 3.13 and 3.14, Linux and macOS, about 3 million texts
across the reviews of the change that introduced C-first) and ruamel.yaml 0.18.10 with
ruamel.yaml.clib 0.2.8 (CPython 3.12, about 260,000 texts). Both report libyaml 0.1.7.
Rerun it, and widen ``CHECKED_LIBYAML_VERSION`` or ``CHECKED_RUAMEL_VERSIONS`` only
afterwards, when either package moves.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import math
import multiprocessing
import random
import sys
from collections.abc import Iterator
from typing import Any

import ruamel.yaml
from ruamel.yaml import YAML
from ruamel.yaml.parser import Parser as RuamelParser

from softschema._portable import (
    _C_PARSER_AVAILABLE,
    PortableInputError,
    _installed_libyaml_version,
    _needs_pure_parser,
    _parse_with,
)


def _distribution_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


Outcome = tuple[Any, ...]

ALPHABET = [*"ab01 \n\r:-#\"'[]{},?\\%|>!&*.~=<@`/xe+", " ", " ", "\n", "a", ":"]

WORDS = [
    "a", "b c", "x:y", "yes", "No", "on", "OFF", "y", "n", "012", "0o12", "0x1f", "0b101",
    "1_000", "190:20:30", "1e3", "1E3", "1.5e+3", ".5", "+.inf", "-.Inf", ".NaN", "~", "null",
    "Null", "NULL", "true", "True", "TRUE", "=", "<<", "2001-12-14t21:59:43.10-05:00",
    "2002-12-14", "-1", "+1", "0", "-0", "00", "08", "0.", "1.", "1,000", "12:30", "http://x/y",
    "a#b", "a #b", "-x", "?x", ":x", "x:", "x -", "é", "中文", "\U0001f600", "...",
    "---x", "a  b", "a\\b", "@", "%", "`", "!", "&", "*", "|", ">",
]  # fmt: skip

ESCAPES = [
    "\\n", "\\0", "\\a", "\\b", "\\e", "\\f", "\\r", "\\v", "\\ ", '\\"', "\\/", "\\N", "\\_",
    "\\L", "\\P", "\\x0A", "\\x7f", "\\u2028", "\\U0010FFFF", "\\U00110000", "\\x", "\\u12",
    "\\\n", "\\\n  x", "\\\r\n x",
]  # fmt: skip

BLOCK_HEADERS = ["|", ">", "|-", ">+", "|1", "|2", ">1-", "|+2", "|-1", "> # c", "|  #c"]

PREFIXES = ["", "", "", "---\n", "--- ", "# c\n", "\n", "---\n# c\n", "--- # c\n", "#" * 30 + "\n"]
SUFFIXES = ["", "", "...\n", "\n\n", "# end", " ", "---\n", "... # c\n", "...", "\n---"]


def outcome(text: str, *, pure: bool) -> Outcome:
    try:
        return ("value", _parse_with(text, pure=pure))
    except PortableInputError as exc:
        return ("error", exc.code, str(exc))
    except Exception as exc:
        # Any other exception is also a reading the two parsers must share.
        return ("exception", type(exc).__name__, str(exc))


def same(left: Any, right: Any) -> bool:
    """Equal in type, key order and float bits, which ``==`` does not check."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(same(left[key], right[key]) for key in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(map(same, left, right))
    if isinstance(left, float):
        return left.hex() == right.hex() or (math.isnan(left) and math.isnan(right))
    return left == right


class Generator:
    """Seeded block and flow documents that mix every shape the two scanners disagree on."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def scalar(self, *, flow: bool, indent: int) -> str:
        rng = self.rng
        word = rng.choice(WORDS)
        style = rng.random()
        if style < 0.45:
            if rng.random() < 0.2:
                pad = " " * rng.choice([0, indent, indent + 1, indent + 2])
                word = f"{word}\n{pad}{rng.choice(WORDS)}"
            return word
        if style < 0.65:
            body = word.replace("'", "''")
            if rng.random() < 0.25:
                pad = " " * rng.choice([0, indent, indent + 1])
                more = rng.choice(WORDS).replace("'", "''")
                body += "\n" + rng.choice(["", "\n", " \n"]) + pad + more
            return f"'{body}'"
        if style < 0.9:
            body = word.replace("\\", "\\\\").replace('"', '\\"')
            roll = rng.random()
            if roll < 0.3:
                body += rng.choice(ESCAPES)
            elif roll < 0.5:
                pad = " " * rng.choice([0, indent, indent + 1])
                body += rng.choice(["\n", "\n\n", " \n ", "  \n\n  ", "\r\n"]) + pad + "z"
            return f'"{body}"'
        if flow:
            items = [self.scalar(flow=True, indent=indent) for _ in range(rng.randrange(3))]
            return "[" + ", ".join(items) + "]"
        header = rng.choice(BLOCK_HEADERS)
        pad = " " * (indent + rng.choice([1, 2, 3]))
        lines = [
            rng.choice(
                [
                    "",
                    pad + rng.choice(WORDS),
                    pad + " " + rng.choice(WORDS),
                    pad + "#x",
                    " " * rng.randrange(0, indent + 4),
                ]
            )
            for _ in range(rng.randrange(0, 4))
        ]
        return header + "\n" + "\n".join(lines) + rng.choice(["", "\n", "\n\n"])

    def flow(self, depth: int) -> str:
        rng = self.rng
        multiline = rng.random() < 0.3
        separator = (
            rng.choice([", ", ",", " , ", ",\n", ",\n  ", "\n,"])
            if multiline
            else rng.choice([", ", ",", " ,"])
        )
        if rng.random() < 0.5:
            items: list[str] = []
            for _ in range(rng.randrange(4)):
                roll = rng.random()
                if depth < 3 and roll < 0.25:
                    items.append(self.flow(depth + 1))
                elif roll < 0.4:
                    key = self.scalar(flow=True, indent=0)
                    items.append(
                        key + rng.choice([": ", ":", " : "]) + self.scalar(flow=True, indent=0)
                    )
                elif roll < 0.48:
                    items.append(
                        "? " + self.scalar(flow=True, indent=0) + rng.choice(["", " : v", ": v"])
                    )
                else:
                    items.append(self.scalar(flow=True, indent=0))
            return "[" + separator.join(items) + rng.choice(["", "", ",", " ,", "\n"]) + "]"
        pairs: list[str] = []
        for _ in range(rng.randrange(4)):
            key = self.scalar(flow=True, indent=0)
            roll = rng.random()
            if roll < 0.1:
                pairs.append(key)
            elif roll < 0.15:
                pairs.append("? " + key)
            else:
                value = (
                    self.flow(depth + 1)
                    if depth < 3 and rng.random() < 0.2
                    else self.scalar(flow=True, indent=0)
                )
                pairs.append(key + rng.choice([": ", ": ", " : ", ":\n", ": \n  "]) + value)
        return "{" + separator.join(pairs) + rng.choice(["", "", ",", "\n"]) + "}"

    def block(self, indent: int, depth: int) -> str:
        rng = self.rng
        pad = " " * indent
        out: list[str] = []
        mapping = rng.random() < 0.55
        for _ in range(rng.randrange(1, 4)):
            if rng.random() < 0.08:
                out.append(
                    rng.choice(["", " " * rng.randrange(6), pad + "# c", "#c", pad + "  # c"])
                    + "\n"
                )
            if mapping:
                out.append(self.mapping_entry(pad, indent, depth))
            else:
                out.append(self.sequence_entry(pad, indent, depth))
        return "".join(out)

    def mapping_entry(self, pad: str, indent: int, depth: int) -> str:
        rng = self.rng
        key = rng.choice(
            ["a", "b", "k k", "'q'", '"d"', "é", "1", "y", "? k", "?", "a:b", "-k", "k#"]
        )
        separator = rng.choice([":", ":", " :", ":  "])
        if key.startswith("?"):
            line = f"{pad}{key}\n{pad}:"
            if rng.random() < 0.5:
                return line + " " + self.scalar(flow=False, indent=indent) + "\n"
            return line + "\n" + (self.block(indent + 2, depth + 1) if depth < 3 else "")
        if depth < 3 and rng.random() < 0.35:
            child = indent + rng.choice([0, 1, 2, 2, 4])
            return (
                pad
                + key
                + separator
                + rng.choice(["", " # c", " "])
                + "\n"
                + self.block(child, depth + 1)
            )
        value = self.flow(depth) if rng.random() < 0.25 else self.scalar(flow=False, indent=indent)
        gap = rng.choice([" ", " ", "  ", "\n" + pad + "  "])
        return pad + key + separator + gap + value + rng.choice(["", "", " # c", "#c", " "]) + "\n"

    def sequence_entry(self, pad: str, indent: int, depth: int) -> str:
        rng = self.rng
        dash = rng.choice(["- ", "- ", "-  ", "-\n" + pad + "  "])
        if depth < 3 and rng.random() < 0.3:
            inner = self.block(indent + 2, depth + 1)
            if rng.random() < 0.5:
                return pad + dash + inner.lstrip(" ")
            return pad + "-\n" + inner
        value = self.flow(depth) if rng.random() < 0.25 else self.scalar(flow=False, indent=indent)
        return pad + dash + value + rng.choice(["", " # c", " "]) + "\n"

    def document(self) -> str:
        rng = self.rng
        roll = rng.random()
        if roll < 0.2:
            body = self.flow(0)
        elif roll < 0.25:
            body = self.scalar(flow=False, indent=0)
        else:
            body = self.block(0, 0)
        text = rng.choice(PREFIXES) + body + rng.choice(SUFFIXES)
        if rng.random() < 0.1:
            text = text.replace("\n", rng.choice(["\r\n", "\r"]))
        if rng.random() < 0.1:
            text = text.rstrip("\n")
        return text

    def short(self) -> str:
        return "".join(self.rng.choice(ALPHABET) for _ in range(self.rng.randrange(1, 9)))

    def mutate(self, text: str) -> str:
        rng = self.rng
        for _ in range(rng.randrange(1, 4)):
            index = rng.randrange(len(text) + 1)
            roll = rng.random()
            fragment = rng.choice(ALPHABET) if roll < 0.7 else rng.choice(WORDS)
            if roll < 0.5:
                text = text[:index] + fragment + text[index:]
            elif roll < 0.75:
                text = text[:index] + text[index + 1 :]
            else:
                text = text[:index] + fragment + text[index + 1 :]
        return text

    def text(self) -> str:
        roll = self.rng.random()
        if roll < 0.35:
            return self.short()
        if roll < 0.75:
            return self.document()
        return self.mutate(self.document())


Stats = tuple[int, int, int]
"""Texts routed to pure by the guard, texts the C parser rejected, texts the C parser read."""


def search(job: tuple[int, int]) -> tuple[Stats, list[tuple[str, Outcome, Outcome]]]:
    seed, count = job
    generator = Generator(random.Random(seed))
    routed = rejected = accepted = 0
    divergences: list[tuple[str, Outcome, Outcome]] = []
    for _ in range(count):
        text = generator.text()
        if _needs_pure_parser(text):
            routed += 1
            continue
        c_reading = outcome(text, pure=False)
        if c_reading[0] != "value":
            rejected += 1
            continue
        accepted += 1
        pure_reading = outcome(text, pure=True)
        if not same(c_reading, pure_reading):
            divergences.append((text, c_reading, pure_reading))
    return (routed, rejected, accepted), divergences


def _results(
    jobs: list[tuple[int, int]], workers: int | None
) -> Iterator[tuple[Stats, list[tuple[str, Outcome, Outcome]]]]:
    """The search results of ``jobs``, from worker processes, or inline when ``workers`` is 1."""
    if workers == 1:
        yield from map(search, jobs)
        return
    with multiprocessing.Pool(workers) as pool:
        yield from pool.imap_unordered(search, jobs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("count", type=int, help="how many texts to generate")
    parser.add_argument(
        "--seed", type=int, default=0, help="first seed; each batch uses the next one"
    )
    parser.add_argument("--batch", type=int, default=5000, help="texts per worker batch")
    parser.add_argument(
        "--jobs", type=int, default=None, help="worker processes (default: CPU count)"
    )
    args = parser.parse_args(argv)

    if YAML(typ="safe").Parser is RuamelParser:
        print(
            "ruamel.yaml.clib is not installed, so there is no C parser to compare", file=sys.stderr
        )
        return 2

    # Whole batches, then one partial batch for the remainder, so every text is run.
    sizes = [args.batch] * (args.count // args.batch)
    if args.count % args.batch or not sizes:
        sizes.append(args.count % args.batch or args.count)
    jobs = [(args.seed + index, size) for index, size in enumerate(sizes)]
    totals = [0, 0, 0]
    found: dict[str, tuple[Outcome, Outcome]] = {}
    for stats, divergences in _results(jobs, args.jobs):
        totals = [total + stat for total, stat in zip(totals, stats, strict=True)]
        for text, c_reading, pure_reading in divergences:
            found.setdefault(text, (c_reading, pure_reading))

    routed, rejected, accepted = totals
    print(
        f"ruamel.yaml {ruamel.yaml.__version__}, ruamel.yaml.clib "
        f"{_distribution_version('ruamel.yaml.clib')} (libyaml {_installed_libyaml_version()}), "
        f"seeds {args.seed}-{args.seed + len(jobs) - 1}, C parser gate {'on' if _C_PARSER_AVAILABLE else 'off'}"
    )
    print(
        f"texts: {sum(totals)}  routed to pure: {routed}  rejected by C: {rejected}  read by C: {accepted}"
    )
    print(f"divergences: {len(found)}")
    for text, (c_reading, pure_reading) in sorted(found.items(), key=lambda item: len(item[0]))[
        :40
    ]:
        print(repr(text))
        print("   C   :", repr(c_reading)[:200])
        print("   pure:", repr(pure_reading)[:200])
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
