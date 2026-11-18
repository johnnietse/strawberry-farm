#!/usr/bin/env bash
# Install the research assistant's language model into Ollama, offline-capable.
#
#   bash ml_engine/models/fetch_models.sh            # Ollama on this machine
#   OLLAMA="docker compose exec -T ollama ollama" bash ml_engine/models/fetch_models.sh
#
# 1. Tries Ollama's own registry (qwen2.5:1.5b).
# 2. Otherwise downloads the same weights from this repository's GitHub release, checks the
#    SHA-256 and builds the model from models/ollama/Modelfile under the same name.
# The forecast models and the LED policy need nothing: they are in the repository.
set -euo pipefail
cd "$(dirname "$0")"
OLLAMA=${OLLAMA:-ollama}
NAME=qwen2.5:1.5b
FILE=qwen2.5-1.5b-instruct-q4_K_M.gguf
URL=https://github.com/johnnietse/strawberry-farm/releases/download/models-2026-11-15/$FILE
SHA=183715c435899236895da3869489cc30ac241476b4971a20285b1a462818a5b4

if $OLLAMA pull "$NAME"; then
  echo "installed $NAME from the Ollama registry"
  exit 0
fi

echo "registry not reachable: using the GitHub release copy"
if [ ! -f "ollama/$FILE" ]; then
  curl -fL --retry 3 -o "ollama/$FILE.part" "$URL"
  mv "ollama/$FILE.part" "ollama/$FILE"
fi
echo "$SHA  ollama/$FILE" | sha256sum -c -
if [[ "$OLLAMA" == *docker* ]]; then
  docker compose cp "ollama/$FILE" ollama:/tmp/$FILE
  docker compose cp ollama/Modelfile ollama:/tmp/Modelfile
  $OLLAMA create "$NAME" -f /tmp/Modelfile
else
  (cd ollama && $OLLAMA create "$NAME" -f Modelfile)
fi
echo "installed $NAME from $FILE"
