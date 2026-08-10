#!/usr/bin/env python3
"""Fail-open PostToolUse context for the ad-boilerplate detector."""

from __future__ import annotations

import json
import os
import re
import signal
import sys
from pathlib import Path


PROVENANCE_TAG = "[humanizer-de: Werbeschablonen-Check]"
MAX_CONTEXT_CHARS = 2000
MIN_WORDS = 80
TIMEOUT_SECONDS = 1
ALLOWED_SUFFIXES = {".md", ".markdown", ".txt"}
CLASS_LABELS = {
    "social_proof": "Sozialbeweis",
    "ad_section": "Standard-Werbeabschnitt",
    "cta_stack": "Handlungsaufforderung",
}
WORD_RE = re.compile(r"[^\W_]+(?:[-'][^\W_]+)?")


def timeout(_signum, _frame) -> None:
    raise TimeoutError


def tool_text(payload: dict) -> str | None:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    tool_name = payload.get("tool_name")
    if tool_name == "Write":
        value = tool_input.get("content")
        return value if isinstance(value, str) else None
    if tool_name == "Edit":
        value = tool_input.get("new_string")
        return value if isinstance(value, str) else None
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits")
        if not isinstance(edits, list):
            return None
        values = [edit.get("new_string") for edit in edits if isinstance(edit, dict)]
        return "\n".join(value for value in values if isinstance(value, str))
    return None


def detect(text: str) -> dict | None:
    scripts = Path(os.environ["CLAUDE_PLUGIN_ROOT"]) / "scripts"
    sys.path.insert(0, str(scripts))
    import german_pattern_lint

    return next(
        (
            item
            for item in german_pattern_lint.lint(text)["findings"]
            if item.get("kind") == "ad_boilerplate_cluster"
        ),
        None,
    )


def context_for(text: str, finding: dict) -> str:
    evidence = finding.get("evidence", {})
    classes = [
        (class_name, matches)
        for class_name, matches in evidence.items()
        if isinstance(matches, list)
    ] if isinstance(evidence, dict) else []
    total = sum(len(matches) for _, matches in classes)
    class_summary = ", ".join(CLASS_LABELS.get(name, name) for name, _ in classes)

    prefix = (
        PROVENANCE_TAG
        + f"\n\nWerbeschablonen erkannt ({class_summary}). "
        "Prüfe bei der laufenden Überarbeitung diese Fundstellen:\n"
    )
    guidance = (
        "\n\nNur die Schablone fällt. Der prüfbare Kern (Zahlen, Normen, Zertifikate, Preise) "
        "bleibt erhalten. Eine mehrgliedrige Werbefigur bleibt nur stehen, wenn mindestens "
        "eines ihrer Glieder eine nachprüfbar falsche Aussage machen könnte."
    )
    kept = []
    full = False
    for class_name, matches in classes:
        for match in matches:
            if not isinstance(match, str):
                continue
            start = text.find(match)
            line = text.count("\n", 0, start) + 1 if start >= 0 else "?"
            label = CLASS_LABELS.get(class_name, class_name)
            item = f"- {label}, Zeile {line}: {match!r}"
            omitted = total - len(kept) - 1
            suffix = f"\n- … und {omitted} weitere" if omitted else ""
            candidate = prefix + "\n".join([*kept, item]) + suffix + guidance
            if len(candidate) > MAX_CONTEXT_CHARS:
                full = True
                break
            kept.append(item)
        if full:
            break

    omitted = total - len(kept)
    suffix = f"\n- … und {omitted} weitere" if omitted else ""
    return (prefix + "\n".join(kept) + suffix + guidance)[:MAX_CONTEXT_CHARS]


def hook_output() -> dict | None:
    payload = json.loads(sys.stdin.read())
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or Path(file_path).suffix.lower() not in ALLOWED_SUFFIXES:
        return
    text = tool_text(payload)
    if text is None or len(WORD_RE.findall(text)) < MIN_WORDS:
        return
    finding = detect(text)
    if finding is None:
        return
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context_for(text, finding),
        }
    }


def main() -> None:
    if os.environ.get("HUMANIZER_AD_HOOK", "").strip().lower() == "off":
        return
    armed = hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer")
    previous_handler = None
    if armed:
        previous_handler = signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, TIMEOUT_SECONDS)
    try:
        output = hook_output()
    finally:
        if armed:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
    if output is not None:
        print(json.dumps(output))


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        pass
