#!/usr/bin/env python3
"""Validate deterministic integrity of Markdown research deliverables.

The validator never detects or launches desktop applications. Standard
Markdown is the default; Obsidian syntax is accepted only through an explicit
profile. Semantic truth and reasoning quality require a separate human/model
audit.
"""

from __future__ import annotations

import argparse
import csv
import json
import posixpath
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan_readability import scan_text


PLACEHOLDERS = (
    re.compile(r"\[TODO[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[TBD[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[\s*待填[^\]]*\]"),
    re.compile(r"\{\{[^}]+\}\}"),
)
WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
WINDOWS_INVALID = re.compile(r'[<>:"\\|?*\x00-\x1f]')


def mask_code(text: str) -> str:
    """Remove fenced and inline code while preserving line breaks and offsets."""
    output: List[str] = []
    in_fence = False
    fence_char = ""
    fence_size = 0
    for line in text.splitlines(keepends=True):
        match = re.match(r"^[ \t]{0,3}(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                fence_size = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_size:
                in_fence = False
            output.append("\n" if line.endswith("\n") else "")
            continue
        if in_fence:
            output.append("\n" if line.endswith("\n") else "")
            continue
        masked = re.sub(r"(`+)([^\n]*?)\1", lambda item: " " * len(item.group(0)), line)
        output.append(masked)
    return "".join(output)


def markdown_targets(text: str) -> List[str]:
    """Extract inline-link destinations, including balanced parentheses."""
    targets: List[str] = []
    cursor = 0
    while True:
        marker = text.find("](", cursor)
        if marker == -1:
            break
        opener = text.rfind("[", 0, marker)
        if opener == -1:
            cursor = marker + 2
            continue
        index = marker + 2
        depth = 1
        escaped = False
        while index < len(text):
            char = text[index]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    break
            index += 1
        if depth != 0:
            cursor = marker + 2
            continue
        inside = text[marker + 2 : index].strip()
        if inside.startswith("<") and ">" in inside:
            target = inside[1 : inside.find(">")]
        else:
            target_chars: List[str] = []
            nested = 0
            escaped = False
            for char in inside:
                if escaped:
                    target_chars.append(char)
                    escaped = False
                elif char == "\\":
                    target_chars.append(char)
                    escaped = True
                elif char == "(":
                    nested += 1
                    target_chars.append(char)
                elif char == ")" and nested:
                    nested -= 1
                    target_chars.append(char)
                elif char.isspace() and nested == 0:
                    break
                else:
                    target_chars.append(char)
            target = "".join(target_chars)
        if target:
            targets.append(target)
        cursor = index + 1
    for match in re.finditer(r"^[ \t]{0,3}\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))", text, flags=re.MULTILINE):
        target = match.group(1) or match.group(2)
        if target:
            targets.append(target)
    return targets


def wiki_targets(text: str) -> List[str]:
    return re.findall(r"\[\[([^\]]+)\]\]", text)


def is_external(raw: str) -> bool:
    stripped = raw.strip()
    if stripped.startswith(("#", "//")):
        return True
    scheme = urlsplit(stripped).scheme.casefold()
    return bool(scheme and scheme != "file")


def is_absolute_local(raw: str) -> bool:
    decoded = unquote(raw.strip().strip("<>"))
    return (
        urlsplit(decoded).scheme.casefold() == "file"
        or decoded.startswith(("/", "\\", "//"))
        or bool(re.match(r"^[A-Za-z]:[\\/]", decoded))
    )


def normalize_relative_target(raw: str) -> str:
    target = raw.strip().strip("<>")
    target = target.split("#", 1)[0].split("?", 1)[0]
    decoded = unquote(target)
    return posixpath.normpath(decoded) if decoded else ""


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def label_for(path: Path, root: Path) -> Path:
    return path.relative_to(root) if root.is_dir() else Path(path.name)


def discover_markdown(root: Path) -> List[Path]:
    if root.is_file():
        return [root] if root.suffix.casefold() == ".md" else []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.casefold() == ".md"
        and not any(part.startswith(".") for part in path.relative_to(root).parts)
    )


def portable_name_errors(relative: Path) -> List[str]:
    errors: List[str] = []
    for part in relative.parts:
        if part != unicodedata.normalize("NFC", part):
            errors.append(f"is not Unicode NFC-normalized: {part!r}")
        if WINDOWS_INVALID.search(part):
            errors.append(f"contains a Windows-invalid character: {part!r}")
        if part.endswith((" ", ".")):
            errors.append(f"ends with a space or dot: {part!r}")
        stem = part.split(".", 1)[0].casefold()
        if stem in WINDOWS_RESERVED:
            errors.append(f"uses a Windows-reserved name: {part!r}")
    return errors


def exact_case_exists(path: Path, boundary: Path) -> bool:
    """Check existence and spelling without trusting a case-insensitive host FS."""
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


def yaml_frontmatter(text: str) -> bool:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    end = next((index for index, line in enumerate(lines[1:], start=1) if line.strip() in {"---", "..."}), -1)
    if end == -1:
        return False
    return any(re.match(r"^[A-Za-z0-9_.-]+\s*:", line) for line in lines[1:end])


def markdown_headings(text: str) -> List[tuple[int, str]]:
    headings: List[tuple[int, str]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        atx = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if atx:
            headings.append((len(atx.group(1)), atx.group(2).strip()))
            continue
        if index + 1 < len(lines) and line.strip():
            setext = re.match(r"^[ \t]{0,3}(=+|-+)\s*$", lines[index + 1])
            if setext:
                headings.append((1 if setext.group(1).startswith("=") else 2, line.strip()))
    return headings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--allow-placeholders", action="store_true")
    parser.add_argument("--h1-policy", choices=("ignore", "warn", "error"), default="warn")
    parser.add_argument("--tier", choices=("light", "medium", "heavy", "super-heavy"), default=None)
    parser.add_argument("--profile", choices=("standard", "obsidian"), default="standard")
    parser.add_argument("--delivery-mode", choices=("auto", "single", "multi"), default="auto")
    parser.add_argument("--strict-warnings", action="store_true")
    args = parser.parse_args()

    root = args.path.expanduser().resolve()
    if not root.exists():
        print(f"ERROR: path does not exist: {root}")
        return 2

    errors: List[str] = []
    warnings: List[str] = []
    md_files = discover_markdown(root)
    if not md_files:
        errors.append("no Markdown files found")

    if args.delivery_mode == "single" and len(md_files) != 1:
        errors.append(f"delivery mode 'single' expects exactly one Markdown file, found {len(md_files)}")
    if args.delivery_mode == "multi" and (root.is_file() or len(md_files) < 2):
        errors.append("delivery mode 'multi' expects a directory with at least two Markdown files")

    visible_files = [root] if root.is_file() else [
        path for path in root.rglob("*") if path.is_file() and not any(part.startswith(".") for part in path.relative_to(root).parts)
    ]
    portability_labels: Dict[str, Path] = {}
    for candidate in visible_files:
        relative_candidate = label_for(candidate, root)
        for issue in portable_name_errors(relative_candidate):
            errors.append(f"non-portable path {relative_candidate}: {issue}")
        casefolded = unicodedata.normalize("NFC", relative_candidate.as_posix()).casefold()
        if casefolded in portability_labels and portability_labels[casefolded] != relative_candidate:
            errors.append(
                f"case-insensitive path collision: {portability_labels[casefolded]} and {relative_candidate}"
            )
        else:
            portability_labels[casefolded] = relative_candidate

    effective_multi = args.delivery_mode == "multi" or (args.delivery_mode == "auto" and root.is_dir() and len(md_files) > 1)
    master_docs: List[Path] = []
    if effective_multi:
        master_docs = [
            path
            for path in md_files
            if path.name.startswith("00-") or path.name.casefold() in {"readme.md", "index.md"}
        ]
        if not master_docs:
            message = "multi-document deliverable has no clear master map (00-*, README.md, or index.md)"
            if args.delivery_mode == "multi":
                errors.append(message)
            else:
                warnings.append(message)
        elif len(master_docs) > 1:
            warnings.append("multiple possible master maps found: " + ", ".join(path.name for path in master_docs))

    texts: Dict[Path, str] = {}
    try:
        for path in md_files:
            texts[path] = read_utf8(path)
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: could not read Markdown as UTF-8: {exc}")
        return 2

    stem_index: Dict[str, List[Path]] = {}
    for path in md_files:
        stem_index.setdefault(path.stem, [])
        if path not in stem_index[path.stem]:
            stem_index[path.stem].append(path)
        if root.is_dir():
            relative_no_suffix = path.relative_to(root).with_suffix("").as_posix()
            stem_index.setdefault(relative_no_suffix, [])
            if path not in stem_index[relative_no_suffix]:
                stem_index[relative_no_suffix].append(path)

    seen_h1: Dict[str, Path] = {}
    for path in md_files:
        relative = label_for(path, root)
        text = texts[path]
        check_text = mask_code(text)
        if not text.strip():
            errors.append(f"empty file: {relative}")
            continue

        if not args.allow_placeholders:
            for pattern in PLACEHOLDERS:
                if pattern.search(text):
                    errors.append(f"placeholder remains in {relative}: {pattern.pattern}")

        headings = markdown_headings(check_text)
        h1s = [title for level, title in headings if level == 1]
        h1_issue = ""
        if len(h1s) != 1:
            h1_issue = f"{relative} contains {len(h1s)} H1 titles; expected one under the selected policy"
        elif h1s[0] in seen_h1:
            h1_issue = f"duplicate H1 {h1s[0]!r} in {relative} and {label_for(seen_h1[h1s[0]], root)}"
        else:
            seen_h1[h1s[0]] = path
        if h1_issue and args.h1_policy == "error":
            errors.append(h1_issue)
        elif h1_issue and args.h1_policy == "warn":
            warnings.append(h1_issue)

        previous_level = 0
        for level, title in headings:
            if previous_level and level > previous_level + 1:
                errors.append(f"heading level jump in {relative}: H{previous_level} -> H{level} at {title!r}")
            previous_level = level

        for raw in markdown_targets(check_text):
            if is_external(raw):
                continue
            if is_absolute_local(raw):
                errors.append(f"absolute local path in Markdown link in {relative}: {raw}")
                continue
            if "\\" in raw and args.profile == "standard":
                errors.append(f"non-portable backslash in Markdown link in {relative}: {raw}")
                continue
            target = normalize_relative_target(raw)
            if target:
                boundary = root if root.is_dir() else root.parent
                unresolved_candidate = path.parent / Path(target)
                candidate = unresolved_candidate.resolve()
                try:
                    candidate.relative_to(boundary)
                except ValueError:
                    errors.append(f"Markdown link escapes the deliverable root in {relative}: {raw}")
                else:
                    if not exact_case_exists(unresolved_candidate, boundary):
                        errors.append(f"broken or case-mismatched Markdown link in {relative}: {raw}")

        wiki = wiki_targets(check_text)
        if wiki and args.profile == "standard":
            errors.append(f"{relative} uses {len(wiki)} wiki link(s) under the standard Markdown profile")
        elif args.profile == "obsidian":
            for raw in wiki:
                target = raw.split("|", 1)[0].split("#", 1)[0].strip()
                target = target.removesuffix(".md").replace("\\", "/").removeprefix("./")
                if target and target not in stem_index:
                    errors.append(f"broken wiki link in {relative}: [[{raw}]]")
                elif target and len(stem_index[target]) > 1:
                    warnings.append(f"ambiguous wiki link in {relative}: [[{raw}]]")

        if args.profile == "standard" and re.search(r"^\s*>\s*\[![^\]]+\]", check_text, flags=re.MULTILINE):
            errors.append(f"{relative} contains Obsidian-style Callout syntax under the standard profile")
        if args.profile == "standard" and yaml_frontmatter(text):
            errors.append(f"{relative} contains YAML/Properties frontmatter under the standard Markdown profile")

        scan = scan_text(text, path)
        for issue in scan.critical:
            errors.append(f"readability [{issue.code}] in {relative}:{issue.line}: {issue.message}")
        for issue in scan.warnings:
            warnings.append(f"readability [{issue.code}] in {relative}:{issue.line}: {issue.message}")

        if args.tier and not path.name.startswith("00-"):
            review_floor = {"light": 300, "medium": 700, "heavy": 1000, "super-heavy": 1400}[args.tier]
            if scan.prose_chars < review_floor:
                warnings.append(
                    f"thin-content review in {relative}: {scan.prose_chars} prose characters; verify semantic completeness instead of padding"
                )

    if effective_multi and master_docs:
        master = master_docs[0]
        linked_targets: Set[str] = {
            normalize_relative_target(raw)
            for raw in markdown_targets(mask_code(texts[master]))
            if not is_external(raw)
        }
        if args.profile == "obsidian":
            for raw in wiki_targets(mask_code(texts[master])):
                target = raw.split("|", 1)[0].split("#", 1)[0].strip().replace("\\", "/").removeprefix("./")
                if target:
                    linked_targets.add(target if target.casefold().endswith(".md") else target + ".md")
        for module in md_files:
            if module == master:
                continue
            relative_target = module.relative_to(master.parent).as_posix()
            if relative_target not in linked_targets and module.name not in linked_targets:
                errors.append(f"master document does not link module: {label_for(module, root)}")

    # Scan only files inside an explicit directory target; never scan siblings
    # when the validation target is a single Markdown file.
    if root.is_dir():
        for json_path in root.rglob("*.json"):
            try:
                json.loads(read_utf8(json_path))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"invalid JSON {json_path.relative_to(root)}: {exc}")
        for csv_path in root.rglob("*.csv"):
            try:
                with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                    rows = list(csv.reader(handle))
                if not rows or not rows[0]:
                    errors.append(f"CSV has no header: {csv_path.relative_to(root)}")
            except (OSError, UnicodeError, csv.Error) as exc:
                errors.append(f"invalid CSV {csv_path.relative_to(root)}: {exc}")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors or (args.strict_warnings and warnings):
        return 1

    print(f"OK: {root}")
    print(f"OK: {len(md_files)} Markdown file(s) passed deterministic integrity checks")
    print("NOTE: semantic truth, evidence entailment, and explanatory depth still require manual review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
