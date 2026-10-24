#!/usr/bin/env python3

import json
from pathlib import Path
import sys


if len(sys.argv) < 3:
    raise SystemExit(2)

with Path(sys.argv[1]).open("a", encoding="utf-8") as output:
    output.write(json.dumps(sys.argv[2:]) + "\n")
