#!/usr/bin/env python3
"""Validate deterministic structure and portability of this Codex skill."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Set


FORBIDDEN_PACKAGE_ITEMS = {"skill.manifest", "skill.sig", ".catpaw-install-meta.json"}
FORBIDDEN_TEXT = {
    "AskQuestion": "product-specific tool name",
    "/Applications/Obsidian.app": "OS-specific application path",
    "--open-in-obsidian": "GUI launch behavior in a quality validator",
    "deep-research-expert-v4": "stale version identity",
    "V4.1": "stale version identity",
    "skillhub.version": "marketplace metadata in runtime skill",
}
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".csv", ".py"}
REQUIRED_ROUTED_RESOURCES = {
    "assets/research-state.template.json",
    "assets/source-ledger.template.csv",
    "assets/claim-evidence-ledger.template.csv",
    "assets/document-coverage.template.csv",
    "assets/explanatory-synthesis.template.md",
    "assets/depth-contract.template.json",
    "assets/critical-review-record.template.json",
    "scripts/scan_readability.py",
    "scripts/validate_deliverable.py",
    "scripts/validate_research.py",
    "scripts/validate_coverage.py",
    "scripts/validate_review.py",
    "scripts/validate_depth.py",
}
WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


def parse_frontmatter(text: str) -> Dict[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, flags=re.DOTALL)
    if not match:
        raise ValueError("SKILL.md must begin with YAML frontmatter")
    values: Dict[str, str] = {}
    for raw in match.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        item = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if not item:
            raise ValueError(f"unsupported frontmatter line: {raw!r}")
        key, value = item.groups()
        values[key] = value.strip().strip('"\'')
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.skill_dir.expanduser().resolve()
    errors: List[str] = []
    warnings: List[str] = []
    if not root.is_dir():
        print(f"ERROR: skill directory does not exist: {root}")
        return 2

    skill_path = root / "SKILL.md"
    if not skill_path.is_file():
        print(f"ERROR: missing {skill_path}")
        return 1
    try:
        skill_text = skill_path.read_text(encoding="utf-8-sig")
        metadata = parse_frontmatter(skill_text)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    extra_keys = sorted(set(metadata) - {"name", "description"})
    if extra_keys:
        errors.append("frontmatter may contain only name and description; extra: " + ", ".join(extra_keys))
    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if name != root.name:
        errors.append(f"frontmatter name {name!r} does not match folder {root.name!r}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        errors.append("name must use lowercase hyphen-case")
    if not description:
        errors.append("frontmatter description is empty")

    for forbidden in FORBIDDEN_PACKAGE_ITEMS:
        if (root / forbidden).exists():
            errors.append(f"stale marketplace/package artifact must be removed: {forbidden}")
    caches = [path for path in root.rglob("*") if path.name == "__pycache__" or path.suffix == ".pyc"]
    for path in caches:
        errors.append(f"generated Python cache must not be packaged: {path.relative_to(root)}")

    referenced: Set[str] = set()
    documents = [skill_path, *sorted((root / "references").rglob("*.md"))]
    for document in documents:
        try:
            body = document.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {document.relative_to(root)} as UTF-8: {exc}")
            continue
        for token in re.findall(r"`([^`]+\.(?:md|json|csv|py|yaml|yml))`", body):
            if token.startswith(("references/", "assets/", "scripts/", "agents/")):
                candidate = root / token
                label = token
            elif "/" not in token and "\\" not in token and document.parent == root / "references":
                candidate = document.parent / token
                label = candidate.relative_to(root).as_posix()
            else:
                continue
            referenced.add(label)
            if not candidate.exists():
                errors.append(f"referenced resource does not exist: {label} (from {document.relative_to(root)})")
        if document != skill_path and len(body.splitlines()) > 100 and not re.search(r"^## (?:导航|目录)\s*$", body, flags=re.MULTILINE):
            errors.append(f"long reference needs a top navigation/contents section: {document.relative_to(root)}")

    unrouted = sorted(REQUIRED_ROUTED_RESOURCES - referenced)
    if unrouted:
        errors.append("required runtime resources are not routed from SKILL/references: " + ", ".join(unrouted))

    openai_path = root / "agents" / "openai.yaml"
    if not openai_path.is_file():
        errors.append("missing agents/openai.yaml")
    else:
        try:
            openai_text = openai_path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read agents/openai.yaml: {exc}")
            openai_text = ""
        if f"${name}" not in openai_text:
            errors.append("agents/openai.yaml default_prompt must mention the skill with $name")
        for field in ("display_name", "short_description", "default_prompt"):
            if not re.search(rf'^\s*{field}:\s*"[^\n]+"\s*$', openai_text, flags=re.MULTILINE):
                errors.append(f"agents/openai.yaml is missing quoted {field}")
        short = re.search(r'^\s*short_description:\s*"([^"]+)"', openai_text, flags=re.MULTILINE)
        if short and not 25 <= len(short.group(1)) <= 64:
            errors.append("agents/openai.yaml short_description must contain 25-64 characters")

    casefolded_paths: Dict[str, Path] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        folded = unicodedata.normalize("NFC", relative.as_posix()).casefold()
        if folded in casefolded_paths and casefolded_paths[folded] != relative:
            errors.append(f"case-insensitive path collision: {casefolded_paths[folded]} and {relative}")
        else:
            casefolded_paths[folded] = relative
        for part in relative.parts:
            if part != unicodedata.normalize("NFC", part):
                errors.append(f"path component is not Unicode NFC-normalized: {relative}")
                break
            stem = part.split(".", 1)[0].casefold()
            if re.search(r'[<>:"\\|?*\x00-\x1f]', part) or part.endswith((" ", ".")) or stem in WINDOWS_RESERVED:
                errors.append(f"Windows-unsafe path component: {relative}")
                break
        if not path.is_file():
            continue
        if path.suffix.casefold() not in TEXT_SUFFIXES:
            continue
        try:
            body = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {relative} as UTF-8: {exc}")
            continue
        placeholder_pattern_definitions = {
            Path("scripts/validate_deliverable.py"),
            Path("scripts/validate_package.py"),
        }
        if relative not in placeholder_pattern_definitions:
            if "TODO:" in body or "[TODO" in body or "[TBD" in body:
                errors.append(f"unresolved placeholder in {relative}")
        # The validator and regression tests intentionally name forbidden
        # patterns. Runtime instructions and resources must not contain them.
        if path.resolve() != Path(__file__).resolve() and "tests" not in relative.parts:
            for token, reason in FORBIDDEN_TEXT.items():
                if token in body:
                    errors.append(f"forbidden text {token!r} in {relative}: {reason}")
        if path.suffix == ".py":
            try:
                compile(body, str(path), "exec")
            except SyntaxError as exc:
                errors.append(f"Python syntax error in {relative}: {exc}")
        elif path.suffix == ".json":
            try:
                json.loads(body)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON in {relative}: {exc}")
        elif path.suffix == ".csv":
            try:
                with path.open(encoding="utf-8-sig", newline="") as handle:
                    rows = list(csv.reader(handle))
                if not rows or not rows[0]:
                    errors.append(f"CSV has no header: {relative}")
            except (OSError, UnicodeError, csv.Error) as exc:
                errors.append(f"invalid CSV in {relative}: {exc}")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1

    print(f"OK: {root}")
    print(f"OK: {len(referenced)} referenced resources exist")
    print("OK: frontmatter, UI metadata, portability, JSON/CSV, and Python syntax checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
