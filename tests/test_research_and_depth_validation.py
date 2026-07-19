from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from validate_depth import TIER_TOTAL_MINIMUM_NPU, calculated_floor
from validate_review import (
    INPUT_SCOPE,
    REQUIRED_GATES,
    candidate_digest,
    contract_digest,
    evidence_bundle_digest,
    markdown_location_exists,
)


def run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPTS / script), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def template_header(name: str) -> list[str]:
    with (ROOT / "assets" / name).open(encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


class ResearchAndDepthValidationTests(unittest.TestCase):
    def write_ledgers(self, root: Path, same_family: bool = False, same_evidence: bool = False) -> tuple[Path, Path]:
        source_path = root / "来源.csv"
        claim_path = root / "主张.csv"
        source_fields = template_header("source-ledger.template.csv")
        claim_fields = template_header("claim-evidence-ledger.template.csv")
        sources = []
        for index in (1, 2):
            row = {field: "" for field in source_fields}
            row.update(
                {
                    "source_id": f"S{index}",
                    "title": f"来源{index}",
                    "url_or_locator": f"https://example.com/{index}",
                    "exact_locator": f"p.{index}",
                    "source_role": "original",
                    "underlying_evidence_id": "E1" if same_evidence else f"E{index}",
                    "source_family_id": "F1" if same_family else f"F{index}",
                    "qualified_unique_source": "true",
                    "direct_or_primary": "true",
                    "counter_or_alternative": "true" if index == 2 else "false",
                    "verification_status": "verified",
                }
            )
            sources.append(row)
        claim = {field: "" for field in claim_fields}
        claim.update(
            {
                "claim_id": "C1",
                "claim_text": "关键机制在当前范围内成立",
                "risk_level": "high",
                "claim_type": "causal",
                "decisive": "true",
                "applicable_scope": "当前研究范围",
                "supporting_source_ids": "S1;S2",
                "counter_source_ids": "S2",
                "counterevidence_status": "found",
                "reasoning_status": "synthesis",
                "evidence_status": "supported",
                "entailment_reviewed": "true",
                "independent_family_count": "1" if (same_family or same_evidence) else "2",
                "evidence_bridge": "两项独立证据分别支持机制链的两个环节",
                "key_assumptions": "测量口径可比",
                "alternative_explanations": "选择偏差",
                "boundary_conditions": "仅限当前人群",
                "flip_conditions": "出现相反的随机证据",
                "current_judgment": "条件性成立",
                "write_location": "报告.md#核心问题",
                "reasoned_explanation_location": "报告.md#核心问题",
                "verification_notes": "已复核",
            }
        )
        with source_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=source_fields)
            writer.writeheader()
            writer.writerows(sources)
        with claim_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=claim_fields)
            writer.writeheader()
            writer.writerow(claim)
        return source_path, claim_path

    def test_claim_hard_gates_pass_while_source_target_is_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path, claim_path = self.write_ledgers(Path(tmp))
            completed = run(
                "validate_research.py",
                "--sources",
                str(source_path),
                "--claims",
                str(claim_path),
                "--tier",
                "medium",
            )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("source target shortfall", completed.stdout)

    def test_strict_source_contract_can_promote_target_to_hard_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path, claim_path = self.write_ledgers(Path(tmp))
            completed = run(
                "validate_research.py",
                "--sources",
                str(source_path),
                "--claims",
                str(claim_path),
                "--tier",
                "medium",
                "--strict-source-targets",
            )
        self.assertNotEqual(completed.returncode, 0)

    def test_same_family_does_not_count_as_independent_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path, claim_path = self.write_ledgers(Path(tmp), same_family=True)
            completed = run("validate_research.py", "--sources", str(source_path), "--claims", str(claim_path), "--tier", "light")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("independent support group", completed.stdout)

    def test_same_underlying_evidence_cannot_be_counted_twice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path, claim_path = self.write_ledgers(Path(tmp), same_evidence=True)
            completed = run("validate_research.py", "--sources", str(source_path), "--claims", str(claim_path), "--tier", "light")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("independent support group", completed.stdout)

    def depth_contract(self) -> dict:
        unit = {
            "unit_id": "U1",
            "question": "为什么会发生？",
            "reader_outcome": "能解释核心因果关系",
            "importance": "central",
            "core_question_ids": ["Q1"],
            "scores": {"complexity": 1, "dispute": 1, "audience_gap": 1, "risk": 1},
            "facets": {
                "definitions": 1,
                "distinctions": 0,
                "mechanism_links": 1,
                "evidence_clusters": 1,
                "alternatives": 1,
                "boundaries": 1,
                "cases": 1,
                "implications": 1,
                "transfers": 1,
                "worked_examples": 0,
                "failure_traces": 0,
                "reproducible_checks": 0,
                "exercises": 0,
            },
            "delivery": {"location": "报告.md#核心问题"},
            "capacity": {
                "floor_npu": 0,
                "previous_floor_npu": 0,
                "revision_reason": "",
                "reconfirmed_after_reduction": False,
            },
            "semantic_audit": {
                "conclusion_clear": True,
                "evidence_interpreted": True,
                "reasoning_bridge_visible": True,
                "mechanism_explained_or_unknown_stated": True,
                "alternatives_handled": True,
                "boundaries_stated": True,
                "example_or_counterexample_used": True,
                "implication_explained": True,
                "transfer_test_passed": True,
                "transition_coherent": True,
                "reviewer_note": "通过",
            },
        }
        floor = calculated_floor(unit, "medium")
        unit["capacity"]["floor_npu"] = floor
        integration_floor = 500
        return {
            "schema_version": "1.0",
            "counting_mode": "npu-v1",
            "task_type": "learning-report",
            "tier": "medium",
            "contract_version": 1,
            "reader_profile": "有基础但不熟悉该主题的读者",
            "calibration_rationale": "核心问题需要机制、反方、边界、案例与迁移，评分采用中等负荷",
            "alignment_confirmed_at": "2026-07-18T09:00:00+08:00",
            "frozen_at": "2026-07-18T10:00:00+08:00",
            "revision_reason": "",
            "reconfirmed_after_reduction": False,
            "previous_total_floor_npu": 0,
            "total_floor_npu": max(floor + integration_floor, TIER_TOTAL_MINIMUM_NPU["medium"]),
            "expected_band_npu": [
                max(floor + integration_floor, TIER_TOTAL_MINIMUM_NPU["medium"]),
                max(floor + integration_floor, TIER_TOTAL_MINIMUM_NPU["medium"]) + 1000,
            ],
            "max_exact_duplicate_ratio": 0.03,
            "max_near_duplicate_ratio": 0.08,
            "independent_critic_required": True,
            "candidate_files": ["报告.md"],
            "evidence_files": ["audit/evidence.txt"],
            "core_questions": [{"question_id": "Q1", "question": "为什么会发生？"}],
            "review_records": {
                "evidence-logic": "audit/evidence-review.json",
                "blind-reader": "audit/blind-review.json",
            },
            "integration": {"location": "报告.md#综合判断", "floor_npu": integration_floor},
            "units": [unit],
        }

    def write_contract_and_reviews(self, root: Path, contract: dict) -> Path:
        audit = root / "audit"
        audit.mkdir()
        evidence_path = audit / "evidence.txt"
        evidence_path.write_text("这是冻结的证据包，用于验证审查后证据不能被静默替换。\n", encoding="utf-8")
        contract_path = root / "depth.json"
        contract_path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
        digest = candidate_digest(root, contract["candidate_files"])
        frozen_contract_digest = contract_digest(contract_path)
        frozen_evidence_digest = evidence_bundle_digest(root, contract["evidence_files"])
        for review_type, filename, reviewer_id in (
            ("evidence-logic", "evidence-review.json", "critic-evidence"),
            ("blind-reader", "blind-review.json", "critic-reader"),
        ):
            record = {
                "schema_version": "1.0",
                "review_id": f"review-{review_type}",
                "review_type": review_type,
                "reviewer_id": reviewer_id,
                "reviewer_context_id": f"context-{review_type}",
                "reviewer_role": review_type,
                "reviewer_provenance": "independent-agent-context",
                "author_involved": False,
                "independent_context": True,
                "input_scope": INPUT_SCOPE[review_type],
                "candidate_sha256": digest,
                "contract_sha256": frozen_contract_digest,
                "evidence_bundle_sha256": frozen_evidence_digest if review_type == "evidence-logic" else "",
                "contract_version": 1,
                "reviewed_at": "2026-07-18T12:00:00+08:00",
                "status": "PASS",
                "preregistered_attack_surface": [
                    "检查核心结论是否存在没有证据支持的因果跳跃",
                    "检查引用来源是否真正蕴含正文中的决定性主张",
                    "检查适用边界和结论翻转条件是否被完整写出",
                    "检查重复改写和外围材料是否被用来虚增篇幅",
                ],
                "gate_results": [
                    {
                        "gate": gate,
                        "status": "PASS",
                        "evidence_location": "报告.md#核心问题",
                        "finding": "审查者针对该门执行了具体攻击并在对应章节找到可复核的通过依据",
                    }
                    for gate in sorted(REQUIRED_GATES[review_type])
                ],
                "issues": [],
                "strongest_counterargument": {
                    "argument": "最强替代机制可以在不依赖当前因果解释的情况下产生相同观察结果，因此必须比较可区分预测",
                    "disposition": "正文已经给出两种机制在关键边界变量变化时的不同预测，并说明当前证据为何更支持现有判断",
                    "evidence_location": "报告.md#核心问题",
                },
                "filler_audit": {
                    "status": "PASS",
                    "evidence": "已核对自动重复折损结果并逐段检查同义改写、模板小结、来源堆叠和无关历史，没有发现实质填充",
                    "effective_npu": contract["total_floor_npu"],
                    "exact_duplicate_ratio": 0,
                    "near_duplicate_ratio": 0,
                },
                "novel_transfer_test": {
                    "status": "PASS" if review_type == "blind-reader" else "not-applicable",
                    "novel_case": "在正文未直接讨论的新情境中同时改变关键边界变量与证据质量，要求读者重新判断" if review_type == "blind-reader" else "",
                    "model_reproduced": "读者能够不借助来源台账完整复述变量、机制链、替代解释和结论翻转条件" if review_type == "blind-reader" else "",
                    "application_result": "读者用复述出的模型得到条件化判断，并指出还需要观察哪项证据才能提高置信度" if review_type == "blind-reader" else "",
                },
            }
            (audit / filename).write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return contract_path

    def test_central_unit_cannot_lowball_all_semantic_facets(self) -> None:
        contract = self.depth_contract()
        unit = contract["units"][0]
        unit["facets"] = {field: 0 for field in unit["facets"]}
        with self.assertRaises(ValueError):
            calculated_floor(unit, "medium")

    def test_dynamic_npu_contract_passes_distinct_explanatory_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = self.depth_contract()
            floor = contract["units"][0]["capacity"]["floor_npu"]
            total_floor = contract["total_floor_npu"]
            (root / "报告.md").write_text(
                "# 报告\n\n## 核心问题\n\n" + "甲" * max(floor + 100, total_floor - 450) + "\n\n## 综合判断\n\n" + "乙" * 560,
                encoding="utf-8",
            )
            contract_path = self.write_contract_and_reviews(root, contract)
            completed = run("validate_depth.py", "--contract", str(contract_path), "--deliverable", str(root), "--tier", "medium")
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_repeated_padding_is_discounted_and_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = self.depth_contract()
            repeated = "这是同一个没有增加理解的句子，反复出现只是为了填充篇幅。" * 5
            (root / "报告.md").write_text(
                "# 报告\n\n## 核心问题\n\n" + repeated + "\n\n" + repeated + "\n\n## 综合判断\n\n" + "乙" * 560,
                encoding="utf-8",
            )
            contract_path = self.write_contract_and_reviews(root, contract)
            completed = run("validate_depth.py", "--contract", str(contract_path), "--deliverable", str(root), "--tier", "medium")
        self.assertNotEqual(completed.returncode, 0)
        self.assertTrue("duplicate" in completed.stdout or "below dynamic floor" in completed.stdout)

    def test_lists_and_tables_cannot_replace_explanatory_prose(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = self.depth_contract()
            bullets = "\n".join(f"- 项目{i}" + "甲" * 80 for i in range(20))
            table = "\n".join(["| 项目 | 内容 |", "|---|---|"] + [f"| {i} | " + "乙" * 80 + " |" for i in range(20)])
            (root / "报告.md").write_text(
                "# 报告\n\n## 核心问题\n\n" + bullets + "\n\n## 综合判断\n\n" + table,
                encoding="utf-8",
            )
            contract_path = self.write_contract_and_reviews(root, contract)
            completed = run("validate_depth.py", "--contract", str(contract_path), "--deliverable", str(root), "--tier", "medium")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("below", completed.stdout)

    def test_contract_tier_cannot_be_silently_downgraded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = self.depth_contract()
            floor = contract["units"][0]["capacity"]["floor_npu"]
            total_floor = contract["total_floor_npu"]
            (root / "报告.md").write_text(
                "# 报告\n\n## 核心问题\n\n" + "甲" * max(floor + 100, total_floor - 450) + "\n\n## 综合判断\n\n" + "乙" * 560,
                encoding="utf-8",
            )
            contract_path = self.write_contract_and_reviews(root, contract)
            completed = run("validate_depth.py", "--contract", str(contract_path), "--deliverable", str(root), "--tier", "heavy")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("does not match requested tier", completed.stdout)

    def test_non_object_depth_contract_returns_stable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "报告.md").write_text("# 报告\n", encoding="utf-8")
            contract_path = root / "depth.json"
            contract_path.write_text("[]", encoding="utf-8")
            completed = run("validate_depth.py", "--contract", str(contract_path), "--deliverable", str(root), "--tier", "medium")
        self.assertEqual(completed.returncode, 2)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)

    def test_csv_extra_fields_return_stable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path, claim_path = self.write_ledgers(Path(tmp))
            with source_path.open("a", encoding="utf-8") as handle:
                handle.write(",".join(["extra"] * (len(template_header("source-ledger.template.csv")) + 1)) + "\n")
            completed = run("validate_research.py", "--sources", str(source_path), "--claims", str(claim_path), "--tier", "light")
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)

    def test_review_pass_is_invalid_after_candidate_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = self.depth_contract()
            floor = contract["units"][0]["capacity"]["floor_npu"]
            total_floor = contract["total_floor_npu"]
            report = root / "报告.md"
            report.write_text(
                "# 报告\n\n## 核心问题\n\n" + "甲" * max(floor + 100, total_floor - 450) + "\n\n## 综合判断\n\n" + "乙" * 560,
                encoding="utf-8",
            )
            contract_path = self.write_contract_and_reviews(root, contract)
            report.write_text(report.read_text(encoding="utf-8") + "\n语义改动。\n", encoding="utf-8")
            completed = run("validate_depth.py", "--contract", str(contract_path), "--deliverable", str(root), "--tier", "medium")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("old PASS is invalid", completed.stdout)

    def test_candidate_digest_includes_uppercase_markdown_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "REPORT.MD"
            report.write_text("# Report\n\nFirst version.\n", encoding="utf-8")
            before = candidate_digest(root)
            report.write_text("# Report\n\nSecond version.\n", encoding="utf-8")
            after = candidate_digest(root)
        self.assertNotEqual(before, after)

    def test_candidate_digest_is_stable_across_bom_and_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "报告.md"
            report.write_text("\ufeff# 报告\r\n\r\n相同正文。\r\n", encoding="utf-8")
            windows_digest = candidate_digest(root)
            report.write_text("# 报告\n\n相同正文。\n", encoding="utf-8")
            posix_digest = candidate_digest(root)
        self.assertEqual(windows_digest, posix_digest)

    def test_candidate_digest_changes_when_linked_image_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "报告.md").write_text("# 报告\n\n![机制图](./model.png)\n", encoding="utf-8")
            image = root / "model.png"
            image.write_bytes(b"first-image")
            before = candidate_digest(root, ["报告.md", "model.png"])
            image.write_bytes(b"second-image")
            after = candidate_digest(root, ["报告.md", "model.png"])
        self.assertNotEqual(before, after)

    def test_contract_digest_is_stable_across_json_formatting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "depth.json"
            value = {"合同": "相同", "contract_version": 1}
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
            pretty_digest = contract_digest(path)
            path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            compact_digest = contract_digest(path)
        self.assertEqual(pretty_digest, compact_digest)

    def test_review_location_rejects_case_mismatch_on_any_host(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Report.md").write_text("# Evidence\n\nText.\n", encoding="utf-8")
            self.assertTrue(markdown_location_exists(root, "Report.md#Evidence"))
            self.assertFalse(markdown_location_exists(root, "report.md#Evidence"))

    def test_review_rejects_fake_locations_and_shallow_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = self.depth_contract()
            total_floor = contract["total_floor_npu"]
            (root / "报告.md").write_text(
                "# 报告\n\n## 核心问题\n\n" + "甲" * (total_floor - 450) + "\n\n## 综合判断\n\n" + "乙" * 560,
                encoding="utf-8",
            )
            contract_path = self.write_contract_and_reviews(root, contract)
            review_path = root / "audit" / "evidence-review.json"
            record = json.loads(review_path.read_text(encoding="utf-8"))
            record["gate_results"][0]["evidence_location"] = "does-not-exist.md#x"
            record["gate_results"][0]["finding"] = "x"
            review_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            completed = run(
                "validate_review.py",
                "--record",
                str(review_path),
                "--deliverable",
                str(root),
                "--contract",
                str(contract_path),
                "--review-type",
                "evidence-logic",
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("valid Markdown heading", completed.stdout)
        self.assertIn("substantive finding", completed.stdout)

    def test_evidence_review_pass_is_invalid_after_ledger_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = self.depth_contract()
            total_floor = contract["total_floor_npu"]
            (root / "报告.md").write_text(
                "# 报告\n\n## 核心问题\n\n" + "甲" * (total_floor - 450) + "\n\n## 综合判断\n\n" + "乙" * 560,
                encoding="utf-8",
            )
            contract_path = self.write_contract_and_reviews(root, contract)
            (root / "audit" / "evidence.txt").write_text("证据包在审查以后被替换。\n", encoding="utf-8")
            completed = run(
                "validate_review.py",
                "--record",
                str(root / "audit" / "evidence-review.json"),
                "--deliverable",
                str(root),
                "--contract",
                str(contract_path),
                "--review-type",
                "evidence-logic",
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("evidence_bundle_sha256", completed.stdout)

    def test_super_heavy_contract_cannot_set_tiny_total_floor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = self.depth_contract()
            contract["tier"] = "super-heavy"
            unit = contract["units"][0]
            unit_floor = calculated_floor(unit, "super-heavy")
            unit["capacity"]["floor_npu"] = unit_floor
            integration_floor = 500
            contract["integration"]["floor_npu"] = integration_floor
            contract["total_floor_npu"] = unit_floor + integration_floor
            contract["expected_band_npu"] = [unit_floor + integration_floor, unit_floor + integration_floor + 1000]
            (root / "报告.md").write_text(
                "# 报告\n\n## 核心问题\n\n" + "甲" * (unit_floor + 100) + "\n\n## 综合判断\n\n" + "乙" * 560,
                encoding="utf-8",
            )
            contract_path = self.write_contract_and_reviews(root, contract)
            completed = run(
                "validate_depth.py",
                "--contract",
                str(contract_path),
                "--deliverable",
                str(root),
                "--tier",
                "super-heavy",
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("tier safety floor 15000", completed.stdout)

    def test_document_coverage_requires_every_core_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "coverage.csv"
            fields = template_header("document-coverage.template.csv")
            row = {field: "" for field in fields}
            row.update(
                {
                    "coverage_id": "D1",
                    "source_id": "S1",
                    "source_locator": "report.pdf",
                    "outline_item": "第一章",
                    "page_or_exact_locator": "pp.1-10",
                    "range_start": "1",
                    "range_end": "10",
                    "coverage_status": "covered",
                    "mapped_core_question_ids": "Q1",
                    "mapped_explanation_unit_ids": "U1",
                    "notes": "提取核心定义和限定",
                }
            )
            with ledger.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(row)
            completed = run(
                "validate_coverage.py",
                "--ledger",
                str(ledger),
                "--expected-items",
                "1",
                "--core-question-id",
                "Q1",
                "--central-unit-id",
                "U1",
                "--source-units",
                "S1=10",
            )
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_technical_learning_cannot_omit_execution_and_practice_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = self.depth_contract()
            contract["task_type"] = "technical-learning"
            floor = contract["units"][0]["capacity"]["floor_npu"]
            total_floor = contract["total_floor_npu"]
            (root / "报告.md").write_text(
                "# 报告\n\n## 核心问题\n\n" + "甲" * max(floor + 100, total_floor - 450) + "\n\n## 综合判断\n\n" + "乙" * 560,
                encoding="utf-8",
            )
            contract_path = self.write_contract_and_reviews(root, contract)
            completed = run("validate_depth.py", "--contract", str(contract_path), "--deliverable", str(root), "--tier", "medium")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("technical-learning gate is missing", completed.stdout)


if __name__ == "__main__":
    unittest.main()
