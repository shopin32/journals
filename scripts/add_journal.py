#!/usr/bin/env python3
"""Add or update a journal record in data/journals.json."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "journals.json"
ISSN_RE = re.compile(r"^\d{4}-\d{3}[\dXx]$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add or update a journal record.")
    parser.add_argument("--interactive", action="store_true", help="Prompt for fields.")
    parser.add_argument("--title", help="Journal title.")
    parser.add_argument("--publisher", default="", help="Publisher name.")
    parser.add_argument("--issn", default="", help="Print ISSN, formatted as 1234-5678.")
    parser.add_argument("--eissn", default="", help="Electronic ISSN, formatted as 1234-5678.")
    parser.add_argument("--free", action="store_true", help="Mark publication price as free.")
    parser.add_argument("--price", type=float, help="Publication price amount.")
    parser.add_argument("--currency", default="", help="Publication price currency, for example USD or EUR.")
    parser.add_argument("--scopus", action="store_true", help="Mark as indexed in Scopus.")
    parser.add_argument("--web-of-science", action="store_true", help="Mark as indexed in Web of Science.")
    parser.add_argument("--quartile", default="", help="Quartile, for example Q1, Q2, Q3, Q4.")
    parser.add_argument(
        "--subject",
        action="append",
        default=[],
        help="Subject area. Repeat for multiple subjects.",
    )
    parser.add_argument("--url", default="", help="Journal URL.")
    parser.add_argument("--email", default="", help="Journal contact email.")
    parser.add_argument("--commit", action="store_true", help="Create a git commit after updating data.")
    parser.add_argument("--tag", help="Create a git tag after committing, for example v2026.04.26.")
    return parser.parse_args()


def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def prompt_bool(label: str, default: bool = False) -> bool:
    marker = "Y/n" if default else "y/N"
    value = input(f"{label} ({marker}): ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "true", "1"}


def load_journals() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{DATA_FILE} must contain a JSON array.")
    return data


def save_journals(journals: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    journals.sort(key=lambda item: item["title"].casefold())
    with DATA_FILE.open("w", encoding="utf-8") as handle:
        json.dump(journals, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def validate_issn(label: str, value: str) -> str:
    value = value.strip().upper()
    if value and not ISSN_RE.match(value):
        raise ValueError(f"{label} must look like 1234-5678.")
    return value


def normalize_quartile(value: str) -> str:
    value = value.strip().upper()
    if value and value not in {"Q1", "Q2", "Q3", "Q4"}:
        raise ValueError("--quartile must be Q1, Q2, Q3, or Q4.")
    return value


def validate_email(value: str) -> str:
    value = value.strip()
    if value and not EMAIL_RE.match(value):
        raise ValueError("--email must be a valid email address.")
    return value


def normalize_price(args: argparse.Namespace) -> dict:
    if args.free and args.price is not None:
        raise ValueError("Use either --free or --price, not both.")
    if args.free:
        return {"type": "free", "value": None, "currency": ""}
    if args.price is None:
        return {"type": "unknown", "value": None, "currency": ""}
    if args.price < 0:
        raise ValueError("--price cannot be negative.")
    currency = args.currency.strip().upper()
    if not currency:
        raise ValueError("--currency is required when --price is provided.")
    value = int(args.price) if args.price.is_integer() else args.price
    return {"type": "paid", "value": value, "currency": currency}


def build_record(args: argparse.Namespace) -> dict:
    if args.interactive:
        args.title = prompt("Title", args.title or "")
        args.publisher = prompt("Publisher", args.publisher)
        args.issn = prompt("ISSN", args.issn)
        args.eissn = prompt("eISSN", args.eissn)
        args.free = prompt_bool("Free publication", args.free)
        if not args.free:
            price = prompt("Publication price", "" if args.price is None else str(args.price))
            args.price = float(price) if price else None
            args.currency = prompt("Currency", args.currency)
        args.scopus = prompt_bool("Indexed in Scopus", args.scopus)
        args.web_of_science = prompt_bool("Indexed in Web of Science", args.web_of_science)
        args.quartile = prompt("Quartile", args.quartile)
        subjects = prompt("Subjects, comma-separated", ", ".join(args.subject))
        args.subject = [item.strip() for item in subjects.split(",") if item.strip()]
        args.url = prompt("URL", args.url)
        args.email = prompt("Email", args.email)

    if not args.title:
        raise ValueError("--title is required unless --interactive is used.")

    subjects = sorted({subject.strip() for subject in args.subject if subject.strip()}, key=str.casefold)

    return {
        "title": args.title.strip(),
        "publisher": args.publisher.strip(),
        "issn": validate_issn("ISSN", args.issn),
        "eissn": validate_issn("eISSN", args.eissn),
        "price": normalize_price(args),
        "indexes": {
            "scopus": bool(args.scopus),
            "web_of_science": bool(args.web_of_science),
        },
        "quartile": normalize_quartile(args.quartile),
        "subjects": subjects,
        "url": args.url.strip(),
        "email": validate_email(args.email),
        "updated_at": date.today().isoformat(),
    }


def upsert_journal(journals: list[dict], record: dict) -> str:
    key = record["title"].casefold()
    for index, journal in enumerate(journals):
        if journal.get("title", "").casefold() == key:
            journals[index] = record
            return "Updated"
    journals.append(record)
    return "Added"


def run_git(args: list[str]) -> None:
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def maybe_commit(record: dict, args: argparse.Namespace) -> None:
    if not args.commit and not args.tag:
        return
    if args.tag and not args.commit:
        raise ValueError("--tag requires --commit so the tag points at the journal update.")
    run_git(["add", str(DATA_FILE.relative_to(ROOT))])
    if args.commit:
        run_git(["commit", "-m", f"Add {record['title']}"])
    if args.tag:
        run_git(["tag", args.tag])


def main() -> int:
    args = parse_args()
    try:
        journals = load_journals()
        record = build_record(args)
        action = upsert_journal(journals, record)
        save_journals(journals)
        maybe_commit(record, args)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"{action}: {record['title']}")
    print(f"Saved: {DATA_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
