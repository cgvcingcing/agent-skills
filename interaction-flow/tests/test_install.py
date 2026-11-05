"""Exercise the installer in disposable configuration roots."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree


PROJECT = Path(__file__).resolve().parent.parent


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="interaction-flow-check-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source project 技能"
        shutil.copytree(PROJECT, self.source, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
        self.codex_home = self.root / "codex config"
        self.claude_home = self.root / "claude 配置"
        self.codex_skill = self.codex_home / "skills/interaction-flow"
        self.claude_skill = self.claude_home / "skills/interaction-flow"
        self.invocation = self.root / "business project 业务"
        self.invocation.mkdir()

    def run_installer(self, *options, expected=0, environment=None):
        result = subprocess.run(
            ["bash", str(self.source / "install.sh"), *options],
            cwd=self.invocation,
            env=environment,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def install(self, target="all", expected=0):
        return self.run_installer(
            "--target", target,
            "--codex-home", str(self.codex_home),
            "--claude-home", str(self.claude_home),
            expected=expected,
        )

    def test_both_platforms_share_the_skill_and_resources(self):
        self.install()
        for relative in ["SKILL.md", "scripts/render_flow.py", "references/flow-model.md", "assets/output-template.md"]:
            expected = (self.source / relative).read_bytes()
            self.assertEqual((self.codex_skill / relative).read_bytes(), expected)
            self.assertEqual((self.claude_skill / relative).read_bytes(), expected)
        self.assertTrue((self.codex_skill / "agents/openai.yaml").is_file())
        self.assertFalse((self.claude_skill / "agents").exists())
        self.assertFalse((self.claude_skill / "tests").exists())
        self.assertFalse((self.claude_skill / "scripts/install_skill.py").exists())

    def test_single_platform_install_preserves_other_configuration(self):
        unrelated = self.claude_home / "skills/another-skill/SKILL.md"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("Existing user skill")
        global_instructions = self.claude_home / "CLAUDE.md"
        global_instructions.write_text("Existing global instructions")
        self.install("claude")
        self.assertTrue((self.claude_skill / "SKILL.md").is_file())
        self.assertFalse(self.codex_home.exists())
        self.assertEqual(unrelated.read_text(), "Existing user skill")
        self.assertEqual(global_instructions.read_text(), "Existing global instructions")

    def test_update_refreshes_content_and_removes_obsolete_skill_files(self):
        self.install()
        stale = self.claude_skill / "references/obsolete.md"
        stale.write_text("Old skill resource")
        entry = self.source / "SKILL.md"
        entry.write_text(entry.read_text() + "\nUpdated shared instruction.\n")
        self.install()
        self.assertFalse(stale.exists())
        self.assertEqual((self.claude_skill / "SKILL.md").read_bytes(), entry.read_bytes())
        self.assertEqual((self.codex_skill / "SKILL.md").read_bytes(), entry.read_bytes())
        for configuration in [self.codex_home, self.claude_home]:
            self.assertFalse(list((configuration / "skills").glob(".interaction-flow-*")))

    def test_environment_roots_are_supported_without_changing_user_home(self):
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(self.codex_home)
        environment["CLAUDE_CONFIG_DIR"] = str(self.claude_home)
        self.run_installer(environment=environment)
        self.assertTrue((self.codex_skill / "SKILL.md").is_file())
        self.assertTrue((self.claude_skill / "SKILL.md").is_file())

    def test_unrelated_destination_is_preserved_before_any_install(self):
        self.claude_skill.mkdir(parents=True)
        sentinel = self.claude_skill / "user-file.txt"
        sentinel.write_text("Must survive")
        self.install(expected=1)
        self.assertEqual(sentinel.read_text(), "Must survive")
        self.assertFalse(self.codex_skill.exists())

    def test_installation_cannot_replace_its_source_project(self):
        source = self.root / "source-root/skills/interaction-flow"
        source.parent.mkdir(parents=True)
        shutil.copytree(self.source, source)
        before = (source / "SKILL.md").read_bytes()
        result = subprocess.run(
            ["bash", str(source / "install.sh"), "--target", "codex", "--codex-home", str(self.root / "source-root")],
            cwd=self.invocation, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual((source / "SKILL.md").read_bytes(), before)
        self.assertTrue((source / "install.sh").is_file())

    def test_installed_renderers_run_from_a_different_project_directory(self):
        self.install()
        reference = (self.source / "references/flow-model.md").read_text()
        model = json.loads(re.search(r"```json\n(.*?)\n```", reference, re.S).group(1))
        model_path = self.invocation / "service flow.json"
        model_path.write_text(json.dumps(model, ensure_ascii=False))
        rendered = []
        for platform, skill in [("codex", self.codex_skill), ("claude", self.claude_skill)]:
            output = self.invocation / f"{platform} flow.svg"
            result = subprocess.run(
                [sys.executable, str(skill / "scripts/render_flow.py"), model_path.name, "-o", output.name],
                cwd=self.invocation, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            document = ElementTree.fromstring(output.read_text())
            self.assertTrue(document.tag.endswith("svg"))
            content = "".join(document.itertext())
            self.assertIn("并行分支", content)
            self.assertIn("order_id", content)
            rendered.append(output.read_bytes())
        self.assertEqual(rendered[0], rendered[1])


if __name__ == "__main__":
    unittest.main()
