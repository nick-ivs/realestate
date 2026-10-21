"""Command line: check deal information and fill the form.

    python -m realestate offer.txt --profile agent.txt -o filled.pdf
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from . import info as info_mod
from .forms import disclosure_of_remuneration as form
from .pdf import fill


def ask_for_missing(deal: info_mod.DealInfo, today: date) -> info_mod.DealInfo:
    """Prompt for each missing value until the form has everything it needs."""
    result = form.build(deal, today)
    asked: set[str] = set()
    while pending := [m for m in result.missing if m.key not in asked]:
        m = pending[0]
        asked.add(m.key)
        answer = input(f"{m.label} ({m.hint}): ").strip()
        if answer:
            deal.values[m.key] = answer
        result = form.build(deal, today)
    return deal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="realestate", description=f"Fill the {form.NAME} form from deal information.")
    parser.add_argument("info", help="text file with the offer information, one \"Label - value\" per line")
    parser.add_argument("--profile", help="text file with your licensee details (name, brokerage, place, commission)")
    parser.add_argument("-o", "--output", default="filled.pdf", help="where to write the filled PDF (default: filled.pdf)")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today(), help="today's date, YYYY-MM-DD")
    parser.add_argument("--no-prompt", action="store_true", help="never ask for missing information; just list it")
    args = parser.parse_args(argv)

    deal = info_mod.parse_file(args.info)
    if args.profile:
        deal = deal.merged_over(info_mod.parse_file(args.profile))

    if not args.no_prompt and sys.stdin.isatty():
        deal = ask_for_missing(deal, args.date)
    result = form.build(deal, args.date)

    problems: list[str] = []
    if result.missing:
        print(f"Not written: {result.name} is missing information.")
        for m in result.missing:
            print(f"  - {m.label}: {m.hint}")
    else:
        pdf, problems = fill(result.template, result.fields, result.values)
        with open(args.output, "wb") as f:
            f.write(pdf)
        print(f"Wrote {args.output}  ({result.name})")
    for key, value in result.derived.items():
        print(f"\n{form.INPUT_BY_KEY[key].label} taken from the property address: {value}")
    for title, items in (("Check", result.warnings + problems), ("Unrecognized lines", deal.unrecognized)):
        if items:
            print(f"\n{title}:")
            for item in items:
                print(f"  - {item}")
    if result.not_on_form:
        print("\nNot used by this form (kept for the Contract of Purchase and Sale):")
        for label, value in result.not_on_form.items():
            print(f"  - {label}: {value}")
    return 1 if result.missing else 0


if __name__ == "__main__":
    sys.exit(main())
