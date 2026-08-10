import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDLER = ROOT / "hooks" / "ad_boilerplate_hook.py"
WRAPPER = ROOT / "hooks" / "run_ad_boilerplate_hook.sh"

AD_TEXT = """# Warum RechnungsHeld die richtige Wahl fuer Ihren Betrieb ist

Ueber 3.400 Handwerksbetriebe in Deutschland vertrauen bereits auf RechnungsHeld. Die App erstellt Rechnungen, verwaltet Zahlungseingaenge und erinnert an offene Forderungen. Seit September 2023 wurden mehr als 210.000 Rechnungen mit einem Gesamtvolumen von 68 Millionen Euro erstellt. Die Server stehen in Frankfurt. Das Produkt ist nach ISO 27001 zertifiziert und kostet monatlich 19 Euro. Betriebe koennen Projekte, Kunden und Leistungen in einer gemeinsamen Ansicht verwalten. Vorlagen lassen sich an das eigene Erscheinungsbild anpassen. Exporte stehen als PDF und CSV bereit.

Registrieren Sie sich noch heute und testen Sie RechnungsHeld kostenlos.
"""

FACTUAL_TEXT = """Der Bericht beschreibt die Ergebnisse einer internen Auswertung. Im ersten Abschnitt stehen Methode und Stichprobe. Danach folgen die beobachteten Werte fuer Januar, Februar und Maerz. Die Tabelle trennt Einnahmen, Ausgaben und offene Posten. Alle Zahlen stammen aus dem Buchhaltungssystem. Vier Personen haben die Daten unabhaengig geprueft. Abweichungen wurden dokumentiert und anschliessend geklaert. Der Anhang nennt die verwendeten Definitionen. Eine zweite Auswertung ist fuer das kommende Quartal geplant. Bis dahin bleiben die aktuellen Werte als vorlaeufig gekennzeichnet. Der Text enthaelt keine Empfehlung fuer ein bestimmtes Produkt oder einen Anbieter.
"""


class AdBoilerplateHookTests(unittest.TestCase):
    def run_hook(self, payload, *, env=None):
        process_env = os.environ.copy()
        process_env["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
        if env:
            process_env.update(env)
        stdin = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.run(
            [sys.executable, str(HANDLER)],
            input=stdin,
            cwd=ROOT,
            env=process_env,
            capture_output=True,
            text=True,
        )

    def payload(self, tool_name, file_path="entwurf.md", **tool_input):
        return {
            "tool_name": tool_name,
            "tool_input": {"file_path": file_path, **tool_input},
        }

    def assert_silent(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(proc.stderr, "")

    def test_write_with_ad_copy_adds_context(self):
        proc = self.run_hook(self.payload("Write", content=AD_TEXT))

        self.assertEqual(proc.returncode, 0, proc.stderr)
        output = json.loads(proc.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(output["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertTrue(context.startswith("[humanizer-de: Werbeschablonen-Check]"))
        self.assertIn("Sozialbeweis", context)
        self.assertIn("Standard-Werbeabschnitt", context)
        self.assertIn("Zahlen, Normen, Zertifikate, Preise", context)

    def test_write_with_factual_text_is_silent(self):
        self.assert_silent(self.run_hook(self.payload("Write", content=FACTUAL_TEXT)))

    def test_edit_checks_new_string(self):
        proc = self.run_hook(self.payload("Edit", new_string=AD_TEXT))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("hookSpecificOutput", json.loads(proc.stdout))

    def test_multiedit_checks_combined_new_strings(self):
        split = len(AD_TEXT) // 2
        proc = self.run_hook(
            self.payload(
                "MultiEdit",
                edits=[
                    {"old_string": "alt", "new_string": AD_TEXT[:split]},
                    {"old_string": "alt2", "new_string": AD_TEXT[split:]},
                ],
            )
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("hookSpecificOutput", json.loads(proc.stdout))

    def test_python_file_is_silent(self):
        self.assert_silent(
            self.run_hook(self.payload("Write", file_path="generator.py", content=AD_TEXT))
        )

    def test_short_text_is_silent(self):
        text = "3.400 zufriedene Kunden. Registrieren Sie sich noch heute."
        self.assert_silent(self.run_hook(self.payload("Write", content=text)))

    def test_broken_json_is_silent_and_fail_open(self):
        self.assert_silent(self.run_hook("{kaputt"))

    def test_environment_switch_disables_hook(self):
        self.assert_silent(
            self.run_hook(
                self.payload("Write", content=AD_TEXT),
                env={"HUMANIZER_AD_HOOK": "off"},
            )
        )

    def test_context_is_capped_and_reports_omitted_findings(self):
        headings = "\n".join(
            f"# Warum Produkt{i} die richtige Wahl fuer Ihren Betrieb ist" for i in range(80)
        )
        proc = self.run_hook(self.payload("Write", content=headings))

        self.assertEqual(proc.returncode, 0, proc.stderr)
        context = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertLessEqual(len(context), 2000)
        self.assertRegex(context, r"… und \d+ weitere")

    def test_wrapper_is_silent_without_python(self):
        env = os.environ.copy()
        env.update({"PATH": "", "CLAUDE_PLUGIN_ROOT": str(ROOT)})
        proc = subprocess.run(
            ["/bin/bash", str(WRAPPER)],
            input="{}",
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assert_silent(proc)


if __name__ == "__main__":
    unittest.main()
