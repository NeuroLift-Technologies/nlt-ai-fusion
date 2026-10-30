#!/usr/bin/env bash
# Assemble (and optionally publish) the AI-Fusion Lite CPU Gradio Space payload.
#
# This Space runs the Fusion runtime with GGUF model support for CPU inference,
# compatible with free-tier Lite CPU tier for models up to ~2GB.
#
# GitHub is the source of truth. This script copies the runtime subset of the
# repository into a staging directory so the Space never holds a second, drifting
# copy of `src/` in git:
#
#   README.md  requirements.txt  .env.example  app/  src/
#
# Nothing from apps/, backend/, services/, archive/, supabase/, docs/, tests/ or
# the repository's root requirements.txt is deployed.
#
# Usage:
#   spaces/ai-fusion-lite/sync-to-hub.sh                      # assemble only
#   spaces/ai-fusion-lite/sync-to-hub.sh --out /tmp/payload    # choose staging dir
#   spaces/ai-fusion-lite/sync-to-hub.sh --push <repo_id>      # assemble + upload
#
# Pushing needs an authenticated `hf` CLI (or huggingface_hub with HF_TOKEN in the
# environment). This script never handles credentials itself.

set -euo pipefail

SPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SPACE_DIR}/../.." && pwd)"
OUT_DIR="${REPO_ROOT}/build/space-ai-fusion-lite"
PUSH_TARGET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT_DIR="$2"; shift 2 ;;
    --push) PUSH_TARGET="$2"; shift 2 ;;
    -h|--help) sed -n '2,25p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

echo "==> source : ${REPO_ROOT}"
echo "==> payload: ${OUT_DIR}"

rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

# --- runtime payload --------------------------------------------------------
cp "${SPACE_DIR}/README.md"         "${OUT_DIR}/README.md"
cp "${SPACE_DIR}/requirements.txt"  "${OUT_DIR}/requirements.txt"
cp "${SPACE_DIR}/.env.example"      "${OUT_DIR}/.env.example"
cp -R "${SPACE_DIR}/app"            "${OUT_DIR}/app"
cp -R "${REPO_ROOT}/src"            "${OUT_DIR}/src"

# Session orchestration: the Space reuses the documented service boundary in
# services/api instead of reimplementing it, so only that package ships.
mkdir -p "${OUT_DIR}/services/api/app"
for pkg in services/__init__.py services/api/__init__.py; do
  cp "${REPO_ROOT}/${pkg}" "${OUT_DIR}/$(dirname "${pkg}")/"
done
cp "${REPO_ROOT}/services/api/app/__init__.py"       "${OUT_DIR}/services/api/app/"
cp "${REPO_ROOT}/services/api/app/schemas.py"        "${OUT_DIR}/services/api/app/"
cp "${REPO_ROOT}/services/api/app/session_service.py" "${OUT_DIR}/services/api/app/"

# Byte-compiled leftovers and local virtualenvs must never ship.
find "${OUT_DIR}" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "${OUT_DIR}" -type f -name '*.pyc' -delete 2>/dev/null || true

# --- guard: no secrets, no stray environment files --------------------------
if find "${OUT_DIR}" -name '.env' -o -name '*.pem' -o -name '*.key' | grep -q .; then
  echo "ERROR: refusing to assemble a payload containing credential-shaped files" >&2
  exit 1
fi

if grep -rlE '(hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|SUPABASE_KEY=[^[:space:]]+)' "${OUT_DIR}" >/dev/null 2>&1; then
  echo "ERROR: credential-shaped string found in the payload" >&2
  exit 1
fi

# --- manifest ---------------------------------------------------------------
cat > "${OUT_DIR}/PAYLOAD_MANIFEST.txt" <<MANIFEST
AI-Fusion Lite CPU Gradio Space payload
assembled_from : NeuroLift-Technologies/nlt-ai-fusion @ $(git -C "${REPO_ROOT}" rev-parse --short HEAD 2>/dev/null || echo "unknown")
assembled_at   : $(date -u +%Y-%m-%dT%H:%M:%SZ)
contents       : README.md requirements.txt .env.example app/ src/
                 services/api/app/ (session_service + schemas only)
decision_source: gguf (CPU inference via llama-cpp-python)
requires       : FUSION_GGUF_MODEL environment variable pointing to a .gguf file
excluded       : apps/ backend/ services/ archive/ supabase/ docs/ tests/ scripts/
                 repository root requirements.txt (superset for development)
MANIFEST

echo "==> payload contents"
(cd "${OUT_DIR}" && find . -maxdepth 1 -mindepth 1 | sort)

if [[ -n "${PUSH_TARGET}" ]]; then
  echo "==> uploading to ${PUSH_TARGET}"
  if command -v hf >/dev/null 2>&1; then
    hf upload "${PUSH_TARGET}" "${OUT_DIR}" . --repo-type space
  else
    python3 - "$PUSH_TARGET" "$OUT_DIR" <<'PY'
import sys
from huggingface_hub import HfApi

repo_id, folder = sys.argv[1], sys.argv[2]
HfApi().upload_folder(
    repo_id=repo_id,
    repo_type="space",
    folder_path=folder,
    commit_message="Deploy AI-Fusion Lite CPU Gradio Space from nlt-ai-fusion",
)
print(f"uploaded {folder} -> {repo_id}")
PY
  fi
fi

echo "==> done"
