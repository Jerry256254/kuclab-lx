#!/usr/bin/env bash
# Finalni prava a kontrola KucLab vrstvy.
set -euo pipefail

chmod 0755 /usr/bin/kuclab-agent /usr/bin/kuclab-store /usr/bin/kuclab-manager /usr/bin/winshit 2>/dev/null || true
chmod 0755 /usr/lib/kuclab/firstboot.sh 2>/dev/null || true
chmod 0755 /usr/lib/kuclab/bin/* 2>/dev/null || true
glib-compile-schemas /usr/share/gnome-shell/extensions/kuclab-agent@kuclab.lx/schemas/ 2>/dev/null || true

for app in org.kuclab.AgentChat org.kuclab.Store org.kuclab.Manager org.kuclab.WinShit; do
  [ -f "/usr/share/applications/${app}.desktop" ] || { echo "CHYBI ${app}.desktop"; exit 1; }
done
[ -f /usr/share/gnome-shell/extensions/kuclab-agent@kuclab.lx/metadata.json ] || { echo "CHYBI rozsireni agenta"; exit 1; }
echo "KucLab vrstva OK"
