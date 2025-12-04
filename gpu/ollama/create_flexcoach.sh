#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
ollama create flexcoach:7b -f Modelfile.sample
ollama run flexcoach:7b -p "How do I reclaim host in Zoom using rtcedu SSO?"
