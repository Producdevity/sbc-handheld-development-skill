#!/usr/bin/env python3

import json
from pathlib import Path
import sys
import time


if len(sys.argv) < 3:
    raise SystemExit(2)

operation = sys.argv[2]
if operation == "down":
    time.sleep(0.15)

record = {
    "arguments": sys.argv[2:],
    "monotonic_ns": time.monotonic_ns(),
}
with Path(sys.argv[1]).open("a", encoding="utf-8") as output:
    output.write(json.dumps(record) + "\n")
