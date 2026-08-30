"""Print the repairs, the errors, and the conformance guarantees for one variant."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent


def main() -> int:
    variant = sys.argv[1]
    rows = json.loads((HERE / f"results-{variant}.json").read_text())

    print("=== repairs applied ===")
    for row in rows:
        for change in row["repairs"]:
            print(f"  {row['artifact']:10} {change['code']:24} path={change['path']}")

    print("\n=== errors reported (not repaired) ===")
    for row in rows:
        for err in row["errors"]:
            print(
                f"  {row['artifact']:10} {err['code']:22} "
                f"prop={err['property']!s:18} {err['message']}"
            )

    print("\n=== conformance guarantees ===")
    print("  repair --check never wrote:", all(r["repair_check_left_file_unwritten"] for r in rows))
    print("  repair idempotent:", all(r["idempotent"] for r in rows))
    noop = [r for r in rows if r["byte_identical_when_noop"] is not None]
    print(
        f"  byte-identical when nothing needed: "
        f"{all(r['byte_identical_when_noop'] for r in noop)} ({len(noop)} artifacts)"
    )

    print("\n=== verdicts ===")
    for verdict, count in Counter(r["verdict"] for r in rows).most_common():
        print(f"  {verdict:20} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
