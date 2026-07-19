#!/usr/bin/env python3
"""Report deterministic readability and repetition risks in Markdown.

Only structural corruption and repeated substantive prose are hard failures.
Length, list density, and visual-anchor density are review signals, not proof
of quality. The script uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Issue:
    code: str
    line: int
    message: str


@dataclass
class ScanResult:
    path: Path
    prose_chars: int = 0
    paragraph_count: int = 0
    critical: List[Issue] = field(default_factory=list)
    warnings: List[Issue] = field(default_factory=list)
    anchor_counts: Dict[str, int] = field(
        default_factory=lambda: {
            "callout": 0,
            "table": 0,
            "diagram": 0,
            "image": 0,
            "bold": 0,
        }
    )


CALLOUT = re.compile(r"^\s*>\s*\[![^\]]+\][+-]?")
TABLE_RULE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|){1,}\s*$")
BULLET = re.compile(r"^\s*(?:[-*+] |\d+[.)] )")
HEADING = re.compile(r"^\s*#{1,6}\s+")
BOLD = re.compile(r"(?<!\*)\*\*[^*\n]+\*\*(?!\*)")


def visible_length(text: str) -> int:
    text = re.sub(r"\[[^\]]*\]\([^)]*\)", "链接", text)
    text = re.sub(r"[`*_>#|]", "", text)
    return len(re.sub(r"\s+", "", text))


def normalized_prose(text: str) -> str:
    text = re.sub(r"\[[^\]]*\]\([^)]*\)", "链接", text)
    text = re.sub(r"[`*_>#|]", "", text)
    text = re.sub(r"\s+", "", text)
    return text.casefold()


def scan_text(text: str, path: Path) -> ScanResult:
    result = ScanResult(path=path)
    lines = text.splitlines()
    in_fence = False
    paragraph: List[Tuple[int, str]] = []
    paragraphs: List[Tuple[int, str, str]] = []
    list_start = 0
    list_count = 0

    def flush_paragraph() -> None:
        nonlocal paragraph
        if not paragraph:
            return
        start = paragraph[0][0]
        joined = " ".join(value.strip() for _, value in paragraph)
        length = visible_length(joined)
        normalized = normalized_prose(joined)
        result.prose_chars += length
        result.paragraph_count += 1
        paragraphs.append((start, joined, normalized))
        if length > 600:
            result.warnings.append(
                Issue(
                    "paragraph-wall",
                    start,
                    f"paragraph has {length} visible characters; verify that it performs only one reasoning move",
                )
            )
        elif length > 360:
            result.warnings.append(
                Issue(
                    "dense-paragraph",
                    start,
                    f"paragraph has {length} visible characters; review its internal reasoning boundaries",
                )
            )
        paragraph = []

    def flush_list() -> None:
        nonlocal list_start, list_count
        if list_count >= 9:
            result.warnings.append(
                Issue(
                    "long-list",
                    list_start,
                    f"{list_count} consecutive list items; verify that prose, grouping, or a table would reveal relationships better",
                )
            )
        list_start = 0
        list_count = 0

    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            if not in_fence and stripped[3:].strip().lower() == "mermaid":
                result.anchor_counts["diagram"] += 1
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        result.anchor_counts["bold"] += len(BOLD.findall(line))
        result.anchor_counts["image"] += line.count("![")
        if CALLOUT.match(line):
            result.anchor_counts["callout"] += 1
        if TABLE_RULE.match(line):
            result.anchor_counts["table"] += 1

        if BULLET.match(line):
            flush_paragraph()
            if list_count == 0:
                list_start = number
            list_count += 1
            continue
        flush_list()

        structural = (
            not stripped
            or HEADING.match(line)
            or line.lstrip().startswith(">")
            or line.lstrip().startswith("|")
            or stripped == "---"
        )
        if structural:
            flush_paragraph()
        else:
            paragraph.append((number, line))

    flush_paragraph()
    flush_list()

    # Repeated substantive prose is a deterministic anti-padding failure.
    exact: Dict[str, List[int]] = {}
    substantive = [(line, raw, norm) for line, raw, norm in paragraphs if len(norm) >= 20]
    for line, _raw, norm in substantive:
        exact.setdefault(norm, []).append(line)
    for lines_found in exact.values():
        if len(lines_found) > 1:
            result.critical.append(
                Issue(
                    "duplicate-prose",
                    lines_found[1],
                    "substantive paragraph repeats at lines " + ", ".join(str(item) for item in lines_found),
                )
            )

    # Near duplicates are warnings. Cap comparisons to keep runtime predictable.
    near_candidates = [(line, raw, norm) for line, raw, norm in substantive if len(norm) >= 40][:250]
    warned_pairs = 0
    for index, (line_a, _raw_a, norm_a) in enumerate(near_candidates):
        for line_b, _raw_b, norm_b in near_candidates[index + 1 :]:
            if norm_a == norm_b:
                continue
            ratio = difflib.SequenceMatcher(None, norm_a, norm_b, autojunk=False).ratio()
            if ratio >= 0.92:
                result.warnings.append(
                    Issue(
                        "near-duplicate-prose",
                        line_b,
                        f"paragraph is {ratio:.0%} similar to the paragraph at line {line_a}; check for padded restatement",
                    )
                )
                warned_pairs += 1
                if warned_pairs >= 20:
                    break
        if warned_pairs >= 20:
            break

    block_anchors = sum(result.anchor_counts[name] for name in ("callout", "table", "diagram", "image"))
    if result.prose_chars >= 1600 and block_anchors == 0:
        result.warnings.append(
            Issue(
                "no-block-anchor",
                1,
                "long-form document has no block anchor; confirm that continuous prose is intentionally the clearest medium",
            )
        )
    if result.paragraph_count >= 4 and block_anchors >= result.paragraph_count:
        result.warnings.append(
            Issue(
                "anchor-over-dominant",
                1,
                f"{block_anchors} block anchors vs {result.paragraph_count} prose paragraphs; verify that anchors do not replace the argument",
            )
        )

    # Validate only definite frontmatter. A leading `---` without a closing
    # delimiter is also a valid CommonMark thematic break, so do not guess.
    if lines and lines[0].strip() == "---":
        yaml_end = next((index for index in range(1, len(lines)) if lines[index].strip() in {"---", "..."}), -1)
        if yaml_end != -1:
            content = [line for line in lines[1:yaml_end] if line.strip() and not line.lstrip().startswith("#")]
            if content and not any(re.match(r"^[A-Za-z0-9_.-]+\s*:", line) for line in content):
                result.warnings.append(Issue("thematic-break", 1, "leading --- is treated as a thematic break, not YAML"))

    # Blank lines are a house-style portability warning, not a CommonMark claim.
    scan_fence = False
    for index in range(len(lines) - 1):
        current = lines[index]
        following = lines[index + 1]
        if current.strip().startswith("```"):
            scan_fence = not scan_fence
            continue
        if scan_fence or not following.strip():
            continue
        if HEADING.match(current) and not HEADING.match(following):
            result.warnings.append(
                Issue("missing-blank-after-heading", index + 1, "add a blank line after the heading for consistent rendering and editing")
            )

    return result


def scan_path(root: Path) -> List[ScanResult]:
    files = [root] if root.is_file() else sorted(
        path for path in root.rglob("*") if path.is_file() and path.suffix.casefold() == ".md"
    )
    results: List[ScanResult] = []
    for path in files:
        text = path.read_text(encoding="utf-8-sig")
        results.append(scan_text(text, path))
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--strict-warnings", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    root = args.path.expanduser().resolve()
    if not root.exists():
        print(f"ERROR: path does not exist: {root}")
        return 2

    try:
        results = scan_path(root)
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: could not read Markdown as UTF-8: {exc}")
        return 2

    critical_count = sum(len(result.critical) for result in results)
    warning_count = sum(len(result.warnings) for result in results)

    if args.json_output:
        payload = []
        for result in results:
            item = asdict(result)
            item["path"] = str(result.path)
            payload.append(item)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for result in results:
            label = result.path.relative_to(root) if root.is_dir() else Path(result.path.name)
            print(f"SCAN: {label} (prose={result.prose_chars}, paragraphs={result.paragraph_count})")
            for issue in result.critical:
                print(f"CRITICAL [{issue.code}] {label}:{issue.line}: {issue.message}")
            for issue in result.warnings:
                print(f"WARNING [{issue.code}] {label}:{issue.line}: {issue.message}")
        print(f"SUMMARY: {len(results)} files, {critical_count} critical, {warning_count} warnings")

    return 1 if critical_count or (args.strict_warnings and warning_count) else 0


if __name__ == "__main__":
    raise SystemExit(main())
