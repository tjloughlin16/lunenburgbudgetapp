#!/usr/bin/env python3
"""Verify the FY25 school surplus report -- a thin wrapper over
`verify_school_surplus.py --fy 2025`, kept so build_reports_index.py finds the verifier
for /analysis/fy25-school-surplus by its name.

    python3 scripts/verify_fy25_school_surplus.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_school_surplus  # noqa: E402

if __name__ == '__main__':
    sys.exit(verify_school_surplus.main(['--fy', '2025']))
