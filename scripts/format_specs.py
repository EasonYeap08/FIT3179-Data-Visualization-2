"""Pretty-print every spec in specs/: nested blocks short enough stay on one line."""
import json
import sys
from pathlib import Path

WIDTH = 100


def fmt(v, depth=0, col=0):
    """col = characters already on the line before this value."""
    one = json.dumps(v, ensure_ascii=False)
    if not isinstance(v, (dict, list)) or col + len(one) <= WIDTH:
        return one
    pad, end = "  " * (depth + 1), "  " * depth
    if isinstance(v, dict):
        items = []
        for k, x in v.items():
            key = f"{pad}{json.dumps(k, ensure_ascii=False)}: "
            items.append(key + fmt(x, depth + 1, len(key)))
        return "{\n" + ",\n".join(items) + "\n" + end + "}"
    return "[\n" + ",\n".join(pad + fmt(x, depth + 1, len(pad)) for x in v) + "\n" + end + "]"


for p in sorted(Path(sys.argv[1] if len(sys.argv) > 1 else "specs").glob("*.json")):
    p.write_text(fmt(json.loads(p.read_text())) + "\n")
