#!/usr/bin/env bash
# Nainstaluje Ollama binarku do /usr/bin (bez /usr/local, kvuli ostree).
set -euo pipefail

VERSION="${OLLAMA_VERSION:-latest}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ "$VERSION" = "latest" ]; then
  URL="https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tgz"
else
  URL="https://github.com/ollama/ollama/releases/download/${VERSION}/ollama-linux-amd64.tgz"
fi

echo "Stahuji Ollama ($VERSION) ..."
curl -fsSL -o "$TMP/ollama.tgz" "$URL"
tar -xzf "$TMP/ollama.tgz" -C "$TMP"
install -m 0755 "$TMP/bin/ollama" /usr/bin/ollama
/usr/bin/ollama --version
