"""
Runs the whole backend suite: `python -m tests.run_all`.

Each module is a script that configures env at import time and binds an engine,
so they cannot share a process — this launches one subprocess per module,
streams its output, and exits non-zero if any failed. Modules are discovered
from tests/test_*.py so a new file is picked up without editing a list.
"""

import subprocess
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent


def main() -> int:
    modules = sorted(p.stem for p in TESTS.glob("test_*.py"))
    if not modules:
        print("no test modules found", file=sys.stderr)
        return 1

    failed: list[str] = []
    for name in modules:
        print(f"\n───── {name}", flush=True)
        result = subprocess.run([sys.executable, "-m", f"tests.{name}"], cwd=TESTS.parent)
        if result.returncode != 0:
            failed.append(name)

    print()
    if failed:
        print(f"FAILED ({len(failed)}/{len(modules)}): {' '.join(failed)}")
        return 1
    print(f"all {len(modules)} suites passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
