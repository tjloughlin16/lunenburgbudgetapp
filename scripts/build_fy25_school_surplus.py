#!/usr/bin/env python3
"""The FY25 school surplus -- a thin wrapper over `build_school_surplus.py --fy 2025`.

    python3 scripts/build_fy25_school_surplus.py            # write the .md, payload, chart
    python3 scripts/build_fy25_school_surplus.py --check     # fail if any is stale

Kept because `fy28/public/data/fy25-school-surplus.json` names this script as its
generator, and that payload is held byte-identical. The work is in build_school_surplus.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_school_surplus  # noqa: E402

if __name__ == '__main__':
    sys.exit(build_school_surplus.main(['--fy', '2025'] + sys.argv[1:]))
