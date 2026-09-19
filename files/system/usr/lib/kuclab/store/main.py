#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/usr/lib/kuclab")

import app  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(app.main())
