#!/usr/bin/env bash

# Opt-in: Ohne HUMANIZER_AD_HOOK=on liest der Hook keinen Nutzertext.
# Normalisierung wie im Python-Handler: Rand-Leerzeichen weg, Gross-/Kleinschreibung egal.
# Bewusst ohne externe Programme, damit der Hook auch bei leerem PATH still bleibt.
switch="${HUMANIZER_AD_HOOK:-}"
switch="${switch#"${switch%%[![:space:]]*}"}"
switch="${switch%"${switch##*[![:space:]]}"}"
shopt -s nocasematch 2>/dev/null || true
case "$switch" in
  on|1|true|yes|ja) ;;
  *) exit 0 ;;
esac
shopt -u nocasematch 2>/dev/null || true
if command -v python3 >/dev/null 2>&1 && [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
  python3 "${CLAUDE_PLUGIN_ROOT}/hooks/ad_boilerplate_hook.py" 2>/dev/null || true
fi
exit 0
