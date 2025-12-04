#!/usr/bin/env bash
set -euo pipefail
curl -fsSL https://ollama.com/install.sh | sh
ollama run mistral:7b-instruct -p "Hello from FLEX Coach" || true
