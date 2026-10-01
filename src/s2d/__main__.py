"""Command line: python -m s2d {schema,validate,render}."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .card import DecisionCard, json_schema
from .render import to_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="s2d", description="Signal2Decision Decision Card tools")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("schema", help="print the Decision Card JSON Schema")

    p_val = sub.add_parser("validate", help="check one or more card files against the honesty rules")
    p_val.add_argument("files", nargs="+", type=Path)

    p_ren = sub.add_parser("render", help="render a card as Markdown")
    p_ren.add_argument("file", type=Path)
    p_ren.add_argument("--lang", default="en", choices=["en"])

    args = parser.parse_args(argv)

    if args.command == "schema":
        print(json.dumps(json_schema(), indent=2, ensure_ascii=False))
        return 0

    if args.command == "validate":
        failed = 0
        for f in args.files:
            try:
                DecisionCard.model_validate_json(f.read_text(encoding="utf-8"))
                print(f"OK    {f}")
            except ValidationError as e:
                failed += 1
                print(f"FAIL  {f}")
                for err in e.errors():
                    where = ".".join(str(p) for p in err["loc"]) or "card"
                    print(f"      {where}: {err['msg']}")
        return 1 if failed else 0

    if args.command == "render":
        card = DecisionCard.model_validate_json(args.file.read_text(encoding="utf-8"))
        sys.stdout.write(to_markdown(card, lang=args.lang))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
