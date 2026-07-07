import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTANT = ROOT / "scripts" / "actant.py"
sys.path.insert(0, str(ROOT / "scripts"))

from actantlib.cli import build_parser
from actantlib.contract import SPEC_CORE_FILES, SPEC_TEMPLATES, STAGE_FLOW, STAGES, default_gate


def run_cli(args, cwd=None, check=True):
    result = subprocess.run(
        [sys.executable, "-B", str(ACTANT), *args],
        cwd=cwd or ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed: {args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def make_planning_ready(run_dir):
    for filename in ["proposal.md", "requirements-delta.md", "tasks.md", "plan.md"]:
        (run_dir / filename).write_text("# test\n", encoding="utf-8")
    gate_path = run_dir / "gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["planning"].update(
        {
            "status": "ready",
            "evidence_refs": ["plan.md#verification-strategy"],
            "has_falsifiable_objective": True,
            "has_hypothesis_or_na_reason": True,
            "has_baseline": True,
            "has_evidence_plan": True,
            "verification_strategy_defined": True,
            "minimum_evidence_defined": True,
        }
    )
    write_json(gate_path, gate)


def make_battle_proceed(run_dir):
    (run_dir / "battle.md").write_text("# battle\n", encoding="utf-8")
    gate_path = run_dir / "gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["battle"].update(
        {
            "status": "ready",
            "evidence_refs": ["battle.md#verdict"],
            "verdict": "proceed",
            "requires_plan_update": False,
            "plan_update_applied": False,
        }
    )
    write_json(gate_path, gate)


def make_codeflow_ready(run_dir):
    (run_dir / "change-record.md").write_text("# change record\n", encoding="utf-8")
    write_json(
        run_dir / "fallback-audit.json",
        {
            "schema_version": 1,
            "status": "clear",
            "coverage": "changed-files-static",
            "findings": [],
            "declared_fallbacks": [],
        },
    )
    gate_path = run_dir / "gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["codeflow"].update(
        {
            "status": "ready",
            "evidence_refs": ["fallback-audit.json"],
            "rot_gate": "done",
            "simplifier": "done",
            "simplifier_not_applicable_reason": None,
            "fallback_audit": "clear",
        }
    )
    write_json(gate_path, gate)


def make_task_plan(run_dir, tasks, active_task_id="T-001", multi_task_reason=None):
    write_json(
        run_dir / "task-plan.json",
        {
            "schema_version": 1,
            "active_task_id": active_task_id,
            "multi_task_reason": multi_task_reason,
            "tasks": tasks,
        },
    )


def ready_task(task_id="T-001", **overrides):
    task = {
        "id": task_id,
        "title": f"Task {task_id}",
        "status": "ready",
        "depends_on": [],
        "change_budget": "single-concern",
        "prd_ref": None,
        "spec_refs": [".actant/specs/architecture.md"],
        "acceptance": ["CLI validation fails when this task boundary is violated"],
        "evidence": ["actant task validate command passes"],
    }
    task.update(overrides)
    return task


def active_run_dir(project_root):
    status = json.loads((project_root / ".actant" / "status.json").read_text(encoding="utf-8"))
    return project_root / ".actant" / "runs" / status["active_run_id"]


class ActantCliTests(unittest.TestCase):
    def test_contract_templates_and_gate_align_with_core_contract(self):
        gate = default_gate()
        self.assertEqual(list(STAGE_FLOW), list(STAGES))
        self.assertTrue(set(SPEC_CORE_FILES).issubset(set(SPEC_TEMPLATES)))
        for section in ["planning", "battle", "codeflow", "check", "evolution"]:
            self.assertIn(section, gate)

    def test_init_and_validate_empty_actant_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(["--project", tmp, "init"])
            result = run_cli(["--project", tmp, "validate"])
            self.assertIn("Actant structure valid", result.stdout)
            self.assertTrue((Path(tmp) / ".actant" / "memory" / "model-lineage.json").exists())
            self.assertTrue((Path(tmp) / ".actant" / "agent-profile.md").exists())
            self.assertTrue((Path(tmp) / ".actant" / "specs" / "context.md").exists())
            self.assertTrue((Path(tmp) / "AGENTS.md").exists())

    def test_init_preserves_agents_content_and_deduplicates_managed_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "AGENTS.md").write_text("# User Rules\n\nKeep this.\n", encoding="utf-8")
            run_cli(["--project", tmp, "init"])
            run_cli(["--project", tmp, "init"])
            text = (project / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("Keep this.", text)
            self.assertEqual(text.count("<!-- actant:start -->"), 1)
            self.assertEqual(text.count("<!-- actant:end -->"), 1)

    def test_spec_list_and_validate_skeleton(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(["--project", tmp, "init"])
            listed = run_cli(["--project", tmp, "spec", "list"])
            self.assertIn(".actant/specs/context.md", listed.stdout)
            self.assertIn(".actant/specs/guides/clear-answer.md", listed.stdout)
            result = run_cli(["--project", tmp, "spec", "validate"])
            self.assertIn("Actant spec validation passed", result.stdout)

    def test_spec_validate_rejects_broken_profile_reference_and_duplicate_agents_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            (project / ".actant" / "agent-profile.md").write_text(
                "Read `.actant/specs/missing.md`.\n", encoding="utf-8"
            )
            broken_ref = run_cli(["--project", tmp, "spec", "validate"], check=False)
            self.assertNotEqual(broken_ref.returncode, 0)
            self.assertIn("missing file", broken_ref.stderr)

            run_cli(["--project", tmp, "init", "--force"])
            with (project / "AGENTS.md").open("a", encoding="utf-8") as fh:
                fh.write("\n<!-- actant:start -->\nduplicate\n<!-- actant:end -->\n")
            duplicate = run_cli(["--project", tmp, "spec", "validate"], check=False)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn("exactly one", duplicate.stderr)

    def test_start_run_creates_valid_json_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(["--project", tmp, "init"])
            result = run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "promote",
                    "--objective",
                    "demo run",
                    "--slug",
                    "demo",
                ]
            )
            self.assertIn("Current stage: planning", result.stdout)

            status = json.loads((Path(tmp) / ".actant" / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["activation_mode"], "explicit-run")
            self.assertEqual(status["stage"], "planning")
            run_dir = active_run_dir(Path(tmp))
            gate = json.loads((run_dir / "gate.json").read_text(encoding="utf-8"))
            self.assertEqual(gate["schema_version"], 5)
            self.assertIn("spec", gate)
            self.assertIn("task", gate)
            self.assertIn("workflow", gate)
            self.assertIn("requires_plan_update", gate["battle"])
            self.assertIn("plan_update_applied", gate["battle"])
            self.assertIn("verification_strategy_defined", gate["planning"])
            self.assertIn("minimum_evidence_defined", gate["planning"])
            self.assertIn("strategy_followed", gate["check"])
            self.assertIn("evidence_sufficient_for_claim", gate["check"])
            self.assertIn("fallback_audit", gate["codeflow"])
            self.assertTrue((run_dir / "codeflow-context.jsonl").exists())
            self.assertTrue((run_dir / "check-context.jsonl").exists())
            self.assertTrue((run_dir / "spec-delta.md").exists())
            self.assertTrue((run_dir / "fallback-audit.json").exists())
            run_cli(["--project", tmp, "validate"])

    def test_start_run_rejects_no_record_memory_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "no-record",
                ],
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no-record is invalid", result.stderr)

    def test_advance_blocks_without_planning_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                    "--objective",
                    "demo run",
                ]
            )
            result = run_cli(["--project", tmp, "advance"], check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required artifact", result.stderr)

    def test_advance_blocks_when_verification_strategy_fields_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                    "--objective",
                    "demo run",
                ]
            )
            run_dir = active_run_dir(project)
            for filename in ["proposal.md", "requirements-delta.md", "tasks.md", "plan.md"]:
                (run_dir / filename).write_text("# test\n", encoding="utf-8")
            gate_path = run_dir / "gate.json"
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            gate["planning"].update(
                {
                    "status": "ready",
                    "has_falsifiable_objective": True,
                    "has_hypothesis_or_na_reason": True,
                    "has_baseline": True,
                    "has_evidence_plan": True,
                    "verification_strategy_defined": False,
                    "minimum_evidence_defined": False,
                }
            )
            write_json(gate_path, gate)
            result = run_cli(["--project", tmp, "advance"], check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("planning gate is not ready", result.stderr)

    def test_revise_and_proceed_requires_plan_update_before_codeflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                    "--objective",
                    "demo run",
                ]
            )
            run_dir = active_run_dir(project)
            make_planning_ready(run_dir)
            run_cli(["--project", tmp, "advance"])

            (run_dir / "battle.md").write_text("# battle\n", encoding="utf-8")
            gate_path = run_dir / "gate.json"
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            gate["battle"].update(
                {
                    "status": "ready",
                    "evidence_refs": ["battle.md#revise-and-proceed"],
                    "verdict": "revise-and-proceed",
                    "requires_plan_update": True,
                    "plan_update_applied": False,
                }
            )
            write_json(gate_path, gate)

            blocked = run_cli(["--project", tmp, "advance"], check=False)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("plan update", blocked.stderr)

            gate["battle"]["plan_update_applied"] = True
            write_json(gate_path, gate)
            advanced = run_cli(["--project", tmp, "advance"])
            self.assertIn("Current stage: codeflow", advanced.stdout)

    def test_check_pass_requires_strategy_followed_and_sufficient_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                    "--objective",
                    "demo run",
                ]
            )
            run_dir = active_run_dir(project)
            make_planning_ready(run_dir)
            run_cli(["--project", tmp, "advance"])
            make_battle_proceed(run_dir)
            run_cli(["--project", tmp, "advance"])
            make_codeflow_ready(run_dir)
            run_cli(["--project", tmp, "advance"])

            (run_dir / "check-report.md").write_text("# check report\n", encoding="utf-8")
            gate_path = run_dir / "gate.json"
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            gate["check"].update(
                {
                    "status": "ready",
                    "evidence_refs": ["check-report.md#direct-evidence"],
                    "result": "pass",
                    "has_direct_evidence": True,
                    "strategy_followed": False,
                    "evidence_sufficient_for_claim": False,
                    "validation_not_run_reason": None,
                }
            )
            write_json(gate_path, gate)
            blocked = run_cli(["--project", tmp, "advance"], check=False)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("strategy_followed", blocked.stderr)

            gate["check"]["strategy_followed"] = True
            write_json(gate_path, gate)
            still_blocked = run_cli(["--project", tmp, "advance"], check=False)
            self.assertNotEqual(still_blocked.returncode, 0)
            self.assertIn("evidence_sufficient_for_claim", still_blocked.stderr)

            gate["check"]["evidence_sufficient_for_claim"] = True
            write_json(gate_path, gate)
            advanced = run_cli(["--project", tmp, "advance"])
            self.assertIn("Current stage: evolution", advanced.stdout)

    def test_task_validate_rejects_multiple_active_tasks_without_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                ]
            )
            run_dir = active_run_dir(project)
            make_task_plan(
                run_dir,
                [
                    ready_task("T-001", status="active"),
                    ready_task("T-002", status="active"),
                ],
                active_task_id="T-001",
            )
            result = run_cli(["--project", tmp, "task", "validate"], check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("multiple active tasks", result.stderr)

            make_task_plan(
                run_dir,
                [
                    ready_task("T-001", status="active"),
                    ready_task("T-002", status="active"),
                ],
                active_task_id="T-001",
                multi_task_reason="Both tasks share one CLI validation boundary.",
            )
            ok = run_cli(["--project", tmp, "task", "validate"])
            self.assertIn("Actant task validation passed", ok.stdout)

    def test_task_validate_rejects_missing_or_generic_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                ]
            )
            run_dir = active_run_dir(project)
            make_task_plan(run_dir, [ready_task(evidence=[])])
            missing = run_cli(["--project", tmp, "task", "validate"], check=False)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("evidence", missing.stderr)

            make_task_plan(run_dir, [ready_task(evidence=["better"])])
            generic = run_cli(["--project", tmp, "task", "validate"], check=False)
            self.assertNotEqual(generic.returncode, 0)
            self.assertIn("evidence", generic.stderr)

    def test_spec_validate_rejects_unapproved_spec_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "promote",
                ]
            )
            run_dir = active_run_dir(project)
            gate_path = run_dir / "gate.json"
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            gate["spec"]["trigger"] = "promotion"
            gate["spec"]["promotion_approved"] = False
            write_json(gate_path, gate)
            result = run_cli(["--project", tmp, "spec", "validate"], check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("promotion requires", result.stderr)

    def test_spec_validate_rejects_unregistered_spec_file_and_accepts_init_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            (project / ".actant" / "specs" / "new-guide.md").write_text("# New\n", encoding="utf-8")
            rejected = run_cli(["--project", tmp, "spec", "validate"], check=False)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("trigger record", rejected.stderr)

            (project / ".actant" / "specs" / "new-guide.md").unlink()
            created = run_cli(
                [
                    "--project",
                    tmp,
                    "spec",
                    "init-capability",
                    "demo-capability",
                    "--title",
                    "Demo Capability",
                ]
            )
            self.assertIn("Initialized capability", created.stdout)
            ok = run_cli(["--project", tmp, "spec", "validate"])
            self.assertIn("Actant spec validation passed", ok.stdout)

    def test_spec_add_context_rejects_code_paths_and_accepts_spec_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                ]
            )
            accepted = run_cli(
                [
                    "--project",
                    tmp,
                    "spec",
                    "add-context",
                    "active",
                    "codeflow",
                    ".actant/specs/architecture.md",
                    "--reason",
                    "Contract for codeflow",
                ]
            )
            self.assertIn("Added codeflow context", accepted.stdout)
            (project / "script.py").write_text("print('x')\n", encoding="utf-8")
            rejected = run_cli(
                [
                    "--project",
                    tmp,
                    "spec",
                    "add-context",
                    "active",
                    "check",
                    "script.py",
                    "--reason",
                    "Bad code path",
                ],
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("illegal", rejected.stderr)

    def test_advance_disables_through_to_prevent_auto_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                ]
            )
            result = run_cli(["--project", tmp, "advance", "--through", "codeflow"], check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no-auto-chain", result.stderr)

    def test_validate_detects_status_and_run_recovery_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                ]
            )
            run_dir = active_run_dir(project)
            run_path = run_dir / "run.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["next_recommended_action"] = "drifted"
            write_json(run_path, run)
            result = run_cli(["--project", tmp, "validate"], check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("recovery mismatch", result.stderr)

    def test_cli_output_contains_single_next_explicit_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                ]
            )
            self.assertEqual(result.stdout.count("Recommended next explicit action:"), 1)

    def test_parser_and_cli_do_not_expose_profile_commands(self):
        help_text = build_parser().format_help()
        self.assertNotIn("profile", help_text)
        result = run_cli(["profile"], check=False)
        self.assertNotEqual(result.returncode, 0)

    def test_legacy_v2_gate_without_spec_still_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                ]
            )
            run_dir = active_run_dir(project)
            gate_path = run_dir / "gate.json"
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            for key in ["schema_version", "spec", "task", "workflow"]:
                gate.pop(key, None)
            write_json(gate_path, gate)
            result = run_cli(["--project", tmp, "validate"])
            self.assertIn("Actant validation passed", result.stdout)

    def test_legacy_v3_gate_without_new_verification_fields_still_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                ]
            )
            run_dir = active_run_dir(project)
            gate_path = run_dir / "gate.json"
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            gate["schema_version"] = 3
            gate["planning"].pop("verification_strategy_defined", None)
            gate["planning"].pop("minimum_evidence_defined", None)
            gate["check"].pop("strategy_followed", None)
            gate["check"].pop("evidence_sufficient_for_claim", None)
            write_json(gate_path, gate)
            result = run_cli(["--project", tmp, "validate"])
            self.assertIn("Actant validation passed", result.stdout)

    def test_default_discovery_excludes_maintainer_release_tests(self):
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_public_release.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertIn(result.returncode, {0, 5}, result.stdout + result.stderr)
        self.assertIn("Ran 0 tests", result.stderr)
        self.assertTrue((ROOT / "maintainer_tests" / "test_public_release.py").exists())

    def test_gate_evidence_refs_required_for_high_impact_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                ]
            )
            run_dir = active_run_dir(project)
            gate_path = run_dir / "gate.json"
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            gate["planning"]["status"] = "ready"
            write_json(gate_path, gate)
            missing_refs = run_cli(["--project", tmp, "validate"], check=False)
            self.assertNotEqual(missing_refs.returncode, 0)
            self.assertIn("planning.evidence_refs", missing_refs.stderr)

            gate["planning"]["evidence_refs"] = ["plan.md#evidence-plan"]
            write_json(gate_path, gate)
            ok = run_cli(["--project", tmp, "validate"])
            self.assertIn("Actant validation passed", ok.stdout)

    def test_fallback_audit_reports_findings_without_claiming_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                ]
            )
            (project / "demo.py").write_text(
                "def load(mapping):\n"
                "    try:\n"
                "        return mapping.get('value', None)\n"
                "    except Exception:\n"
                "        return None\n",
                encoding="utf-8",
            )
            result = run_cli(["--project", tmp, "fallback-audit", "scan", "--file", "demo.py"])
            self.assertIn("Fallback audit findings", result.stdout)
            audit = json.loads((active_run_dir(project) / "fallback-audit.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["status"], "findings")
            self.assertEqual(audit["coverage"], "changed-files-static")
            self.assertTrue(any(item["kind"] == "broad-except" for item in audit["findings"]))
            self.assertNotIn("proof", json.dumps(audit).lower())

    def test_declared_fallback_requires_reason_scope_visibility_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                ]
            )
            run_dir = active_run_dir(project)
            write_json(
                run_dir / "fallback-audit.json",
                {
                    "schema_version": 1,
                    "status": "findings",
                    "coverage": "changed-files-static",
                    "findings": [
                        {
                            "id": "demo.py:4:broad-except",
                            "path": "demo.py",
                            "line": 4,
                            "kind": "broad-except",
                            "message": "broad Exception handler",
                        }
                    ],
                    "declared_fallbacks": [
                        {
                            "reason": "Third-party parser may be absent in scratch projects.",
                            "scope": "demo.py:4",
                            "user_visible_behavior": "The command exits with a clear diagnostic.",
                        }
                    ],
                },
            )
            result = run_cli(["--project", tmp, "fallback-audit", "validate"], check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires test_ref", result.stderr)

    def test_codeflow_gate_blocks_unresolved_fallback_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                    "--objective",
                    "demo run",
                ]
            )
            run_dir = active_run_dir(project)
            make_planning_ready(run_dir)
            run_cli(["--project", tmp, "advance"])
            make_battle_proceed(run_dir)
            run_cli(["--project", tmp, "advance"])
            (run_dir / "change-record.md").write_text("# change record\n\nFallback Audit: findings\n", encoding="utf-8")
            finding = {
                "id": "demo.py:4:broad-except",
                "path": "demo.py",
                "line": 4,
                "kind": "broad-except",
                "message": "broad Exception handler",
            }
            write_json(
                run_dir / "fallback-audit.json",
                {
                    "schema_version": 1,
                    "status": "findings",
                    "coverage": "changed-files-static",
                    "findings": [finding],
                    "declared_fallbacks": [],
                },
            )
            gate_path = run_dir / "gate.json"
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            gate["codeflow"].update(
                {
                    "status": "ready",
                    "evidence_refs": ["fallback-audit.json"],
                    "rot_gate": "done",
                    "simplifier": "done",
                    "simplifier_not_applicable_reason": None,
                    "fallback_audit": "findings",
                }
            )
            write_json(gate_path, gate)

            blocked = run_cli(["--project", tmp, "advance"], check=False)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("unresolved finding", blocked.stderr)

            audit = json.loads((run_dir / "fallback-audit.json").read_text(encoding="utf-8"))
            audit["declared_fallbacks"] = [
                {
                    "reason": "The approved slice intentionally reports optional parser absence.",
                    "scope": "demo.py:4",
                    "user_visible_behavior": "The user sees a clear validation error instead of silent recovery.",
                    "test_ref": "tests/test_demo.py::test_optional_parser_error",
                }
            ]
            write_json(run_dir / "fallback-audit.json", audit)
            advanced = run_cli(["--project", tmp, "advance"])
            self.assertIn("Current stage: check", advanced.stdout)

    def test_task_split_start_and_finish(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_cli(["--project", tmp, "init"])
            run_cli(
                [
                    "--project",
                    tmp,
                    "start-run",
                    "--activation-mode",
                    "explicit-run",
                    "--scope",
                    "project",
                    "--memory-policy",
                    "record-only",
                ]
            )
            run_cli(
                [
                    "--project",
                    tmp,
                    "task",
                    "split",
                    "--title",
                    "Add validation task",
                    "--spec-ref",
                    ".actant/specs/architecture.md",
                    "--acceptance",
                    "CLI validation fails when acceptance is absent",
                    "--evidence",
                    "actant task validate command passes",
                ]
            )
            start = run_cli(["--project", tmp, "task", "start", "T-001"])
            self.assertIn("Started task", start.stdout)
            run_dir = active_run_dir(project)
            gate = json.loads((run_dir / "gate.json").read_text(encoding="utf-8"))
            self.assertEqual(gate["task"]["active_task_id"], "T-001")
            finish = run_cli(["--project", tmp, "task", "finish", "T-001"])
            self.assertIn("Finished task", finish.stdout)

    def test_gitignore_keeps_release_zip_artifacts_visible(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("dist/*.zip", gitignore)

if __name__ == "__main__":
    unittest.main()
