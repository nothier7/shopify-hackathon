from __future__ import annotations

import argparse
import json
from pathlib import Path

from .payload import recommend_payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run RoomSwipe on the shared input JSON."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    rendered = json.dumps(recommend_payload(payload), indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
