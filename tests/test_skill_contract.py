from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig")


class SkillContractTests(unittest.TestCase):
    def test_frontmatter_contains_only_name_and_description(self) -> None:
        skill = read("SKILL.md")
        block = re.match(r"\A---\n(.*?)\n---\n", skill, flags=re.DOTALL)
        self.assertIsNotNone(block)
        keys = re.findall(r"^([A-Za-z0-9_-]+):", block.group(1), flags=re.MULTILINE)
        self.assertEqual(keys, ["name", "description"])

    def test_explanatory_synthesis_is_a_required_gate(self) -> None:
        skill = read("SKILL.md")
        synthesis = read("references/explanatory-synthesis.md")
        self.assertIn("Gate 4：解释性综合", skill)
        self.assertIn("来源替换测试", synthesis)
        self.assertIn("证据桥梁", synthesis)
        self.assertIn("新案例迁移测试", synthesis)

    def test_dynamic_depth_and_independent_critique_are_required(self) -> None:
        skill = read("SKILL.md")
        critic = read("references/critical-review.md")
        self.assertIn("动态篇幅硬门", skill)
        self.assertIn("独立批判审查硬门", skill)
        self.assertIn("预注册攻击面", critic)
        self.assertIn("反填充测试", critic)

    def test_standard_markdown_is_default(self) -> None:
        skill = read("SKILL.md")
        artifact = read("references/artifact-output.md")
        self.assertIn("标准 Markdown 优先", skill)
        self.assertIn("标准配置（默认）", artifact)
        self.assertIn("Obsidian 增强（仅用户明确选择）", artifact)

    def test_no_product_or_os_specific_runtime_dependency(self) -> None:
        bodies = [read("SKILL.md"), read("references/research-contract.md"), read("references/artifact-output.md")]
        combined = "\n".join(bodies)
        for forbidden in ("AskQuestion", "/Applications/Obsidian.app", "--open-in-obsidian"):
            self.assertNotIn(forbidden, combined)

    def test_scripts_are_referenced(self) -> None:
        skill = read("SKILL.md")
        for script in (
            "scan_readability.py",
            "validate_deliverable.py",
            "validate_research.py",
            "validate_coverage.py",
            "validate_review.py",
            "validate_depth.py",
        ):
            self.assertIn(script, skill)

    def test_candidate_hash_uses_os_independent_sort_key(self) -> None:
        validator = read("scripts/validate_review.py")
        self.assertIn('normalized_name = unicodedata.normalize("NFC", relative.as_posix())', validator)
        self.assertIn('return sorted(resolved, key=lambda item: item[0])', validator)


if __name__ == "__main__":
    unittest.main()
