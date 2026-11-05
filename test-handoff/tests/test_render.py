import contextlib
import importlib.util
import io
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


renderer = module("renderer", "scripts/render_form.py")
installer = module("installer", "install.py")


class RenderTests(unittest.TestCase):
    def test_finalization_preserves_answers_and_removes_form_controls(self):
        original = renderer.normalize({"meta": {"developer": "Existing owner"},
            "tables": {"scope": [{"_id": "scope-1", "handoff": "Exact answer\nSELECT ';' AS value;", "priority": "含 P0"}]},
            "sections": {"scope": {"status": "已确认", "note": "Code reviewed; testing still pending"}},
            "_presentation": {"badge": "Developer filled", "sources": [{"name": "source.md", "note": "§3"}]}})
        tags = []
        parser = HTMLParser()
        parser.handle_starttag = lambda tag, attrs: tags.append((tag, dict(attrs)))
        output = renderer.render(original, read_only=True)
        parser.feed(output)
        self.assertFalse(any(tag in {"input", "textarea", "select"} or "contenteditable" in attrs for tag, attrs in tags))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "final.html"
            path.write_text(output, encoding="utf-8")
            self.assertEqual(renderer.extract(path), original)

    def test_updating_a_finalized_html_keeps_it_readonly(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp) / "final.html", Path(temp) / "updated.html"
            original = renderer.normalize({"tables": {"scope": [{"handoff": "Confirmed answer"}]}})
            source.write_text(renderer.render(original, read_only=True), encoding="utf-8")
            with patch("sys.argv", ["render_form.py", "--from-html", str(source), "-o", str(target)]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(renderer.main(), 0)
            tags = []
            parser = HTMLParser()
            parser.handle_starttag = lambda tag, attrs: tags.append((tag, dict(attrs)))
            parser.feed(target.read_text(encoding="utf-8"))
            self.assertTrue(any(tag == "html" and attrs.get("data-read-only") == "true" for tag, attrs in tags))
            self.assertEqual(renderer.extract(target), original)

    def test_unknown_facts_remain_blank_and_priorities_pending(self):
        data = renderer.normalize({"tables": {"scope": [{}], "database": [{}]}})
        self.assertEqual(data["tables"]["scope"][0]["priority"], "待确认")
        self.assertEqual(data["tables"]["database"][0]["storage"], "")
        self.assertTrue(all(s["status"] == "待补充" for s in data["sections"].values()))

    def test_legacy_data_and_filled_answers_survive_upgrade(self):
        original = renderer.normalize({"meta": {"developer": "Existing owner"},
            "tables": {"scope": [{"range": "Checkout", "handoff": "Prepared data", "decision": "本次必测"}]}})
        original["tables"]["scope"][0].pop("priority")
        original["tables"]["scope"][0].pop("priorityNote")
        migrated = renderer.normalize(original)
        self.assertEqual(migrated["documentId"], original["documentId"])
        self.assertEqual(migrated["meta"]["developer"], "Existing owner")
        self.assertEqual(migrated["tables"]["scope"][0]["handoff"], "Prepared data")
        self.assertEqual(migrated["tables"]["scope"][0]["decision"], "本次必测")

    def test_html_roundtrip_preserves_plain_text_and_metadata(self):
        text = '</script><img src=x onerror="alert(1)"> & 中文'
        data = renderer.normalize({"meta": {"requirement": text}, "tables": {"scope": [{"scenarios": text}]},
            "_presentation": {"sources": [{"name": "spec.md", "note": "§3"}]}})
        output = renderer.render(data)
        self.assertNotIn(text, output)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "form.html"
            path.write_text(output)
            self.assertEqual(renderer.extract(path), data)

    def test_invalid_selections_and_row_counts_rejected(self):
        for raw in ({"tables": {"scope": [{"priority": "P9"}]}}, {"tables": {"logs": [{}] * 501}}):
            with self.assertRaises(ValueError):
                renderer.normalize(raw)

    def test_answer_migration_isolates_drafts_without_changing_answers(self):
        original = renderer.normalize({"meta": {"developer": "Existing owner"},
            "tables": {"scope": [{"_id": "scope-1", "handoff": "Exact developer answer", "priority": "含 P0"}]},
            "sections": {"scope": {"status": "已确认", "note": "Code reviewed; testing still pending"}}})
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "form.html"
            path.write_text(renderer.render(original, fresh_draft=True))
            migrated = renderer.extract(path)
            self.assertNotEqual(migrated["documentId"], original["documentId"])
            migrated["documentId"] = original["documentId"]
            self.assertEqual(migrated, original)
            path.write_text(renderer.render(original))
            self.assertEqual(renderer.extract(path), original)

    def test_duplicate_row_ids_do_not_break_row_actions(self):
        data = renderer.normalize({"tables": {"scope": [{"_id": "same"}, {"_id": "same"}]}})
        self.assertEqual(len(set(row["_id"] for row in data["tables"]["scope"])), 2)


class InstallTests(unittest.TestCase):
    def test_repeat_install_copy_and_uninstall(self):
        with tempfile.TemporaryDirectory() as temp:
            targets = {name: Path(temp) / name / "test-handoff" for name in ("claude", "codex")}
            with patch.object(installer, "destinations", return_value=targets), patch("sys.argv", ["install.py"]), contextlib.redirect_stdout(io.StringIO()):
                installer.main()
                installer.main()
            for target in targets.values():
                self.assertTrue(installer.managed(target))
                self.assertEqual((target / "assets/form.js").read_bytes(), (ROOT / "assets/form.js").read_bytes())
                self.assertTrue((target / "scripts/render_form.py").is_file())
            with patch.object(installer, "destinations", return_value=targets), patch("sys.argv", ["install.py", "--uninstall"]), contextlib.redirect_stdout(io.StringIO()):
                installer.main()
            self.assertTrue(all(not target.exists() for target in targets.values()))

    def test_unmanaged_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "test-handoff"
            target.mkdir()
            sentinel = target / "personal.txt"
            sentinel.write_text("Keep this")
            with patch.object(installer, "destinations", return_value={"codex": target}), patch("sys.argv", ["install.py"]), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    installer.main()
            self.assertEqual(sentinel.read_text(), "Keep this")


if __name__ == "__main__":
    unittest.main()
