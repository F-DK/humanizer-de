#!/usr/bin/env python3
"""Report register and profile drift in German text passages."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
import importlib.util
import json
import re
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import evidence_lint
import text_scope
from cli_output import print_json, resolve_exit_code


SYNTAX_SCRIPT = SCRIPT_DIR / "syntax_lint.py"
_SYNTAX_LINT = None

MODAL_PARTICLES = {"ja", "doch", "eben", "halt", "wohl", "mal", "schon", "ohnehin"}
DU_FORMS = ("du", "dir", "dich", "dein", "deine", "deinen", "deinem", "deiner", "deines")
SIE_FORMS = ("Sie", "Ihnen", "Ihr", "Ihre", "Ihren", "Ihrem", "Ihrer", "Ihres")
WIR_FORMS = ("wir", "uns", "unser", "unsere", "unseren", "unserem", "unserer", "unseres")
SIE_FORMS_RE = re.compile(rf"\b(?:{'|'.join(re.escape(form) for form in SIE_FORMS)})\b")
EMOJI_RE = re.compile("[\u2600-\u27BF\U0001F300-\U0001FAFF]")


def load_syntax_lint():
    global _SYNTAX_LINT
    if _SYNTAX_LINT is not None:
        return _SYNTAX_LINT

    module = sys.modules.get("syntax_lint")
    if module is None:
        spec = importlib.util.spec_from_file_location("syntax_lint", SYNTAX_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        sys.modules["syntax_lint"] = module
        spec.loader.exec_module(module)

    _SYNTAX_LINT = module
    return module


def precise_context(precise: bool) -> tuple[dict | None, object | None]:
    if not precise:
        return None, None

    syntax_lint = load_syntax_lint()
    if not hasattr(syntax_lint, "_HUMANIZER_PRECISE_CACHE"):
        syntax_lint._HUMANIZER_PRECISE_CACHE = syntax_lint.load_nlp()

    nlp, reason = syntax_lint._HUMANIZER_PRECISE_CACHE
    if nlp is None:
        return {"requested": True, "active": False, "reason": reason or "spacy_missing"}, None
    return {"requested": True, "active": True}, nlp


def strip_protected(text: str, exclude_blockquotes: bool = False) -> str:
    scope = text_scope.AUTHORED_PROSE if exclude_blockquotes else text_scope.DOCUMENT_PROSE
    clean_text = text_scope.mask_text(text, scope=scope)
    if not exclude_blockquotes:
        return clean_text

    def mask_quote(match: re.Match) -> str:
        return "".join(char if char in {"\n", "\r"} else " " for char in match.group())

    for pattern in evidence_lint.VALID_QUOTE_PATTERNS:
        clean_text = pattern.sub(mask_quote, clean_text)
    return clean_text


def blockquote_ranges(text: str) -> list[tuple[int, int]]:
    return text_scope.blockquote_ranges(text)


def is_in_ranges(start: int, end: int, ranges: Iterable[tuple[int, int]]) -> bool:
    return any(start < range_end and end > range_start for range_start, range_end in ranges)


def count_words(text: str, words: Iterable[str]) -> int:
    return len(word_spans(text, words))


def word_spans(text: str, words: Iterable[str]) -> list[tuple[int, int]]:
    return sorted(
        match.span()
        for word in words
        for match in re.finditer(rf"\b{re.escape(word)}\b", text, re.IGNORECASE)
    )


def is_sentence_initial_sie(text: str, start: int) -> bool:
    prefix = text[:start]
    return not prefix.strip() or re.search(r"[.!?:]\s+$", prefix) is not None


def has_morph(token: object, key: str, value: str) -> bool:
    return value in token.morph.get(key)


def token_for_match(doc: object, start: int, end: int):
    for token in doc:
        if token.idx == start and token.idx + len(token.text) == end:
            return token
    return None


def previous_sentence(doc: object, token: object):
    sentences = list(doc.sents)
    for index, sent in enumerate(sentences):
        if sent.start <= token.i < sent.end:
            return sentences[index - 1] if index > 0 else None
    return None


def contains_du_form(text: str) -> bool:
    return count_words(text, DU_FORMS) > 0


def contains_imperative(sent: object) -> bool:
    return any("Imp" in token.morph.get("Mood") or token.tag_ == "VVIMP" for token in sent)


def previous_sentence_allows_anaphora(doc: object, token: object) -> bool:
    sent = previous_sentence(doc, token)
    if sent is None:
        return True
    return not contains_imperative(sent) and not contains_du_form(sent.text)


def is_anaphoric_sie(match: re.Match, text: str, doc: object) -> bool:
    if match.group(0) != "Sie":
        return False
    if not is_sentence_initial_sie(text, match.start()):
        return False

    token = token_for_match(doc, match.start(), match.end())
    if token is None:
        return False
    return (
        token.text == "Sie"
        and has_morph(token, "Person", "3")
        and has_morph(token, "Case", "Nom")
        and has_morph(token, "Number", "Sing")
        and previous_sentence_allows_anaphora(doc, token)
    )


def sie_formal_spans(text: str, nlp: object | None = None) -> list[tuple[int, int]]:
    blockquotes = blockquote_ranges(text) if nlp is not None else []
    doc = nlp(text) if nlp is not None else None
    spans: list[tuple[int, int]] = []
    for match in SIE_FORMS_RE.finditer(text):
        if is_in_ranges(match.start(), match.end(), blockquotes):
            continue
        if doc is not None and is_anaphoric_sie(match, text, doc):
            continue
        spans.append(match.span())
    return spans


def sie_formal_count(text: str, nlp: object | None = None) -> int:
    return len(sie_formal_spans(text, nlp=nlp))


def features(text: str, nlp: object | None = None, exclude_blockquotes: bool | None = None) -> dict:
    if exclude_blockquotes is None:
        exclude_blockquotes = nlp is not None
    clean_text = strip_protected(text, exclude_blockquotes=exclude_blockquotes)
    return {
        "du_count": count_words(clean_text, DU_FORMS),
        "sie_formal_count": sie_formal_count(clean_text, nlp=nlp),
        "wir_count": count_words(clean_text, WIR_FORMS),
        "man_count": count_words(clean_text, {"man"}),
        "modal_particle_count": count_words(clean_text, MODAL_PARTICLES),
        "emoji_count": len(EMOJI_RE.findall(clean_text)),
        "rhetorical_questions": len(re.findall(r"\?\s*(?:$|\n|[A-ZÄÖÜ])", clean_text)),
    }


def add(
    findings: list[dict],
    severity: str,
    kind: str,
    message: str,
    spans: list[tuple[int, int]] | None = None,
) -> None:
    item = {"severity": severity, "kind": kind, "message": message}
    serialized = text_scope.serialize_spans(spans or [])
    if serialized:
        item["spans"] = serialized
    findings.append(item)


def lint(text: str, mode: str = "sachlich", expected_address: str | None = None, precise: bool = False) -> dict:
    status, nlp = precise_context(precise)
    clean_text = strip_protected(text, exclude_blockquotes=nlp is not None)
    spans = {
        "du": word_spans(clean_text, DU_FORMS),
        "sie": sie_formal_spans(clean_text, nlp=nlp),
        "wir": word_spans(clean_text, WIR_FORMS),
        "particles": word_spans(clean_text, MODAL_PARTICLES),
        "emoji": [match.span() for match in EMOJI_RE.finditer(clean_text)],
        "questions": [
            (match.start(), match.start() + 1)
            for match in re.finditer(r"\?\s*(?:$|\n|[A-ZÄÖÜ])", clean_text)
        ],
    }
    found = {
        "du_count": len(spans["du"]),
        "sie_formal_count": len(spans["sie"]),
        "wir_count": len(spans["wir"]),
        "man_count": count_words(clean_text, {"man"}),
        "modal_particle_count": len(spans["particles"]),
        "emoji_count": len(spans["emoji"]),
        "rhetorical_questions": len(spans["questions"]),
    }
    findings: list[dict] = []

    if found["du_count"] and found["sie_formal_count"]:
        add(
            findings,
            "warning",
            "mixed_address",
            "Possible Du/Sie address mix; verify that capitalized forms are direct address, not anaphora or quoted voice.",
            spans["du"] + spans["sie"],
        )
    if expected_address == "du" and found["sie_formal_count"]:
        add(findings, "blocker", "unexpected_sie", "Profile expects du-address, but formal Sie appears.", spans["sie"])
    if expected_address == "sie" and found["du_count"]:
        add(findings, "blocker", "unexpected_du", "Profile expects Sie-address, but du-address appears.", spans["du"])
    if expected_address == "wir" and (found["du_count"] or found["sie_formal_count"]):
        add(
            findings,
            "blocker",
            "unexpected_direct_address",
            "Profile expects wir-address, but du/Sie-address appears.",
            spans["du"] + spans["sie"],
        )
    if expected_address == "neutral" and (found["du_count"] or found["sie_formal_count"] or found["wir_count"]):
        add(
            findings,
            "blocker",
            "unexpected_direct_address",
            "Profile expects neutral address, but direct address appears.",
            spans["du"] + spans["sie"] + spans["wir"],
        )
    if mode in {"sachlich", "formal"} and found["modal_particle_count"]:
        add(
            findings,
            "warning",
            "particles_outside_locker",
            "Modal particles should not be added in Sachlich/Formal.",
            spans["particles"],
        )
    if mode == "formal" and (found["emoji_count"] or found["rhetorical_questions"]):
        add(
            findings,
            "blocker",
            "formal_voice_intrusion",
            "Formal mode should not add emojis or rhetorical engagement.",
            spans["emoji"] + spans["questions"],
        )
    if mode == "locker" and found["modal_particle_count"] > 3:
        add(
            findings,
            "warning",
            "particle_overdose",
            "Locker mode uses too many modal particles.",
            spans["particles"],
        )

    report = {"ok": not findings, "mode": mode, "expected_address": expected_address, "features": found, "findings": findings}
    if status is not None:
        report["precise"] = status
    return report


def check_fixture(path: Path, precise: bool = False) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    report = lint(
        data["text"],
        mode=data.get("mode", "sachlich"),
        expected_address=data.get("expected_address"),
        precise=precise,
    )
    expected = set(data.get("expect_kinds", []))
    actual = {item["kind"] for item in report["findings"]}
    return {"fixture": str(path), "ok": actual == expected, "report": report}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report German register/profile drift.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--file", type=Path)
    source.add_argument("--fixture", type=Path)
    parser.add_argument("--mode", choices=["locker", "sachlich", "formal"], default="sachlich")
    parser.add_argument("--expected-address", choices=["du", "sie", "wir", "neutral"])
    parser.add_argument("--precise", action="store_true", help="spaCy-gestützte Verfeinerung, wenn installiert; sonst wirkungslos")
    parser.add_argument("--fail-on", choices=["never", "blocker", "any"], default="blocker")
    args = parser.parse_args(argv)
    if args.fixture:
        if not args.fixture.exists():
            parser.error(f"fixture path does not exist: {args.fixture}")
        if args.fixture.is_dir() and not any(args.fixture.glob("*.json")):
            parser.error(f"fixture directory contains no JSON files: {args.fixture}")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.fixture:
        files = sorted(args.fixture.glob("*.json")) if args.fixture.is_dir() else [args.fixture]
        results = [check_fixture(file_path, precise=args.precise) for file_path in files]
        print_json({"ok": all(item["ok"] for item in results), "results": results})
        return 0 if all(item["ok"] for item in results) else 1

    text = args.file.read_text(encoding="utf-8") if args.file else args.text or ""
    report = lint(text, mode=args.mode, expected_address=args.expected_address, precise=args.precise)
    print_json(report)
    return resolve_exit_code(args.fail_on, report["findings"])


if __name__ == "__main__":
    raise SystemExit(main())
