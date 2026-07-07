import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "scripts"))

from actantlib.codex_install import (  # noqa: E402
    ROOT_SKILL_DIRS,
    SUBSKILL_NAMES,
    ensure_request_user_input_flag,
    ensure_skill_registry_entries,
    install_into_codex,
)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build_source_tree(root: Path) -> None:
    write_text(root / "SKILL.md", "---\nname: actant\n---\n")
    for dirname in ROOT_SKILL_DIRS:
        write_text(root / dirname / "placeholder.txt", f"{dirname}\n")
    for name in SUBSKILL_NAMES:
        write_text(root / "skills" / name / "SKILL.md", f"---\nname: {name}\n---\n")
        write_text(root / "skills" / name / "agents" / "openai.yaml", "policy:\n  allow_implicit_invocation: false\n")


def build_installed_layout(root: Path) -> Path:
    actant_root = root / "actant"
    write_text(actant_root / "SKILL.md", "---\nname: actant\n---\n")
    for dirname in ROOT_SKILL_DIRS:
        write_text(actant_root / dirname / "placeholder.txt", f"{dirname}\n")
    for name in SUBSKILL_NAMES:
        write_text(root / name / "SKILL.md", f"---\nname: {name}\n---\n")
        write_text(root / name / "agents" / "openai.yaml", "policy:\n  allow_implicit_invocation: false\n")
    return actant_root


class CodexInstallTests(unittest.TestCase):
    def test_ensure_request_user_input_flag_updates_existing_features_section(self):
        text = "[features]\njs_repl = false\ndefault_mode_request_user_input = false\n"
        updated, changed = ensure_request_user_input_flag(text)
        self.assertTrue(changed)
        self.assertIn("default_mode_request_user_input = true", updated)
        self.assertNotIn("default_mode_request_user_input = false", updated)

    def test_ensure_skill_registry_entries_enables_existing_block_and_appends_missing(self):
        planning = Path(r"C:\Users\Tian\.codex\skills\actant-planning\SKILL.md")
        battle = Path(r"C:\Users\Tian\.codex\skills\actant-battle\SKILL.md")
        text = (
            "[[skills.config]]\n"
            f"path = '{planning}'\n"
            "enabled = false\n"
        )
        updated, changed = ensure_skill_registry_entries(text, [planning, battle])
        self.assertTrue(changed)
        self.assertIn(f"path = '{planning}'", updated)
        self.assertIn(f"path = '{battle}'", updated)
        self.assertEqual(updated.count("[[skills.config]]"), 2)
        self.assertEqual(updated.count("enabled = true"), 2)

    def test_install_into_codex_copies_skills_and_updates_config(self):
        with tempfile.TemporaryDirectory() as src_tmp, tempfile.TemporaryDirectory() as codex_tmp:
            source_root = Path(src_tmp)
            codex_home = Path(codex_tmp)
            build_source_tree(source_root)

            config_path = codex_home / "config.toml"
            planning_path = codex_home / "skills" / "actant-planning" / "SKILL.md"
            write_text(
                config_path,
                "[features]\njs_repl = false\n\n"
                "[[skills.config]]\n"
                f"path = '{planning_path}'\n"
                "enabled = false\n",
            )

            summary = install_into_codex(source_root=source_root, codex_home=codex_home)

            self.assertTrue((codex_home / "skills" / "actant" / "SKILL.md").exists())
            for name in SUBSKILL_NAMES:
                self.assertTrue((codex_home / "skills" / name / "SKILL.md").exists())
            self.assertTrue(summary.config_changed)
            self.assertIsNotNone(summary.backup_path)
            self.assertTrue(summary.backup_path.exists())

            config_text = config_path.read_text(encoding="utf-8")
            self.assertIn("default_mode_request_user_input = true", config_text)
            for installed_path in summary.installed_skill_paths:
                self.assertIn(f"path = '{installed_path}'", config_text)
            self.assertNotIn("enabled = false", config_text)

    def test_install_into_codex_accepts_installed_style_source_layout(self):
        with tempfile.TemporaryDirectory() as src_tmp, tempfile.TemporaryDirectory() as codex_tmp:
            source_root = build_installed_layout(Path(src_tmp))
            codex_home = Path(codex_tmp)

            summary = install_into_codex(source_root=source_root, codex_home=codex_home)

            self.assertEqual(len(summary.installed_skill_paths), 6)
            self.assertTrue((codex_home / "skills" / "actant" / "SKILL.md").exists())
            self.assertTrue((codex_home / "skills" / "actant-planning" / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
