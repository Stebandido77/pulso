"""Print a deterministic content inventory of a wheel for diff-based comparison.

Output format: one line per file, alphabetical order, with format
    <size>  <sha256>  <filename>

Used by the wheel-identity gate (see
docs/internal/r-port/04_wheel_identity_verification.md).
"""

from __future__ import annotations

import hashlib
import sys
import zipfile


def main(path: str) -> int:
    with zipfile.ZipFile(path) as z:
        rows = []
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            with z.open(info) as f:
                sha = hashlib.sha256(f.read()).hexdigest()
            rows.append(f"{info.file_size:>10}  {sha}  {info.filename}")
    print("\n".join(rows))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: wheel_inventory.py <path-to-wheel>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
