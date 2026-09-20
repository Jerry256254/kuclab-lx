#!/usr/bin/env bash
# Hlasove nastroje agenta: whisper.cpp (STT) + Piper (TTS) vcetne knihoven.
# Obe binarky maji RUNPATH $ORIGIN, takze knihovny musi lezet vedle nich.
# Modely se stahuji az pri prvnim pouziti (viz agent/voice.py).
set -euo pipefail

BIN=/usr/lib/kuclab/bin
WHISPER_URL="${WHISPER_URL:-https://github.com/ggml-org/whisper.cpp/releases/download/b5130/whisper-bin-ubuntu-x64.tar.gz}"
PIPER_URL="${PIPER_URL:-https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$BIN"

echo "Stahuji whisper.cpp ..."
curl -fsSL -o "$TMP/whisper.tgz" "$WHISPER_URL"
tar -xzf "$TMP/whisper.tgz" -C "$TMP"
cp -a "$TMP"/whisper-bin-ubuntu-x64/whisper-cli "$TMP"/whisper-bin-ubuntu-x64/lib*.so* "$BIN"/

echo "Stahuji Piper TTS ..."
curl -fsSL -o "$TMP/piper.tgz" "$PIPER_URL"
tar -xzf "$TMP/piper.tgz" -C "$TMP"
cp -a "$TMP"/piper/. "$BIN"/

echo "Kontrola ..."
"$BIN/whisper-cli" --help >/dev/null
"$BIN/piper" --help >/dev/null
ls "$BIN"
