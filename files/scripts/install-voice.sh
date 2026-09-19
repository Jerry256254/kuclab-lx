#!/usr/bin/env bash
# Hlasove nastroje agenta: whisper.cpp (STT) + Piper (TTS).
# Binarky do /usr/lib/kuclab/bin, modely se stahuji az pri prvnim pouziti.
set -euo pipefail

BIN=/usr/lib/kuclab/bin
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$BIN"

echo "Stahuji whisper.cpp ..."
WHISPER_URL="https://github.com/ggml-org/whisper.cpp/releases/latest/download/whisper-cpp-ubuntu-22.04-x64.zip"
curl -fsSL -o "$TMP/whisper.zip" "$WHISPER_URL" || {
  echo "Varovani: whisper.cpp se nepodarilo stahnout, agent pouzije textovy rezim."
  WHISPER_URL=""
}
if [ -n "${WHISPER_URL}" ] && [ -f "$TMP/whisper.zip" ]; then
  python3 -c "import zipfile,sys; zipfile.ZipFile('$TMP/whisper.zip').extractall('$TMP/whisper')"
  find "$TMP/whisper" -name 'whisper-cli' -exec install -m 0755 {} "$BIN/whisper-cli" \;
fi

echo "Stahuji Piper TTS ..."
PIPER_VER="${PIPER_VERSION:-v1.2.0}"
PIPER_URL="https://github.com/rhasspy/piper/releases/download/${PIPER_VER}/piper_linux_x86_64.tar.gz"
curl -fsSL -o "$TMP/piper.tar.gz" "$PIPER_URL" || {
  echo "Varovani: Piper se nepodarilo stahnout, agent pouzije textovy rezim."
  PIPER_URL=""
}
if [ -f "$TMP/piper.tar.gz" ]; then
  tar -xzf "$TMP/piper.tar.gz" -C "$TMP"
  install -m 0755 "$TMP/piper/piper" "$BIN/piper"
fi

ls -la "$BIN" || true
