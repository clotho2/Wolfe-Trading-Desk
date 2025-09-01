from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Set


THRESH = 85.0


def _get_changed_files() -> Set[Path]:
    # PR context
    base = os.getenv("GITHUB_BASE_REF")
    head = os.getenv("GITHUB_SHA")
    if base:
        # GitHub actions fetch-depth may limit diff; fallback to HEAD~1
        os.system("git fetch --unshallow || true")
        cmd = f"git diff --name-only origin/{base}...{head}"
    else:
        cmd = "git diff --name-only HEAD~1"
    out = os.popen(cmd).read().strip().splitlines()
    return {Path(p) for p in out if p.endswith(".py")}


def _parse_cov(xml_path: Path) -> Dict[Path, float]:
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    out: Dict[Path, float] = {}
    for f in root.iterfind('.//class'):
        filename = f.get('filename')
        if not filename:
            continue
        lines = f.find('lines')
        hits = 0
        total = 0
        if lines is not None:
            for ln in lines:
                total += 1
                if int(ln.get('hits', '0')) > 0:
                    hits += 1
        pct = 100.0 * hits / total if total else 0.0
        out[Path(filename)] = pct
    return out


def main() -> int:
    changed = _get_changed_files()
    cov = _parse_cov(Path('coverage.xml'))
    failures = []
    for f in sorted(changed):
        pct = cov.get(f)
        if pct is None:
            failures.append((str(f), 0.0))
        elif pct < THRESH:
            failures.append((str(f), pct))
    if failures:
        print("Coverage gate failed (<85%) for:")
        for fn, pct in failures:
            print(f" - {fn}: {pct:.1f}%")
        return 2
    print("Coverage gate passed for changed files.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
