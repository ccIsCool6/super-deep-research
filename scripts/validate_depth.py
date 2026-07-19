#!/usr/bin/env python3
"""Validate a project-specific explanatory-capacity contract.

NPU v1: one CJK character = 1 NPU, one Latin word = 2 NPU, and one
numeric token = 0.5 NPU. Repeated substantive blocks are discounted.
Tables, lists, and callouts can contribute at reduced weight, capped so they
cannot replace continuous explanatory prose.
"""

from __future__ import annotations

import argparse
import difflib
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_coverage import validate_coverage
from validate_review import exact_case_exists, parse_timestamp, validate_record


HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
TABLE_RULE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
LIST_ITEM = re.compile(r"^\s*(?:[-*+] |\d+[.)] )")
CALLOUT = re.compile(r"^\s*>\s*(?:\[![^\]]+\][+-]?\s*)?")
TIER_FACTOR = {"light": 0.85, "medium": 1.0, "heavy": 1.15, "super-heavy": 1.30}
TIER_TOTAL_MINIMUM_NPU = {"light": 800, "medium": 3000, "heavy": 7000, "super-heavy": 15000}
FACET_WEIGHTS = {
    "definitions": 80,
    "distinctions": 80,
    "mechanism_links": 110,
    "evidence_clusters": 130,
    "alternatives": 160,
    "boundaries": 110,
    "cases": 150,
    "implications": 110,
    "transfers": 130,
    "worked_examples": 180,
    "failure_traces": 180,
    "reproducible_checks": 160,
    "exercises": 110,
}
SCORE_WEIGHTS = {"complexity": 0.12, "dispute": 0.10, "audience_gap": 0.10, "risk": 0.12}
SEMANTIC_FIELDS = {
    "conclusion_clear",
    "evidence_interpreted",
    "reasoning_bridge_visible",
    "mechanism_explained_or_unknown_stated",
    "alternatives_handled",
    "boundaries_stated",
    "example_or_counterexample_used",
    "implication_explained",
    "transfer_test_passed",
    "transition_coherent",
}
TASK_TYPES = {"research", "document-analysis", "learning-report", "technical-learning"}
CENTRAL_REQUIRED_FACETS = {
    "mechanism_links",
    "evidence_clusters",
    "alternatives",
    "boundaries",
    "cases",
    "implications",
    "transfers",
}
TECHNICAL_REQUIRED_FACETS = {"worked_examples", "failure_traces", "reproducible_checks", "exercises"}


@dataclass
class Block:
    kind: str
    raw_npu: float
    normalized: str
    location: str


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def round_up_50(value: float) -> int:
    return int(math.ceil(value / 50.0) * 50)


def npu(text: str) -> float:
    clean = re.sub(r"https?://\S+", "", text)
    cjk = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", clean))
    latin = len(re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", clean))
    numbers = len(re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)?(?![A-Za-z])", clean))
    return cjk + 2.0 * latin + 0.5 * numbers


def normalize(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^\w\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+", "", text, flags=re.UNICODE)
    return text.casefold()


def normalize_heading(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[`*_~]", "", value)).strip().casefold()


def extract_location(root: Path, location: str) -> str:
    raw_path, separator, raw_heading = location.partition("#")
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"location must stay inside deliverable root: {location}")
    boundary = root.resolve()
    unresolved_path = boundary / relative
    path = unresolved_path.resolve()
    try:
        path.relative_to(boundary)
    except ValueError as exc:
        raise ValueError(f"location escapes deliverable root: {location}") from exc
    if not exact_case_exists(unresolved_path, boundary) or not path.is_file():
        raise ValueError(f"location file does not exist: {location}")
    text = read_utf8(path)
    if not separator:
        return text

    wanted = normalize_heading(raw_heading)
    lines = text.splitlines()
    start = -1
    level = 0
    end = len(lines)
    for index, line in enumerate(lines):
        match = HEADING.match(line)
        if not match:
            continue
        current_level = len(match.group(1))
        if start == -1 and normalize_heading(match.group(2)) == wanted:
            start = index + 1
            level = current_level
        elif start != -1 and current_level <= level:
            end = index
            break
    if start == -1:
        raise ValueError(f"heading not found for location: {location}")
    return "\n".join(lines[start:end])


def blocks_from_markdown(text: str, location: str) -> List[Block]:
    blocks: List[Block] = []
    in_fence = False
    paragraph: List[str] = []

    def flush() -> None:
        nonlocal paragraph
        if not paragraph:
            return
        raw = " ".join(item.strip() for item in paragraph)
        blocks.append(Block("prose", npu(raw), normalize(raw), location))
        paragraph = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence or HEADING.match(line) or TABLE_RULE.match(line):
            flush()
            continue
        if not stripped:
            flush()
            continue
        if line.lstrip().startswith("|"):
            flush()
            raw = line.replace("|", " ")
            blocks.append(Block("table", npu(raw), normalize(raw), location))
        elif LIST_ITEM.match(line):
            flush()
            raw = LIST_ITEM.sub("", line)
            blocks.append(Block("list", npu(raw), normalize(raw), location))
        elif line.lstrip().startswith(">"):
            flush()
            raw = CALLOUT.sub("", line)
            blocks.append(Block("callout", npu(raw), normalize(raw), location))
        else:
            paragraph.append(line)
    flush()
    return [block for block in blocks if block.raw_npu > 0]


def calculated_floor(unit: Dict[str, object], tier: str) -> int:
    scores = unit.get("scores")
    facets = unit.get("facets")
    if not isinstance(scores, dict) or not isinstance(facets, dict):
        raise ValueError("scores and facets must be objects")
    base = 120.0
    for field, weight in FACET_WEIGHTS.items():
        value = facets.get(field)
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"facet {field} must be a non-negative integer")
        base += weight * value
    importance = unit.get("importance")
    if importance not in {"central", "supporting"}:
        raise ValueError("importance must be central or supporting")
    if importance == "central":
        missing = sorted(field for field in CENTRAL_REQUIRED_FACETS if facets.get(field, 0) < 1)
        if missing:
            raise ValueError("central unit must include every core explanatory facet: " + ", ".join(missing))
        if facets.get("definitions", 0) + facets.get("distinctions", 0) < 1:
            raise ValueError("central unit must define the key concept or make a decisive distinction")
    multiplier = 1.0
    for field, weight in SCORE_WEIGHTS.items():
        value = scores.get(field)
        if not isinstance(value, int) or value not in {0, 1, 2}:
            raise ValueError(f"score {field} must be 0, 1, or 2")
        multiplier += weight * (value - 1)
    if importance == "central" and sum(int(scores[field]) for field in SCORE_WEIGHTS) < 3:
        raise ValueError("central unit score profile is implausibly low; justify and recalibrate complexity, dispute, audience gap, and risk")
    multiplier = min(1.60, max(0.80, multiplier))
    return round_up_50(base * multiplier * TIER_FACTOR[tier])


def effective_counts(block_groups: Sequence[Tuple[str, List[Block]]]) -> Tuple[Dict[str, float], float, float, float]:
    seen: List[Tuple[str, float]] = []
    per_location: Dict[str, float] = {}
    raw_total = 0.0
    exact_loss = 0.0
    near_loss = 0.0
    for location, blocks in block_groups:
        prose = 0.0
        auxiliary = 0.0
        for block in blocks:
            raw_total += block.raw_npu
            factor = 1.0
            if block.raw_npu >= 20 and block.normalized:
                exact = next((item for item, _value in seen if item == block.normalized), None)
                if exact is not None:
                    factor = 0.0
                    exact_loss += block.raw_npu
                else:
                    near = block.raw_npu >= 40 and any(
                        value >= 40
                        and difflib.SequenceMatcher(None, block.normalized, item, autojunk=False).ratio() >= 0.90
                        for item, value in seen[-300:]
                    )
                    if near:
                        factor = 0.20
                        near_loss += block.raw_npu * 0.80
                    seen.append((block.normalized, block.raw_npu))
            if block.kind == "prose":
                prose += block.raw_npu * factor
            else:
                weight = {"list": 0.40, "table": 0.30, "callout": 0.50}[block.kind]
                auxiliary += block.raw_npu * factor * weight
        per_location[location] = prose + min(auxiliary, prose * 0.15)
    return per_location, raw_total, exact_loss, near_loss


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--deliverable", required=True, type=Path)
    parser.add_argument("--tier", required=True, choices=tuple(TIER_FACTOR))
    args = parser.parse_args()

    contract_path = args.contract.expanduser().resolve()
    root = args.deliverable.expanduser().resolve()
    if not contract_path.is_file() or not root.is_dir():
        print("ERROR: --contract must be a JSON file and --deliverable must be a directory")
        return 2
    try:
        contract = json.loads(read_utf8(contract_path))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not parse depth contract: {exc}")
        return 2
    if not isinstance(contract, dict):
        print("ERROR: depth contract must contain a JSON object")
        return 2

    errors: List[str] = []
    warnings: List[str] = []
    if contract.get("counting_mode") != "npu-v1":
        errors.append("counting_mode must be npu-v1")
    task_type = contract.get("task_type")
    if task_type not in TASK_TYPES:
        errors.append("task_type must be research, document-analysis, learning-report, or technical-learning")
        task_type = "research"
    if not str(contract.get("reader_profile", "")).strip():
        errors.append("reader_profile is required so explanation depth can be calibrated")
    if not str(contract.get("calibration_rationale", "")).strip():
        errors.append("calibration_rationale is required; do not hide a low floor behind unexplained scores")
    try:
        alignment_time = parse_timestamp(contract.get("alignment_confirmed_at"))
        frozen_time = parse_timestamp(contract.get("frozen_at"))
    except ValueError as exc:
        errors.append(f"alignment_confirmed_at and frozen_at must be ISO timestamps: {exc}")
    else:
        if frozen_time < alignment_time:
            errors.append("frozen_at cannot predate alignment_confirmed_at")
        if alignment_time > datetime.now(timezone.utc) + timedelta(minutes=5) or frozen_time > datetime.now(timezone.utc) + timedelta(minutes=5):
            errors.append("alignment_confirmed_at and frozen_at cannot be in the future")
    tier = contract.get("tier")
    if tier not in TIER_FACTOR:
        errors.append("tier must be light, medium, heavy, or super-heavy")
        tier = "medium"
    elif tier != args.tier:
        errors.append(f"contract tier {tier!r} does not match requested tier {args.tier!r}")
    if args.tier in {"medium", "heavy", "super-heavy"} and contract.get("independent_critic_required") is not True:
        errors.append("medium and above require independent_critic_required=true")
    version = contract.get("contract_version")
    if not isinstance(version, int) or version < 1:
        errors.append("contract_version must be a positive integer")
    previous_floor = contract.get("previous_total_floor_npu", 0)
    declared_total = contract.get("total_floor_npu")
    if isinstance(previous_floor, int) and isinstance(declared_total, int) and previous_floor > 0:
        if declared_total < previous_floor * 0.90:
            if not contract.get("revision_reason") or contract.get("reconfirmed_after_reduction") is not True:
                errors.append("total floor was reduced by more than 10% without revision_reason and renewed user confirmation")

    units = contract.get("units")
    if not isinstance(units, list) or not units:
        errors.append("contract must contain at least one explanatory unit")
        units = []

    core_questions_raw = contract.get("core_questions")
    core_question_ids: set[str] = set()
    if not isinstance(core_questions_raw, list) or not core_questions_raw:
        errors.append("core_questions must contain the confirmed research questions")
    else:
        for index, item in enumerate(core_questions_raw, start=1):
            if not isinstance(item, dict):
                errors.append(f"core question {index} must be an object")
                continue
            question_id = str(item.get("question_id", "")).strip()
            question = str(item.get("question", "")).strip()
            if not question_id or not question:
                errors.append(f"core question {index} has an empty question_id or question")
            elif question_id in core_question_ids:
                errors.append(f"duplicate core question id {question_id!r}")
            else:
                core_question_ids.add(question_id)

    unit_ids: set[str] = set()
    locations: set[str] = set()
    calculated_floors: Dict[str, int] = {}
    block_groups: List[Tuple[str, List[Block]]] = []
    unit_by_location: Dict[str, Dict[str, object]] = {}
    central_unit_ids: set[str] = set()
    mapped_core_question_ids: set[str] = set()
    for index, unit in enumerate(units, start=1):
        label = f"unit {index}"
        if not isinstance(unit, dict):
            errors.append(f"{label} must be an object")
            continue
        unit_id = str(unit.get("unit_id", "")).strip()
        question = str(unit.get("question", "")).strip()
        reader_outcome = str(unit.get("reader_outcome", "")).strip()
        delivery = unit.get("delivery")
        capacity = unit.get("capacity")
        audit = unit.get("semantic_audit")
        if not unit_id or not question or not reader_outcome:
            errors.append(f"{label} has an empty unit_id, question, or reader_outcome")
            continue
        if unit_id in unit_ids:
            errors.append(f"{label} duplicate unit_id {unit_id!r}")
        unit_ids.add(unit_id)
        importance = unit.get("importance")
        mapped_ids_raw = unit.get("core_question_ids")
        if not isinstance(mapped_ids_raw, list) or not all(isinstance(item, str) for item in mapped_ids_raw):
            errors.append(f"{label} core_question_ids must be a list of strings")
            mapped_ids: set[str] = set()
        else:
            mapped_ids = {item.strip() for item in mapped_ids_raw if item.strip()}
        if importance == "central":
            central_unit_ids.add(unit_id)
            if not mapped_ids:
                errors.append(f"{label} is central but maps no core_question_ids")
            unknown = sorted(str(item) for item in mapped_ids - core_question_ids)
            if unknown:
                errors.append(f"{label} maps unknown core question id(s): {', '.join(unknown)}")
            mapped_core_question_ids.update(str(item) for item in mapped_ids if item in core_question_ids)
            if task_type == "technical-learning":
                facets = unit.get("facets")
                missing_technical = sorted(
                    field for field in TECHNICAL_REQUIRED_FACETS if not isinstance(facets, dict) or facets.get(field, 0) < 1
                )
                if missing_technical:
                    errors.append(f"{label} technical-learning gate is missing: {', '.join(missing_technical)}")
        elif mapped_ids:
            unknown = sorted(str(item) for item in mapped_ids - core_question_ids)
            if unknown:
                errors.append(f"{label} maps unknown core question id(s): {', '.join(unknown)}")
        if not isinstance(delivery, dict) or not str(delivery.get("location", "")).strip():
            errors.append(f"{label} has no delivery.location")
            continue
        location = str(delivery["location"]).strip()
        if location in locations:
            errors.append(f"{label} reuses location {location!r}; each explanation unit needs a traceable section")
        locations.add(location)
        try:
            floor = calculated_floor(unit, tier)
        except ValueError as exc:
            errors.append(f"{label}: {exc}")
            continue
        calculated_floors[unit_id] = floor
        declared_floor = capacity.get("floor_npu") if isinstance(capacity, dict) else None
        if declared_floor != floor:
            errors.append(f"{label} floor_npu must equal calculated NPU floor {floor}, got {declared_floor!r}")
        if isinstance(capacity, dict):
            previous_unit_floor = capacity.get("previous_floor_npu", 0)
            if isinstance(previous_unit_floor, int) and previous_unit_floor > 0 and isinstance(declared_floor, int):
                if declared_floor < previous_unit_floor * 0.90:
                    if not capacity.get("revision_reason") or capacity.get("reconfirmed_after_reduction") is not True:
                        errors.append(f"{label} floor was reduced by more than 10% without a reason and renewed confirmation")
        if contract.get("independent_critic_required"):
            if not isinstance(audit, dict):
                errors.append(f"{label} semantic_audit is missing")
            else:
                failed = sorted(field for field in SEMANTIC_FIELDS if audit.get(field) is not True)
                if failed:
                    errors.append(f"{label} has not passed semantic audit fields: {', '.join(failed)}")
        try:
            text = extract_location(root, location)
            block_groups.append((location, blocks_from_markdown(text, location)))
            unit_by_location[location] = unit
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{label}: {exc}")

    if not central_unit_ids:
        errors.append("contract must contain at least one central explanation unit")
    missing_core_mappings = sorted(core_question_ids - mapped_core_question_ids)
    if missing_core_mappings:
        errors.append("core questions without a central explanation unit: " + ", ".join(missing_core_mappings))

    if task_type == "document-analysis":
        coverage = contract.get("source_coverage")
        if not isinstance(coverage, dict):
            errors.append("document-analysis requires source_coverage")
        else:
            raw_ledger = str(coverage.get("ledger_path", "")).strip()
            expected_items = coverage.get("expected_outline_items")
            raw_sources = coverage.get("sources")
            source_unit_totals: Dict[str, int] = {}
            if not isinstance(raw_sources, list) or not raw_sources:
                errors.append("source_coverage.sources must declare each source and its total pages/equivalent units")
            else:
                for source_index, source in enumerate(raw_sources, start=1):
                    if not isinstance(source, dict):
                        errors.append(f"source_coverage source {source_index} must be an object")
                        continue
                    source_id = str(source.get("source_id", "")).strip()
                    total_units = source.get("total_pages_or_equivalent_units")
                    if not source_id or not isinstance(total_units, int) or total_units < 1:
                        errors.append(f"source_coverage source {source_index} needs source_id and positive total units")
                    elif source_id in source_unit_totals:
                        errors.append(f"source_coverage has duplicate source_id {source_id!r}")
                    else:
                        source_unit_totals[source_id] = total_units
            relative_ledger = Path(raw_ledger)
            if not raw_ledger or relative_ledger.is_absolute() or ".." in relative_ledger.parts:
                errors.append("source_coverage.ledger_path must be a safe path relative to the depth contract")
            elif not isinstance(expected_items, int):
                errors.append("source_coverage.expected_outline_items must be an integer")
            elif coverage.get("outline_frozen_before_synthesis") is not True:
                errors.append("source document outline must be frozen before synthesis")
            else:
                coverage_boundary = contract_path.parent.resolve()
                unresolved_coverage_path = coverage_boundary / relative_ledger
                coverage_path = unresolved_coverage_path.resolve()
                if not exact_case_exists(unresolved_coverage_path, coverage_boundary):
                    errors.append("source_coverage.ledger_path is missing or has a case mismatch")
                coverage_errors, _rows = validate_coverage(
                    coverage_path,
                    expected_items,
                    core_question_ids,
                    central_unit_ids,
                    source_unit_totals,
                )
                errors.extend(f"source coverage: {error}" for error in coverage_errors)

    calculated_unit_total = sum(calculated_floors.values())
    expected_integration_floor = max(500, round_up_50(0.10 * calculated_unit_total))
    integration = contract.get("integration")
    integration_location = ""
    if not isinstance(integration, dict):
        errors.append("integration must be an object")
    else:
        integration_location = str(integration.get("location", "")).strip()
        if not integration_location:
            errors.append("integration.location is required")
        if integration.get("floor_npu") != expected_integration_floor:
            errors.append(
                f"integration.floor_npu must equal calculated floor {expected_integration_floor}, got {integration.get('floor_npu')!r}"
            )
        if integration_location in locations:
            errors.append("integration.location must be a distinct synthesis section, not a reused unit section")
        elif integration_location:
            try:
                text = extract_location(root, integration_location)
                block_groups.append((integration_location, blocks_from_markdown(text, integration_location)))
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append(f"integration: {exc}")

    semantic_floor = calculated_unit_total + expected_integration_floor
    expected_total_floor = max(semantic_floor, TIER_TOTAL_MINIMUM_NPU[args.tier])
    if declared_total != expected_total_floor:
        errors.append(
            f"total_floor_npu must equal max(semantic floor {semantic_floor}, tier safety floor "
            f"{TIER_TOTAL_MINIMUM_NPU[args.tier]}) = {expected_total_floor}, got {declared_total!r}"
        )
    expected_band = contract.get("expected_band_npu")
    if not (
        isinstance(expected_band, list)
        and len(expected_band) == 2
        and all(isinstance(item, int) for item in expected_band)
        and expected_band[0] >= expected_total_floor
        and expected_band[1] >= expected_band[0]
    ):
        errors.append("expected_band_npu must be [lower, upper] with lower >= total floor")

    if args.tier in {"medium", "heavy", "super-heavy"}:
        review_records = contract.get("review_records")
        review_ids: set[str] = set()
        reviewer_ids: set[str] = set()
        reviewer_context_ids: set[str] = set()
        if not isinstance(review_records, dict):
            errors.append("medium and above require evidence-logic and blind-reader review records")
        else:
            for review_type in ("evidence-logic", "blind-reader"):
                raw_record = str(review_records.get(review_type, "")).strip()
                relative_record = Path(raw_record)
                if not raw_record or relative_record.is_absolute() or ".." in relative_record.parts:
                    errors.append(f"review_records.{review_type} must be a safe path relative to the depth contract")
                    continue
                record_boundary = contract_path.parent.resolve()
                unresolved_record_path = record_boundary / relative_record
                record_path = unresolved_record_path.resolve()
                if not exact_case_exists(unresolved_record_path, record_boundary):
                    errors.append(f"review_records.{review_type} is missing or has a case mismatch")
                record_errors, record = validate_record(
                    record_path, root, contract_path, review_type
                )
                errors.extend(f"{review_type} review: {error}" for error in record_errors)
                review_id = str(record.get("review_id", "")).strip()
                reviewer_id = str(record.get("reviewer_id", "")).strip()
                reviewer_context_id = str(record.get("reviewer_context_id", "")).strip()
                if review_id:
                    if review_id in review_ids:
                        errors.append("evidence-logic and blind-reader reviews must have distinct review_id values")
                    review_ids.add(review_id)
                if reviewer_id:
                    if reviewer_id in reviewer_ids:
                        errors.append("blind-reader review must use a different reviewer/context from evidence-logic review")
                    reviewer_ids.add(reviewer_id)
                if reviewer_context_id:
                    if reviewer_context_id in reviewer_context_ids:
                        errors.append("blind-reader review must use a different reviewer_context_id from evidence-logic review")
                    reviewer_context_ids.add(reviewer_context_id)

    counts, raw_total, exact_loss, near_loss = effective_counts(block_groups)
    for location, unit in unit_by_location.items():
        unit_id = str(unit["unit_id"])
        actual = counts.get(location, 0.0)
        floor = calculated_floors.get(unit_id, 0)
        print(f"UNIT: {unit_id} effective={actual:.0f}/{floor} NPU at {location}")
        if actual < floor:
            errors.append(f"unit {unit_id!r} below dynamic floor: {actual:.0f}/{floor} NPU")
    integration_actual = counts.get(integration_location, 0.0)
    print(f"INTEGRATION: effective={integration_actual:.0f}/{expected_integration_floor} NPU at {integration_location}")
    if integration_location and integration_actual < expected_integration_floor:
        errors.append(f"integration section below floor: {integration_actual:.0f}/{expected_integration_floor} NPU")

    effective_total = sum(counts.values())
    if effective_total < expected_total_floor:
        errors.append(f"deliverable below dynamic total floor: {effective_total:.0f}/{expected_total_floor} NPU")
    elif isinstance(expected_band, list) and len(expected_band) == 2:
        if effective_total < expected_band[0]:
            warnings.append(f"effective content meets the hard floor but is below planned band: {effective_total:.0f}/{expected_band[0]} NPU")
        elif effective_total > expected_band[1]:
            warnings.append(f"effective content exceeds planned band: {effective_total:.0f}/{expected_band[1]} NPU; review for redundancy")

    exact_ratio = exact_loss / raw_total if raw_total else 0.0
    near_ratio = near_loss / raw_total if raw_total else 0.0
    max_exact = contract.get("max_exact_duplicate_ratio")
    max_near = contract.get("max_near_duplicate_ratio")
    if not isinstance(max_exact, (int, float)) or not 0 <= max_exact <= 1:
        errors.append("max_exact_duplicate_ratio must be between 0 and 1")
    elif exact_ratio > max_exact:
        errors.append(f"exact duplicate ratio {exact_ratio:.1%} exceeds {max_exact:.1%}")
    if not isinstance(max_near, (int, float)) or not 0 <= max_near <= 1:
        errors.append("max_near_duplicate_ratio must be between 0 and 1")
    elif near_ratio > max_near:
        errors.append(f"near duplicate discount ratio {near_ratio:.1%} exceeds {max_near:.1%}")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1

    print(
        f"OK: dynamic depth contract passed (effective={effective_total:.0f}, raw={raw_total:.0f}, "
        f"exact_loss={exact_loss:.0f}, near_loss={near_loss:.0f} NPU)"
    )
    print("NOTE: NPU is a hard capacity floor, not proof of truth or explanatory quality")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
