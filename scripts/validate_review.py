#!/usr/bin/env python3
"""Validate an independent review record against frozen candidate and evidence bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from validate_deliverable import is_absolute_local, is_external, markdown_targets, mask_code, normalize_relative_target


REQUIRED_GATES = {
    "evidence-logic": {
        "task-coverage",
        "evidence-entailment",
        "anti-restatement",
        "explanation",
        "counterargument",
        "coherence",
        "depth-and-filler",
        "uncertainty",
    },
    "blind-reader": {
        "reader-comprehension",
        "mechanism-reproduction",
        "novel-transfer",
        "continuity",
        "anti-jargon",
        "depth-and-filler",
    },
}
INPUT_SCOPE = {
    "evidence-logic": "contract-evidence-and-final-deliverable",
    "blind-reader": "final-deliverable-and-reader-profile-only",
}
ATX_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def read_json_object(path: Path, label: str) -> Dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


TEXT_SUFFIXES = {".md", ".txt", ".csv", ".yaml", ".yml"}


def canonical_payload(path: Path) -> bytes:
    if path.suffix.casefold() == ".json":
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return unicodedata.normalize(
            "NFC", json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        ).encode("utf-8")
    if path.suffix.casefold() in TEXT_SUFFIXES:
        text = path.read_text(encoding="utf-8-sig")
        return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n")).encode("utf-8")
    return path.read_bytes()


def resolve_file_list(base: Path, relative_files: object, label: str) -> List[Tuple[str, Path]]:
    if not isinstance(relative_files, list) or not relative_files or not all(isinstance(item, str) for item in relative_files):
        raise ValueError(f"{label} must be a non-empty list of relative file paths")
    boundary = base.resolve()
    resolved: List[Tuple[str, Path]] = []
    seen: set[str] = set()
    for raw in relative_files:
        normalized_raw = raw.strip().replace("\\", "/")
        relative = Path(normalized_raw)
        if not normalized_raw or relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"{label} contains an unsafe path: {raw!r}")
        normalized_name = unicodedata.normalize("NFC", relative.as_posix())
        folded = normalized_name.casefold()
        if folded in seen:
            raise ValueError(f"{label} contains a duplicate/case-colliding path: {raw!r}")
        seen.add(folded)
        unresolved = boundary / relative
        path = unresolved.resolve()
        try:
            path.relative_to(boundary)
        except ValueError as exc:
            raise ValueError(f"{label} path escapes its root: {raw!r}") from exc
        if not exact_case_exists(unresolved, boundary) or not path.is_file():
            raise ValueError(f"{label} file is missing or case-mismatched: {raw!r}")
        resolved.append((normalized_name, path))
    return sorted(resolved, key=lambda item: item[0])


def digest_file_list(files: List[Tuple[str, Path]]) -> str:
    digest = hashlib.sha256()
    for normalized_name, path in files:
        relative = normalized_name.encode("utf-8")
        payload = canonical_payload(path)
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def candidate_digest(root: Path, relative_files: object = None) -> str:
    """Hash the frozen user-facing candidate, including linked non-Markdown assets."""
    if not root.is_dir():
        raise ValueError("deliverable must be a directory")
    if relative_files is None:
        relative_files = [
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and not any(part.startswith(".") for part in path.relative_to(root).parts)
        ]
    files = resolve_file_list(root, relative_files, "candidate_files")
    listed = {name for name, _path in files}
    boundary = root.resolve()
    for name, path in files:
        if path.suffix.casefold() != ".md":
            continue
        text = mask_code(path.read_text(encoding="utf-8-sig"))
        for raw in markdown_targets(text):
            if is_external(raw) or is_absolute_local(raw):
                continue
            target = normalize_relative_target(raw)
            if not target:
                continue
            unresolved = path.parent / Path(target)
            resolved = unresolved.resolve()
            try:
                relative_target = unicodedata.normalize("NFC", resolved.relative_to(boundary).as_posix())
            except ValueError as exc:
                raise ValueError(f"candidate Markdown link escapes root in {name}: {raw}") from exc
            if not exact_case_exists(unresolved, boundary) or not resolved.is_file():
                raise ValueError(f"candidate Markdown link is broken or case-mismatched in {name}: {raw}")
            if relative_target not in listed:
                raise ValueError(f"candidate Markdown links an asset not listed in candidate_files: {relative_target}")
    return digest_file_list(files)


def evidence_bundle_digest(base: Path, relative_files: object) -> str:
    return digest_file_list(resolve_file_list(base, relative_files, "evidence_files"))


def contract_digest(path: Path) -> str:
    contract = read_json_object(path, "depth contract")
    canonical = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(unicodedata.normalize("NFC", canonical).encode("utf-8")).hexdigest()


def nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def meaningful_string(value: object, minimum: int) -> bool:
    if not isinstance(value, str):
        return False
    visible = re.sub(r"[^A-Za-z0-9\u3400-\u9fff]+", "", value)
    return len(visible) >= minimum


def parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp is empty")
    raw = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        parsed = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
    else:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def normalize_heading(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[`*_~]", "", value)).strip().casefold()


def exact_case_exists(path: Path, boundary: Path) -> bool:
    try:
        relative = path.relative_to(boundary)
    except ValueError:
        return False
    current = boundary
    for part in relative.parts:
        try:
            names = {child.name for child in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current = current / part
    return current.exists()


def markdown_location_exists(root: Path, location: object) -> bool:
    if not isinstance(location, str):
        return False
    raw_path, separator, raw_heading = location.strip().partition("#")
    relative = Path(raw_path)
    if not separator or not raw_heading.strip() or relative.is_absolute() or ".." in relative.parts or "\\" in raw_path:
        return False
    boundary = root.resolve()
    unresolved_path = boundary / relative
    path = unresolved_path.resolve()
    try:
        path.relative_to(boundary)
    except ValueError:
        return False
    if not exact_case_exists(unresolved_path, boundary) or not path.is_file() or path.suffix.casefold() != ".md":
        return False
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        return False
    wanted = normalize_heading(raw_heading)
    for index, line in enumerate(lines):
        atx = ATX_HEADING.match(line)
        if atx and normalize_heading(atx.group(2)) == wanted:
            return True
        if index + 1 < len(lines) and line.strip() and re.match(r"^[ \t]{0,3}(=+|-+)\s*$", lines[index + 1]):
            if normalize_heading(line) == wanted:
                return True
    return False


def validate_record(
    record_path: Path,
    deliverable: Path,
    contract_path: Path,
    expected_type: str,
) -> Tuple[List[str], Dict[str, object]]:
    errors: List[str] = []
    record: Dict[str, object] = {}
    try:
        record = read_json_object(record_path, "review record")
        contract = read_json_object(contract_path, "depth contract")
        digest = candidate_digest(deliverable, contract.get("candidate_files"))
        frozen_contract_digest = contract_digest(contract_path)
        evidence_digest = evidence_bundle_digest(contract_path.parent, contract.get("evidence_files"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"could not validate review record: {exc}"], record

    if expected_type not in REQUIRED_GATES:
        return [f"unknown review type: {expected_type}"], record
    if record.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if record.get("review_type") != expected_type:
        errors.append(f"review_type must be {expected_type!r}")
    for field in ("review_id", "reviewer_id", "reviewer_context_id", "reviewer_role", "reviewed_at"):
        if not nonempty_string(record.get(field)):
            errors.append(f"{field} must be a non-empty string")
    if record.get("reviewer_provenance") != "independent-agent-context":
        errors.append("reviewer_provenance must be 'independent-agent-context'")
    if record.get("author_involved") is not False:
        errors.append("author_involved must be false")
    if record.get("independent_context") is not True:
        errors.append("independent_context must be true")
    if record.get("input_scope") != INPUT_SCOPE[expected_type]:
        errors.append(f"input_scope must be {INPUT_SCOPE[expected_type]!r}")
    if str(record.get("status", "")).casefold() != "pass":
        errors.append("review status must be PASS")
    if record.get("candidate_sha256") != digest:
        errors.append("candidate_sha256 does not match the current candidate bundle; old PASS is invalid")
    if record.get("contract_sha256") != frozen_contract_digest:
        errors.append("contract_sha256 does not match the frozen depth contract; old PASS is invalid")
    if expected_type == "evidence-logic" and record.get("evidence_bundle_sha256") != evidence_digest:
        errors.append("evidence_bundle_sha256 does not match the frozen evidence files; old PASS is invalid")
    if expected_type == "blind-reader" and record.get("evidence_bundle_sha256") not in {"", None}:
        errors.append("blind-reader review must not receive or hash the evidence bundle")
    if record.get("contract_version") != contract.get("contract_version"):
        errors.append("review contract_version does not match the current depth contract")
    try:
        reviewed_at = parse_timestamp(record.get("reviewed_at"))
        frozen_at = parse_timestamp(contract.get("frozen_at"))
    except ValueError as exc:
        errors.append(f"invalid review/freeze timestamp: {exc}")
    else:
        now = datetime.now(timezone.utc)
        if reviewed_at < frozen_at:
            errors.append("reviewed_at predates the frozen contract")
        if reviewed_at > now + timedelta(minutes=5):
            errors.append("reviewed_at is in the future")

    attack_surface = record.get("preregistered_attack_surface")
    concrete_attacks = [item.strip() for item in attack_surface if meaningful_string(item, 12)] if isinstance(attack_surface, list) else []
    if len(set(concrete_attacks)) < 4:
        errors.append("preregistered_attack_surface must contain at least four concrete attack areas")

    gate_results = record.get("gate_results")
    passed_gates = set()
    if not isinstance(gate_results, list):
        errors.append("gate_results must be a list")
    else:
        for index, result in enumerate(gate_results, start=1):
            if not isinstance(result, dict):
                errors.append(f"gate result {index} must be an object")
                continue
            gate = str(result.get("gate", "")).strip()
            if str(result.get("status", "")).casefold() != "pass":
                errors.append(f"gate {gate or index!r} has not passed")
            if not markdown_location_exists(deliverable, result.get("evidence_location")):
                errors.append(f"gate {gate or index!r} lacks a valid Markdown heading evidence_location")
            if not meaningful_string(result.get("finding"), 20):
                errors.append(f"gate {gate or index!r} lacks a substantive finding")
            passed_gates.add(gate)
    missing_gates = sorted(REQUIRED_GATES[expected_type] - passed_gates)
    if missing_gates:
        errors.append("missing required gate results: " + ", ".join(missing_gates))

    issues = record.get("issues")
    if not isinstance(issues, list):
        errors.append("issues must be a list, including an empty list when no issue was found")
    else:
        for index, issue in enumerate(issues, start=1):
            if not isinstance(issue, dict):
                errors.append(f"issue {index} must be an object")
                continue
            severity = str(issue.get("severity", "")).upper()
            status = str(issue.get("status", "")).casefold()
            if severity not in {"P0", "P1", "P2"}:
                errors.append(f"issue {index} uses invalid severity {severity!r}")
            if severity in {"P0", "P1"} and status != "closed":
                errors.append(f"issue {index} is an open {severity}; review cannot PASS")
            if status == "closed" and not meaningful_string(issue.get("closure_evidence"), 20):
                errors.append(f"closed issue {index} lacks closure_evidence")

    counterargument = record.get("strongest_counterargument")
    if not isinstance(counterargument, dict) or not meaningful_string(counterargument.get("argument"), 30) or not meaningful_string(
        counterargument.get("disposition"), 30
    ) or not markdown_location_exists(deliverable, counterargument.get("evidence_location")):
        errors.append("strongest_counterargument must record argument, disposition, and evidence_location")
    filler = record.get("filler_audit")
    filler_numbers_valid = isinstance(filler, dict) and isinstance(filler.get("effective_npu"), (int, float)) and filler.get(
        "effective_npu", 0
    ) > 0 and all(
        isinstance(filler.get(field), (int, float)) and 0 <= filler[field] <= 1
        for field in ("exact_duplicate_ratio", "near_duplicate_ratio")
    )
    if not isinstance(filler, dict) or str(filler.get("status", "")).casefold() != "pass" or not meaningful_string(
        filler.get("evidence") if isinstance(filler, dict) else None, 40
    ) or not filler_numbers_valid:
        errors.append("filler_audit must PASS with concrete evidence")

    if expected_type == "blind-reader":
        transfer = record.get("novel_transfer_test")
        if not isinstance(transfer, dict) or str(transfer.get("status", "")).casefold() != "pass" or not all(
            meaningful_string(transfer.get(field), 30) for field in ("novel_case", "model_reproduced", "application_result")
        ):
            errors.append("blind-reader review requires a passing novel_transfer_test with a novel case, reproduced model, and result")

    return errors, record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--deliverable", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--review-type", required=True, choices=tuple(REQUIRED_GATES))
    args = parser.parse_args()

    record_path = args.record.expanduser().resolve()
    deliverable = args.deliverable.expanduser().resolve()
    contract_path = args.contract.expanduser().resolve()
    if not record_path.is_file() or not contract_path.is_file() or not deliverable.is_dir():
        print("ERROR: --record and --contract must be files; --deliverable must be a directory")
        return 2
    errors, _record = validate_record(record_path, deliverable, contract_path, args.review_type)
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print(f"OK: {args.review_type} review is bound to the current frozen candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
