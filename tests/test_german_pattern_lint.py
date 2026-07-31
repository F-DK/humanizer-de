import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "german_pattern_lint.py"

spec = importlib.util.spec_from_file_location("german_pattern_lint", SCRIPT)
german_pattern_lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(german_pattern_lint)


def kinds(report):
    return {item["kind"] for item in report["findings"]}


def spacy_model_available():
    try:
        import spacy

        spacy.load("de_core_news_sm")
    except Exception:
        return False
    return True


SPACY_MODEL_AVAILABLE = spacy_model_available()


class GermanPatternLintTests(unittest.TestCase):
    def test_ai_marker_cluster(self):
        text = "Der Text beleuchtet das vielschichtige Zusammenspiel in einer dynamischen Landschaft."
        self.assertIn("ai_marker_cluster", kinds(german_pattern_lint.lint(text)))

    def test_single_marker_is_not_cluster(self):
        text = "Die robuste Statistik nutzt ein dynamisches Routing."
        self.assertNotIn("ai_marker_cluster", kinds(german_pattern_lint.lint(text)))

    def test_ai_marker_mentions_in_quotes_are_not_cluster(self):
        text = (
            "Im Review ging es um Wörter wie „Nahtlos“, „beleuchten“ und "
            "„maßgeschneidert“, nicht um ihren Einsatz im Text."
        )
        self.assertNotIn("ai_marker_cluster", kinds(german_pattern_lint.lint(text)))

    def test_ai_marker_cluster_ignores_extra_quote_marker(self):
        text = (
            "Der Text beleuchtet den Prozess, bleibt dynamisch und nutzt ein "
            "vielschichtiges Modell. Im Review fiel auch „nahtlos“."
        )
        report = german_pattern_lint.lint(text)
        finding = next(item for item in report["findings"] if item["kind"] == "ai_marker_cluster")
        self.assertEqual(sum(finding["evidence"].values()), 3)

    def test_ai_marker_mentions_in_markdown_are_not_cluster(self):
        text = "Im Glossar steht *nahtlos* neben `beleuchten` und *maßgeschneidert*."
        self.assertNotIn("ai_marker_cluster", kinds(german_pattern_lint.lint(text)))

    def test_apostrophes_do_not_open_mention_spans(self):
        text = (
            "Das gibt's öfter: Der Text beleuchtet den Prozess, bleibt dynamisch "
            "und wirkt vielschichtig, sagt's Team."
        )
        self.assertIn("ai_marker_cluster", kinds(german_pattern_lint.lint(text)))

    def test_copula_avoidance_cluster(self):
        text = "Die Plattform fungiert als Werkzeug und verfügt über mehrere Module."
        self.assertIn("copula_avoidance_cluster", kinds(german_pattern_lint.lint(text)))

    def test_single_stellt_dar_is_not_double_counted(self):
        text = "Dies stellt dar, was gemeint ist."
        self.assertNotIn("copula_avoidance_cluster", kinds(german_pattern_lint.lint(text)))

    def test_stellt_full_verbs_are_not_copula_avoidance(self):
        text = "Der Bericht stellt eine Frage. Das Team stellt den Plan nächste Woche vor."
        self.assertNotIn("copula_avoidance_cluster", kinds(german_pattern_lint.lint(text)))

    def test_stellt_dar_cluster_counts_separable_forms(self):
        text = "Der Absatz stellt den Ablauf dar. Die Grafik stellt die Rollen dar."
        report = german_pattern_lint.lint(text)
        self.assertIn("copula_avoidance_cluster", kinds(report))
        finding = next(item for item in report["findings"] if item["kind"] == "copula_avoidance_cluster")
        self.assertEqual(finding["evidence"], {"stellt ... dar": 2})

    def test_default_regex_counts_sentence_boundary_stellt_dar(self):
        text = "Dies stellt sicher. Kurz darauf legte er dar, was passiert, und fungiert als Beispiel."
        self.assertIn("copula_avoidance_cluster", kinds(german_pattern_lint.lint(text)))

    def test_negation_parallelism(self):
        text = "Kein Server, keine Datenbank. Kein Dashboard nötig."
        report = german_pattern_lint.lint(text)
        self.assertIn("negation_parallelism", kinds(report))
        self.assertNotIn("negation_antithesis_cluster", kinds(report))

    def test_negation_parallelism_ignores_factual_correction(self):
        text = "Ich will nicht Tee, sondern Kaffee."
        self.assertNotIn("negation_parallelism", kinds(german_pattern_lint.lint(text)))

    def test_negation_parallelism_ignores_single_negation(self):
        text = "Keine Sorge, das passt schon."
        self.assertNotIn("negation_parallelism", kinds(german_pattern_lint.lint(text)))

    def test_negation_parallelism_ignores_quoted_example(self):
        text = "Im Beispiel steht: „Kein Server, keine Datenbank.“"
        self.assertNotIn("negation_parallelism", kinds(german_pattern_lint.lint(text)))

    def test_negation_antithesis_cluster(self):
        text = (
            "Nicht abwarten, sondern machen. Nicht erklären, sondern liefern. "
            "Nicht verwalten, sondern gestalten. Laut und nicht leise lautet die Devise."
        )
        self.assertIn("negation_antithesis_cluster", kinds(german_pattern_lint.lint(text)))

    def test_negation_antithesis_cluster_for_repeated_not_but(self):
        text = (
            "Nicht reden, sondern handeln. Nicht planen, sondern anfangen. "
            "Nicht prüfen, sondern glauben. Nicht zweifeln, sondern folgen."
        )
        self.assertIn("negation_antithesis_cluster", kinds(german_pattern_lint.lint(text)))

    def test_negation_antithesis_cluster_for_repeated_and_not(self):
        text = (
            "Die Ansage ist laut und nicht leise. Der Plan bleibt starr und nicht beweglich. "
            "Die Antwort wirkt glatt und nicht ehrlich. Der Ton ist scharf und nicht sachlich."
        )
        self.assertIn("negation_antithesis_cluster", kinds(german_pattern_lint.lint(text)))

    def test_negation_antithesis_cluster_ignores_single_substantive_contrast(self):
        text = "Die Auswertung bewertet nicht die Person, sondern das Verfahren."
        self.assertNotIn("negation_antithesis_cluster", kinds(german_pattern_lint.lint(text)))

    def test_negation_antithesis_cluster_ignores_factual_corrections(self):
        text = (
            "Der Termin ist nicht Montag, sondern Dienstag. "
            "Die Abgabe ist nicht Mittwoch, sondern Donnerstag. "
            "Das Treffen ist nicht Freitag, sondern Samstag. "
            "Der Prüfmonat ist nicht Januar, sondern Februar."
        )
        self.assertNotIn("negation_antithesis_cluster", kinds(german_pattern_lint.lint(text)))

    def test_negation_antithesis_cluster_ignores_low_document_density(self):
        text = "Wort " * 1400 + (
            "Nicht abwarten, sondern machen. Nicht erklären, sondern liefern. "
            "Nicht verwalten, sondern gestalten. Laut und nicht leise lautet die Devise."
        )
        self.assertNotIn("negation_antithesis_cluster", kinds(german_pattern_lint.lint(text)))

    def test_negation_antithesis_cluster_ignores_use_mentions(self):
        text = (
            "Im Leitfaden stehen „nicht abwarten, sondern machen“ und "
            "`nicht erklären, sondern liefern`. Die Varianten "
            "*nicht verwalten, sondern gestalten* und "
            "_laut und nicht leise_ werden nur zitiert."
        )
        self.assertNotIn("negation_antithesis_cluster", kinds(german_pattern_lint.lint(text)))

    def test_negation_antithesis_cluster_ignores_not_only_correlatives(self):
        text = (
            "Nicht nur Tempo, sondern auch Sorgfalt zählt. "
            "Nicht nur Technik, sondern auch Abstimmung hilft. "
            "Nicht nur Kosten, sondern auch Nutzen werden geprüft. "
            "Nicht nur heute, sondern auch morgen bleibt Zeit."
        )
        self.assertNotIn("negation_antithesis_cluster", kinds(german_pattern_lint.lint(text)))

    def test_bold_overdose(self):
        text = "**Alpha:** eins. **Beta:** zwei. **Gamma:** drei. **Delta:** vier. **Epsilon:** fünf."
        self.assertIn("bold_overdose", kinds(german_pattern_lint.lint(text)))

    def test_bold_overdose_ignores_four_spans(self):
        text = "**Alpha:** eins. **Beta:** zwei. **Gamma:** drei. **Delta:** vier."
        self.assertNotIn("bold_overdose", kinds(german_pattern_lint.lint(text)))

    def test_bold_overdose_ignores_single_span(self):
        text = "Dieser Hinweis ist **wichtig** für die Auswertung."
        self.assertNotIn("bold_overdose", kinds(german_pattern_lint.lint(text)))

    def test_colon_heading_spans_keep_splitlines_semantics(self):
        text = "  # Eins: Inhalt  \u2028## Zwei: Inhalt"
        report = german_pattern_lint.lint(text)
        finding = next(item for item in report["findings"] if item["kind"] == "colon_heading_cluster")

        self.assertEqual(
            [text[span["start"]:span["end"]] for span in finding["spans"]],
            ["# Eins: Inhalt", "## Zwei: Inhalt"],
        )

    def test_address_validation_candidate_is_info_advisory(self):
        report = german_pattern_lint.lint("Du bist nicht zu sensibel.")
        finding = next(
            item for item in report["findings"] if item["kind"] == "address_validation_candidate"
        )

        self.assertEqual(finding["pattern"], 72)
        self.assertEqual(finding["severity"], "info")
        self.assertTrue(finding["advisory"])
        self.assertEqual(
            finding["message"],
            "Kandidat für unbelegte Adressaten-Validierung: Kontext prüfen "
            "(Beratungsauftrag? Zitat? Sachklärung?)",
        )

    def test_address_validation_candidate_ignores_quoted_use_mention(self):
        text = 'Der Satz „Du bist nicht zu sensibel“ ist hier nur ein Beispiel.'
        self.assertNotIn("address_validation_candidate", kinds(german_pattern_lint.lint(text)))


@unittest.skipUnless(SPACY_MODEL_AVAILABLE, "spaCy German model is not available")
class GermanPatternLintPreciseTests(unittest.TestCase):
    def test_precise_ignores_sentence_boundary_stellt_dar(self):
        text = "Dies stellt sicher. Kurz darauf legte er dar, was passiert, und fungiert als Beispiel."
        report = german_pattern_lint.lint(text, precise=True)

        self.assertNotIn("copula_avoidance_cluster", kinds(report))

    def test_precise_keeps_real_stellt_dar_cluster(self):
        text = "Dies stellt einen Fortschritt dar und fungiert als Beispiel."
        report = german_pattern_lint.lint(text, precise=True)

        self.assertIn("copula_avoidance_cluster", kinds(report))


if __name__ == "__main__":
    unittest.main()
