#!/usr/bin/env python3
"""Generate a Cadence .io file from a spreadsheet CSV IO plan."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "hammer"))
from hammer.technology.sky130.io_plan import main

if __name__ == "__main__":
    main()
