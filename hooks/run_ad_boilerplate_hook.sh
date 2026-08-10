#!/usr/bin/env bash

if [[ "${HUMANIZER_AD_HOOK:-}" == "off" ]]; then
  exit 0
fi
if command -v python3 >/dev/null 2>&1 && [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
  python3 "${CLAUDE_PLUGIN_ROOT}/hooks/ad_boilerplate_hook.py" 2>/dev/null || true
fi
exit 0
