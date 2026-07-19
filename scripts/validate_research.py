#!/usr/bin/env python3
"""Validate source and claim-evidence ledgers for research hard gates."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Set


SOURCE_FIELDS = {
    "source_id",
    "title",
    "url_or_locator",
    "exact_locator",
    "source_role",
    "underlying_evidence_id",
    "source_family_id",
    "qualified_unique_source",
    "direct_or_primary",
    "counter_or_alternative",
    "verification_status",
}
CLAIM_FIELDS = {
    "claim_id",
    "claim_text",
    "risk_level",
    "claim_type",
    "decisive",
    "applicable_scope",
    "supporting_source_ids",
    "counter_source_ids",
    "counterevidence_status",
    "reasoning_status",
    "evidence_status",
    "entailment_reviewed",
    "independent_family_count",
    "evidence_bridge",
    "key_assumptions",
    "alternative_explanations",
    "boundary_conditions",
    "flip_conditions",
    "current_judgment",
    "write_location",
    "reasoned_explanation_location",
    "single_source_reason",
}
TRUE_VALUES = {"true", "1", "yes", "y"}
FALSE_VALUES = {"false", "0", "no", "n", ""}
SOURCE_TARGETS = {
    "light": (5, 2, 1),
    "medium": (12, 5, 2),
    "heavy": (30, 12, 4),
    "super-heavy": (60, 24, 8),
}
PRECISION_TYPES = {"quote", "number", "version"}
ARGUMENT_TYPES = {"mechanism", "causal", "effect", "prediction", "recommendation"}
CLAIM_TYPES = {"fact", "mechanism", "causal", "effect", "value", "prediction", "recommendation", "quote", "number", "version", "textual-authority"}
REASONING_STATUSES = {"direct-evidence", "source-view", "synthesis", "recommendation", "unknown"}
SOURCE_ROLES = {"original", "synthesis", "practice", "discovery"}


def meaningful(value: str, minimum: int) -> bool:
    return len(re.sub(r"[^A-Za-z0-9\u3400-\u9fff]+", "", value)) >= minimum


def traceable_location(value: str) -> bool:
    raw_path, separator, heading = value.partition("#")
    relative = Path(raw_path)
    return bool(separator and heading.strip() and raw_path.strip() and not relative.is_absolute() and ".." not in relative.parts)


def split_ids(value: str) -> List[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def parse_bool(value: str, field: str, row_label: str, errors: List[str]) -> bool:
    normalized = value.strip().casefold()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    errors.append(f"{row_label}: {field} must be true or false, got {value!r}")
    return False


def read_rows(path: Path, required: Set[str]) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if None in (reader.fieldnames or []):
            raise ValueError("ledger contains an empty header")
        headers = set(reader.fieldnames or [])
        missing = sorted(required - headers)
        if missing:
            raise ValueError(f"missing required columns: {', '.join(missing)}")
        rows: List[Dict[str, str]] = []
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"row {row_number} contains more fields than the header")
            rows.append({str(key): (value or "").strip() for key, value in row.items()})
        return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--claims", required=True, type=Path)
    parser.add_argument("--tier", required=True, choices=tuple(SOURCE_TARGETS))
    parser.add_argument("--strict-source-targets", action="store_true")
    args = parser.parse_args()

    source_path = args.sources.expanduser().resolve()
    claim_path = args.claims.expanduser().resolve()
    if not source_path.is_file() or not claim_path.is_file():
        print("ERROR: --sources and --claims must point to existing CSV files")
        return 2

    try:
        sources = read_rows(source_path, SOURCE_FIELDS)
        claims = read_rows(claim_path, CLAIM_FIELDS)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(f"ERROR: could not parse ledger: {exc}")
        return 2

    errors: List[str] = []
    warnings: List[str] = []
    if not sources:
        errors.append("source ledger contains no source records")
    if not claims:
        errors.append("claim ledger contains no claim records")

    source_by_id: Dict[str, Dict[str, str]] = {}
    qualified_ids: Set[str] = set()
    qualified_evidence: Dict[str, List[str]] = {}
    direct_count = 0
    counter_count = 0

    for row_number, row in enumerate(sources, start=2):
        label = f"source row {row_number}"
        source_id = row["source_id"]
        if not source_id:
            errors.append(f"{label}: source_id is empty")
            continue
        if source_id in source_by_id:
            errors.append(f"{label}: duplicate source_id {source_id!r}")
            continue
        source_by_id[source_id] = row

        qualified = parse_bool(row["qualified_unique_source"], "qualified_unique_source", label, errors)
        direct = parse_bool(row["direct_or_primary"], "direct_or_primary", label, errors)
        counter = parse_bool(row["counter_or_alternative"], "counter_or_alternative", label, errors)
        if qualified:
            for field in ("title", "url_or_locator", "source_role", "underlying_evidence_id", "source_family_id"):
                if not row[field]:
                    errors.append(f"{label}: qualified source is missing {field}")
            if row["verification_status"].casefold() != "verified":
                errors.append(f"{label}: qualified source must have verification_status=verified")
            if row["source_role"].casefold() not in SOURCE_ROLES:
                errors.append(f"{label}: invalid source_role {row['source_role']!r}")
            evidence_id = row["underlying_evidence_id"]
            if evidence_id:
                qualified_evidence.setdefault(evidence_id, []).append(source_id)
            qualified_ids.add(source_id)
            direct_count += int(direct)
            counter_count += int(counter)

    referenced_ids: Set[str] = set()
    decisive_count = 0
    for row_number, row in enumerate(claims, start=2):
        label = f"claim row {row_number}"
        claim_id = row["claim_id"]
        if not claim_id:
            errors.append(f"{label}: claim_id is empty")
            continue
        if any(previous["claim_id"] == claim_id for previous in claims[: row_number - 2]):
            errors.append(f"{label}: duplicate claim_id {claim_id!r}")

        decisive = parse_bool(row["decisive"], "decisive", label, errors)
        entailment_reviewed = parse_bool(row["entailment_reviewed"], "entailment_reviewed", label, errors)
        support_ids = split_ids(row["supporting_source_ids"])
        counter_ids = split_ids(row["counter_source_ids"])
        referenced_ids.update(support_ids)
        referenced_ids.update(counter_ids)

        missing_ids = [source_id for source_id in support_ids + counter_ids if source_id not in source_by_id]
        for source_id in missing_ids:
            errors.append(f"{label}: references unknown source_id {source_id!r}")
        unqualified = [source_id for source_id in support_ids if source_id in source_by_id and source_id not in qualified_ids]
        for source_id in unqualified:
            errors.append(f"{label}: supporting source {source_id!r} is not a qualified source")

        if decisive:
            decisive_count += 1
            for field in (
                "claim_text",
                "applicable_scope",
                "evidence_bridge",
                "boundary_conditions",
                "current_judgment",
                "write_location",
                "reasoned_explanation_location",
            ):
                if not row[field]:
                    errors.append(f"{label}: decisive claim is missing {field}")
            for field, minimum in (
                ("claim_text", 8),
                ("applicable_scope", 4),
                ("evidence_bridge", 12),
                ("boundary_conditions", 4),
                ("current_judgment", 4),
            ):
                if row[field] and not meaningful(row[field], minimum):
                    errors.append(f"{label}: decisive claim field {field} is too shallow to audit")
            for field in ("write_location", "reasoned_explanation_location"):
                if row[field] and not traceable_location(row[field]):
                    errors.append(f"{label}: {field} must be a safe file.md#heading location")
            if not support_ids:
                errors.append(f"{label}: decisive claim has no supporting source")
            if not entailment_reviewed:
                errors.append(f"{label}: decisive claim must have entailment_reviewed=true")
            if row["evidence_status"].casefold() not in {"supported", "partial", "contested"}:
                errors.append(f"{label}: decisive claim has invalid evidence_status {row['evidence_status']!r}")

        risk = row["risk_level"].casefold()
        claim_type = row["claim_type"].casefold()
        if risk not in {"low", "medium", "high"}:
            errors.append(f"{label}: invalid risk_level {row['risk_level']!r}")
        if claim_type not in CLAIM_TYPES:
            errors.append(f"{label}: invalid claim_type {row['claim_type']!r}")
        if row["reasoning_status"].casefold() not in REASONING_STATUSES:
            errors.append(f"{label}: invalid reasoning_status {row['reasoning_status']!r}")
        families = {
            source_by_id[source_id]["source_family_id"]
            for source_id in support_ids
            if source_id in source_by_id and source_by_id[source_id]["source_family_id"]
        }
        evidence_groups = {
            source_by_id[source_id]["underlying_evidence_id"]
            for source_id in support_ids
            if source_id in source_by_id and source_by_id[source_id]["underlying_evidence_id"]
        }
        independent_count = min(len(families), len(evidence_groups))
        try:
            recorded_family_count = int(row["independent_family_count"])
        except ValueError:
            errors.append(f"{label}: independent_family_count must be an integer")
        else:
            if recorded_family_count != independent_count:
                errors.append(
                    f"{label}: independent_family_count={recorded_family_count} but supporting sources resolve to {independent_count} independent support group(s) after source-family and underlying-evidence checks"
                )
        if risk == "high" and decisive and independent_count < 2:
            single_authority = claim_type == "textual-authority" and bool(row["single_source_reason"])
            if not single_authority:
                errors.append(f"{label}: high-risk decisive claim has only {independent_count} independent support group(s)")

        if claim_type in PRECISION_TYPES:
            for source_id in support_ids:
                source = source_by_id.get(source_id)
                if source and not source["exact_locator"]:
                    errors.append(f"{label}: {claim_type} claim source {source_id!r} lacks exact_locator")

        if decisive and (risk == "high" or claim_type in ARGUMENT_TYPES):
            status = row["counterevidence_status"].casefold()
            if status not in {"found", "searched-none-found", "not-applicable", "not-searched"}:
                errors.append(f"{label}: invalid counterevidence_status {row['counterevidence_status']!r}")
            if not counter_ids and status not in {"searched-none-found", "not-applicable"}:
                errors.append(f"{label}: requires counterevidence or an explicit counterevidence_status")
            if status == "not-applicable" and not row["single_source_reason"]:
                warnings.append(f"{label}: counterevidence marked not-applicable without an explanatory reason")
            if not row["alternative_explanations"]:
                errors.append(f"{label}: high-risk/argument claim is missing alternative_explanations")
            elif not meaningful(row["alternative_explanations"], 4):
                errors.append(f"{label}: alternative_explanations is too shallow to audit")
            if not row["flip_conditions"]:
                errors.append(f"{label}: high-risk/argument claim is missing flip_conditions")
            elif not meaningful(row["flip_conditions"], 4):
                errors.append(f"{label}: flip_conditions is too shallow to audit")

        if row["reasoning_status"].casefold() == "synthesis":
            for field in ("evidence_bridge", "key_assumptions", "alternative_explanations", "boundary_conditions"):
                if not row[field]:
                    errors.append(f"{label}: synthesis claim is missing {field}")
                elif not meaningful(row[field], 4 if field != "evidence_bridge" else 12):
                    errors.append(f"{label}: synthesis field {field} is too shallow to audit")

    if decisive_count == 0:
        errors.append("claim ledger has no decisive claim; mark the claims that control the conclusion")

    target, direct_target, counter_target = SOURCE_TARGETS[args.tier]
    target_messages = []
    if len(qualified_ids) < target:
        target_messages.append(f"qualified sources {len(qualified_ids)}/{target}")
    if direct_count < direct_target:
        target_messages.append(f"direct/primary sources {direct_count}/{direct_target}")
    if counter_count < counter_target:
        target_messages.append(f"counter/alternative sources {counter_count}/{counter_target}")
    if target_messages:
        message = f"tier '{args.tier}' source target shortfall: " + ", ".join(target_messages)
        if args.strict_source_targets:
            errors.append(message)
        else:
            warnings.append(message + "; record the reason and affected conclusions in research state")

    unreferenced = sorted(qualified_ids - referenced_ids)
    if unreferenced:
        warnings.append("qualified sources not referenced by any claim: " + ", ".join(unreferenced))
    for evidence_id, source_ids in qualified_evidence.items():
        if len(source_ids) > 1:
            warnings.append(
                f"qualified sources {', '.join(source_ids)} share underlying evidence {evidence_id!r}; they may count as distinct documents but not as independent confirmation"
            )

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1

    print(f"OK: {len(qualified_ids)} qualified source(s), {len(claims)} claim(s), {decisive_count} decisive claim(s)")
    print("NOTE: ledger consistency passed; source existence and semantic entailment still require human/model review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
