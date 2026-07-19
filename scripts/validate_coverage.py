#!/usr/bin/env python3
"""Validate complete-reading coverage for source-document analysis."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Set, Tuple


REQUIRED_FIELDS = {
    "coverage_id",
    "source_id",
    "source_locator",
    "outline_item",
    "page_or_exact_locator",
    "range_start",
    "range_end",
    "coverage_status",
    "mapped_core_question_ids",
    "mapped_explanation_unit_ids",
    "decisive_claim_ids",
    "omission_reason",
    "notes",
}
STATUSES = {"covered", "intentionally-excluded", "unavailable"}


def split_ids(value: str) -> List[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if None in (reader.fieldnames or []):
            raise ValueError("coverage ledger contains an empty header")
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_FIELDS - headers)
        if missing:
            raise ValueError("missing required columns: " + ", ".join(missing))
        rows: List[Dict[str, str]] = []
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"row {row_number} contains more fields than the header")
            rows.append({str(key): (value or "").strip() for key, value in row.items()})
        return rows


def validate_coverage(
    path: Path,
    expected_items: int,
    core_question_ids: Set[str],
    central_unit_ids: Set[str],
    source_unit_totals: Dict[str, int],
) -> Tuple[List[str], List[Dict[str, str]]]:
    errors: List[str] = []
    try:
        rows = read_rows(path)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        return [f"could not parse coverage ledger: {exc}"], []
    if expected_items < 1:
        errors.append("expected_outline_items must be a positive integer")
    if len(rows) != expected_items:
        errors.append(f"coverage ledger has {len(rows)} outline item(s), expected {expected_items}")
    if not source_unit_totals or any(not source_id or not isinstance(total, int) or total < 1 for source_id, total in source_unit_totals.items()):
        errors.append("source unit totals must map every source_id to a positive page/equivalent-unit count")
    minimum_items = sum((total + 49) // 50 for total in source_unit_totals.values())
    if expected_items < minimum_items:
        errors.append(f"expected_outline_items={expected_items} is below the anti-collapse minimum {minimum_items} for the declared source lengths")
    seen: Set[str] = set()
    mapped_questions: Set[str] = set()
    mapped_units: Set[str] = set()
    accounted_units: Dict[str, Set[int]] = {source_id: set() for source_id in source_unit_totals}
    for row_number, row in enumerate(rows, start=2):
        label = f"coverage row {row_number}"
        coverage_id = row["coverage_id"]
        if not coverage_id:
            errors.append(f"{label}: coverage_id is empty")
        elif coverage_id in seen:
            errors.append(f"{label}: duplicate coverage_id {coverage_id!r}")
        seen.add(coverage_id)
        for field in ("source_id", "source_locator", "outline_item", "page_or_exact_locator"):
            if not row[field]:
                errors.append(f"{label}: {field} is empty")
        source_id = row["source_id"]
        if source_id not in source_unit_totals:
            errors.append(f"{label}: unknown source_id {source_id!r}; declare its total units in the contract/CLI")
        try:
            range_start = int(row["range_start"])
            range_end = int(row["range_end"])
        except ValueError:
            errors.append(f"{label}: range_start and range_end must be integers")
        else:
            total_units = source_unit_totals.get(source_id, 0)
            if range_start < 1 or range_end < range_start or range_end > total_units:
                errors.append(f"{label}: range {range_start}-{range_end} is outside source {source_id!r} bounds 1-{total_units}")
            elif range_end - range_start + 1 > 50:
                errors.append(f"{label}: one coverage row may span at most 50 pages/equivalent units; split the source outline")
            else:
                accounted_units.setdefault(source_id, set()).update(range(range_start, range_end + 1))
        status = row["coverage_status"].casefold()
        if status not in STATUSES:
            errors.append(f"{label}: invalid coverage_status {row['coverage_status']!r}")
        question_ids = set(split_ids(row["mapped_core_question_ids"]))
        unit_ids = set(split_ids(row["mapped_explanation_unit_ids"]))
        unknown_questions = sorted(question_ids - core_question_ids)
        unknown_units = sorted(unit_ids - central_unit_ids)
        if unknown_questions:
            errors.append(f"{label}: unknown core question id(s): {', '.join(unknown_questions)}")
        if unknown_units:
            errors.append(f"{label}: unknown central unit id(s): {', '.join(unknown_units)}")
        if status == "covered":
            if not question_ids and not unit_ids:
                errors.append(f"{label}: covered item is not mapped to a core question or central explanation unit")
            if not row["notes"]:
                errors.append(f"{label}: covered item needs notes stating what was extracted or checked")
            mapped_questions.update(question_ids)
            mapped_units.update(unit_ids)
        elif not row["omission_reason"]:
            errors.append(f"{label}: excluded or unavailable item requires omission_reason")
    missing_questions = sorted(core_question_ids - mapped_questions)
    missing_units = sorted(central_unit_ids - mapped_units)
    if missing_questions:
        errors.append("core questions without covered source-document items: " + ", ".join(missing_questions))
    if missing_units:
        errors.append("central explanation units without covered source-document items: " + ", ".join(missing_units))
    for source_id, total_units in source_unit_totals.items():
        missing_ranges = sorted(set(range(1, total_units + 1)) - accounted_units.get(source_id, set()))
        if missing_ranges:
            preview = ", ".join(str(item) for item in missing_ranges[:12])
            suffix = "..." if len(missing_ranges) > 12 else ""
            errors.append(f"source {source_id!r} has unaccounted page/equivalent units: {preview}{suffix}")
    return errors, rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--expected-items", required=True, type=int)
    parser.add_argument("--core-question-id", action="append", default=[])
    parser.add_argument("--central-unit-id", action="append", default=[])
    parser.add_argument("--source-units", action="append", default=[], metavar="SOURCE_ID=TOTAL")
    args = parser.parse_args()
    path = args.ledger.expanduser().resolve()
    if not path.is_file():
        print("ERROR: --ledger must point to an existing CSV file")
        return 2
    source_unit_totals: Dict[str, int] = {}
    parse_errors: List[str] = []
    for item in args.source_units:
        source_id, separator, raw_total = item.partition("=")
        try:
            total = int(raw_total)
        except ValueError:
            total = 0
        if not separator or not source_id.strip() or total < 1 or source_id.strip() in source_unit_totals:
            parse_errors.append(f"invalid --source-units value {item!r}; use unique SOURCE_ID=TOTAL with TOTAL > 0")
        else:
            source_unit_totals[source_id.strip()] = total
    errors, rows = validate_coverage(
        path, args.expected_items, set(args.core_question_id), set(args.central_unit_id), source_unit_totals
    )
    errors = parse_errors + errors
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print(f"OK: {len(rows)} source-document outline item(s) are accounted for")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
