from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from scan_readability import scan_path, scan_text


def validate(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPTS / "validate_deliverable.py"), str(path), *args],
        check=False,
        capture_output=True,
        text=True,
    )


class DeliverableValidationTests(unittest.TestCase):
    def test_exact_repeated_substantive_paragraph_is_hard_failure(self) -> None:
        repeated = "这一段在没有增加任何机制、证据、边界或含义的情况下被原样重复，用来制造虚假的篇幅与深度。" * 5
        result = scan_text(f"# 标题\n\n{repeated}\n\n{repeated}\n", Path("report.md"))
        self.assertTrue(any(issue.code == "duplicate-prose" for issue in result.critical))

    def test_short_repeated_paragraphs_cannot_evade_padding_detection(self) -> None:
        repeated = "这段话反复出现只是在凑篇幅，并没有增加机制证据边界或迁移理解。"
        result = scan_text("# 标题\n\n" + "\n\n".join([repeated] * 20), Path("report.md"))
        self.assertTrue(any(issue.code == "duplicate-prose" for issue in result.critical))

    def test_long_prose_without_visual_anchor_is_not_hard_failure(self) -> None:
        paragraphs = "\n\n".join(f"第{i}段解释一个不同的因果关系与适用边界。" * 20 for i in range(8))
        result = scan_text(f"# 标题\n\n{paragraphs}\n", Path("report.md"))
        self.assertFalse(any(issue.code == "anchor-too-sparse" for issue in result.critical))

    def test_medium_single_document_can_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "研究报告.md"
            report.write_text("# 研究报告\n\n这是一份结构完整但篇幅较短的候选稿。\n", encoding="utf-8")
            completed = validate(report, "--tier", "medium", "--delivery-mode", "single", "--h1-policy", "error")
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("thin-content review", completed.stdout)

    def test_standard_profile_rejects_wiki_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "00-地图.md").write_text("# 地图\n\n[[模块]]\n", encoding="utf-8")
            (root / "模块.md").write_text("# 模块\n\n正文。\n", encoding="utf-8")
            completed = validate(root, "--profile", "standard")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("wiki link", completed.stdout)

    def test_obsidian_profile_accepts_resolvable_wiki_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "00-地图.md").write_text("# 地图\n\n[[模块]]\n\n[模块](./模块.md)\n", encoding="utf-8")
            (root / "模块.md").write_text("# 模块\n\n正文。\n", encoding="utf-8")
            completed = validate(root, "--profile", "obsidian")
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_obsidian_profile_accepts_path_qualified_wiki_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sub").mkdir()
            (root / "00-地图.md").write_text("# 地图\n\n[[sub/模块]]\n", encoding="utf-8")
            (root / "sub" / "模块.md").write_text("# 模块\n\n正文。\n", encoding="utf-8")
            completed = validate(root, "--profile", "obsidian")
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_standard_profile_rejects_obsidian_only_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "报告.md"
            report.write_text("---\ntags: [研究]\n---\n# 报告\n\n> [!note] 提示\n", encoding="utf-8")
            completed = validate(report, "--profile", "standard")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("YAML/Properties", completed.stdout)
        self.assertIn("Callout", completed.stdout)

    def test_commonmark_thematic_break_is_not_misread_as_unclosed_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "报告.md"
            report.write_text("---\n\n# 报告\n\n正文。\n", encoding="utf-8")
            completed = validate(report, "--profile", "standard")
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_links_inside_code_are_not_treated_as_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "报告.md"
            report.write_text(
                "# 报告\n\n`[示例](missing.md)`\n\n```markdown\n[示例](missing.md)\n[[missing]]\n```\n",
                encoding="utf-8",
            )
            completed = validate(report, "--profile", "standard")
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_headings_inside_code_do_not_count_as_document_h1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "报告.md"
            report.write_text("# 报告\n\n```bash\n# install\n```\n", encoding="utf-8")
            completed = validate(report, "--h1-policy", "error")
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_setext_h1_is_accepted_by_h1_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "报告.md"
            report.write_text("报告\n====\n\n正文。\n", encoding="utf-8")
            completed = validate(report, "--h1-policy", "error")
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_readability_directory_scan_includes_uppercase_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "REPORT.MD").write_text("# Report\n\nText.\n", encoding="utf-8")
            results = scan_path(root)
        self.assertEqual(len(results), 1)

    def test_missing_image_is_a_broken_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "报告.md"
            report.write_text("# 报告\n\n![图](./assets/missing.png)\n", encoding="utf-8")
            completed = validate(report)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("broken", completed.stdout)

    def test_missing_reference_style_image_is_a_broken_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "报告.md"
            report.write_text("# 报告\n\n![图][figure]\n\n[figure]: ./assets/missing.png\n", encoding="utf-8")
            completed = validate(report)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("broken", completed.stdout)

    def test_link_cannot_escape_deliverable_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "delivery"
            root.mkdir()
            (base / "outside.md").write_text("# 外部\n", encoding="utf-8")
            (root / "报告.md").write_text("# 报告\n\n[外部](../outside.md)\n", encoding="utf-8")
            completed = validate(root)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("escapes", completed.stdout)

    def test_absolute_local_link_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "报告.md"
            report.write_text("# 报告\n\n[本机文件](/etc/hosts)\n", encoding="utf-8")
            completed = validate(report)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("absolute local path", completed.stdout)

    def test_windows_reserved_filename_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "CON.md"
            report.write_text("# 报告\n\n正文。\n", encoding="utf-8")
            completed = validate(report)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Windows-reserved", completed.stdout)

    def test_windows_reserved_non_markdown_asset_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "报告.md").write_text("# 报告\n\n正文。\n", encoding="utf-8")
            (root / "CON.json").write_text("{}", encoding="utf-8")
            completed = validate(root)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Windows-reserved", completed.stdout)

    def test_link_case_mismatch_is_rejected_even_on_case_insensitive_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "报告.md").write_text("# 报告\n\n[模块](./module.md)\n", encoding="utf-8")
            (root / "Module.md").write_text("# 模块\n\n正文。\n", encoding="utf-8")
            completed = validate(root)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("case-mismatched", completed.stdout)

    def test_chinese_space_parentheses_bom_and_crlf_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "中文 空格"
            root.mkdir()
            (root / "00-总览.md").write_text(
                "\ufeff# 总览\r\n\r\n[资料](<./资料%20%28一%29.md>)\r\n",
                encoding="utf-8",
            )
            (root / "资料 (一).md").write_text("# 资料\r\n\r\n不同内容。\r\n", encoding="utf-8")
            completed = validate(root, "--delivery-mode", "multi", "--h1-policy", "error")
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_multi_mode_requires_master_to_link_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "00-地图.md").write_text("# 地图\n\n[一](./01-一.md)\n", encoding="utf-8")
            (root / "01-一.md").write_text("# 一\n\n正文。\n", encoding="utf-8")
            (root / "02-二.md").write_text("# 二\n\n正文。\n", encoding="utf-8")
            completed = validate(root, "--delivery-mode", "multi")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("master document does not link", completed.stdout)


if __name__ == "__main__":
    unittest.main()
