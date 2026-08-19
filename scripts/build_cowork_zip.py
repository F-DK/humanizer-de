#!/usr/bin/env python3
"""Baut das Cowork-Skill-Paket nach dist/humanizer-de-cowork.zip.

Claude Cowork nimmt Skills als ZIP mit maximal 200 Dateien entgegen und lehnt
Pakete mit mehr als einer SKILL.md ab. Der Plugin-Router skills/humanizer-de/
bleibt deshalb draussen: Cowork liest ihn sonst als zweiten Skill. Dafuer meldet
doctor.py im Paket einen fehlenden Basis-Skill-Pfad — das ist der bewusste
Tausch, nicht ein defektes Paket.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "humanizer-de-cowork.zip"
PREFIX = "humanizer-de"

# Laufzeit-Set: was der Skill zum Arbeiten braucht, plus die Manifeste, damit
# doctor.py Version und Paket-Sync pruefen kann. tests/, docs/, .github/ und die
# README-Bilder bleiben draussen — sie kosten nur Dateien am 200er-Limit.
FILES = ("SKILL.md", "LICENSE", "NOTICE", "assets/checkliste-ki-tells.md",
         ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
         ".codex-plugin/plugin.json")
GLOBS = ("references/*.md", "references/*.json", "scripts/*.py")


def collect() -> list[Path]:
    paths = [ROOT / name for name in FILES]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        raise SystemExit(f"fehlende Dateien: {[str(p.relative_to(ROOT)) for p in missing]}")
    for pattern in GLOBS:
        paths.extend(sorted(ROOT.glob(pattern)))
    return sorted(set(paths))


def build() -> Path:
    paths = collect()
    if sum(1 for p in paths if p.name == "SKILL.md") != 1:
        raise SystemExit("Paket braucht genau eine SKILL.md — Cowork lehnt zwei ab")
    if len(paths) > 200:
        raise SystemExit(f"{len(paths)} Dateien — Cowork erlaubt hoechstens 200")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in paths:
            zf.write(path, f"{PREFIX}/{path.relative_to(ROOT).as_posix()}")
    return OUT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="nur pruefen, ob das eingecheckte ZIP zum Baum passt")
    args = parser.parse_args(argv)

    if args.check:
        if not OUT.is_file():
            print(f"FEHLT: {OUT.relative_to(ROOT)} — 'make cowork-zip' ausfuehren")
            return 1
        before = OUT.read_bytes()
        backup = OUT.with_suffix(".zip.bak")
        shutil.copyfile(OUT, backup)
        try:
            build()
            # Zeitstempel machen ZIPs nicht byte-identisch; verglichen wird der Inhalt.
            stale = zipfile.ZipFile(backup).namelist() != zipfile.ZipFile(OUT).namelist()
            OUT.write_bytes(before)
        finally:
            backup.unlink(missing_ok=True)
        if stale:
            print("VERALTET: Dateiliste weicht ab — 'make cowork-zip' ausfuehren")
            return 1
        print("aktuell")
        return 0

    out = build()
    print(f"{out.relative_to(ROOT)} — {len(collect())} Dateien, {out.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
