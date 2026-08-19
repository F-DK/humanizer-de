import re
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "dist" / "humanizer-de-cowork.zip"
VERSION_RE = re.compile(r"(?m)^\s{2}version:\s*['\"]?([^'\"\s]+)")


def skill_version(text: str) -> str | None:
    match = VERSION_RE.search(text)
    return match.group(1) if match else None


class CoworkZipTests(unittest.TestCase):
    """Das ZIP ist ausgeliefert, nicht generiert: Nutzer laden es direkt von
    GitHub. Es darf deshalb nicht hinter den Baum zurueckfallen."""

    @classmethod
    def setUpClass(cls):
        if not ZIP_PATH.is_file():
            raise unittest.SkipTest("dist/humanizer-de-cowork.zip fehlt — 'make cowork-zip'")
        cls.names = zipfile.ZipFile(ZIP_PATH).namelist()

    def test_zip_has_exactly_one_skill_md(self):
        # Cowork lehnt Pakete mit zwei SKILL.md ab (Plugin-Router bleibt draussen).
        skills = [n for n in self.names if n.endswith("SKILL.md")]
        self.assertEqual(skills, ["humanizer-de/SKILL.md"], f"unerwartete SKILL.md: {skills}")

    def test_zip_stays_under_cowork_file_limit(self):
        files = [n for n in self.names if not n.endswith("/")]
        self.assertLessEqual(len(files), 200, "Cowork erlaubt hoechstens 200 Dateien")

    def test_zip_version_matches_tree(self):
        # Faengt den Hauptfall von Drift: Release gebumpt, ZIP nicht neu gebaut.
        # Verglichen wird gegen den Baum, nicht gegen eine gepinnte Konstante —
        # eine Konstante wandert beim Bump mit und laesst genau diesen Fall durch.
        with zipfile.ZipFile(ZIP_PATH) as zf:
            zipped = skill_version(zf.read("humanizer-de/SKILL.md").decode("utf-8"))
        tree = skill_version((ROOT / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIsNotNone(zipped, "SKILL.md im ZIP hat keine Version")
        self.assertEqual(
            zipped,
            tree,
            "ZIP ist veraltet — 'make cowork-zip' ausfuehren und neu committen",
        )

    def test_zip_carries_every_reference_and_script(self):
        for path in sorted(ROOT.glob("references/*.md")) + sorted(ROOT.glob("scripts/*.py")):
            name = f"humanizer-de/{path.relative_to(ROOT).as_posix()}"
            self.assertIn(name, self.names, f"{name} fehlt im ZIP — 'make cowork-zip'")

    def test_zip_excludes_build_junk(self):
        for name in self.names:
            self.assertNotIn("__pycache__", name)
            self.assertNotIn(".DS_Store", name)


if __name__ == "__main__":
    unittest.main()
