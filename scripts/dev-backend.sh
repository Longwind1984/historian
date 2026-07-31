#!/usr/bin/env bash
# Local dev helper: run backend without Docker (YAML in-memory indexes, no DB).
# Usage: scripts/dev-backend.sh
set -euo pipefail
exec "$(dirname "$0")/run-backend.sh" --host 0.0.0.0 --port 8000 --reload
