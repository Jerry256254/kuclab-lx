#!/usr/bin/env bash
# Nainstaluje Ollama server do /usr/bin (bez /usr/local, kvuli ostree).
# Asset se jmenuje .tar.zst (drive .tgz) a obsahuje bin/ollama.
set -euo pipefail

OLLAMA_URL="${OLLAMA_URL:-https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.zst}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Stahuji Ollama ..."
curl -fsSL -o "$TMP/ollama.tar.zst" "$OLLAMA_URL"
tar --zstd -xf "$TMP/ollama.tar.zst" -C "$TMP"
install -m 0755 "$TMP/bin/ollama" /usr/bin/ollama
/usr/bin/ollama --version
