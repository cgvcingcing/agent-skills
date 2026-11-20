"""Exercise the flow renderer in a disposable directory."""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree


PROJECT = Path(__file__).resolve().parent.parent
RENDERER = PROJECT / "scripts/render_flow.py"


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="interaction-flow-render-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def model(self):
        reference = (PROJECT / "references/flow-model.md").read_text(encoding="utf-8")
        return json.loads(re.search(r"```json\n(.*?)\n```", reference, re.S).group(1))

    def test_renderer_writes_svg_from_a_separate_working_directory(self):
        model_path = self.root / "service flow.json"
        model_path.write_text(json.dumps(self.model(), ensure_ascii=False), encoding="utf-8")
        output = self.root / "flow.svg"
        result = subprocess.run(
            [sys.executable, str(RENDERER), model_path.name, "-o", output.name],
            cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        document = ElementTree.fromstring(output.read_text(encoding="utf-8"))
        self.assertTrue(document.tag.endswith("svg"))
        content = "".join(document.itertext())
        self.assertIn("并行分支", content)
        self.assertIn("order_id", content)

    def test_repeated_renders_are_identical(self):
        model_path = self.root / "flow.json"
        model_path.write_text(json.dumps(self.model(), ensure_ascii=False), encoding="utf-8")
        rendered = []
        for name in ("first.svg", "second.svg"):
            output = self.root / name
            result = subprocess.run([sys.executable, str(RENDERER), str(model_path), "-o", str(output)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            rendered.append(output.read_bytes())
        self.assertEqual(rendered[0], rendered[1])


if __name__ == "__main__":
    unittest.main()
