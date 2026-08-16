#!/usr/bin/env bash
# Populate the offline tokenizer artifact cache mounted into the gateway container.
# Run ONCE from a clean checkout (needs network). Afterwards the container runs the
# recount benchmark fully offline (HF_HUB_OFFLINE=1).
#
# Downloads ONLY tokenizer artifacts (no model weights):
#   - tiktoken cl100k_base / o200k_base BPE files
#   - hf-internal-testing/llama-tokenizer : tokenizer.json, tokenizer.model, configs
set -euo pipefail
cd "$(dirname "$0")/.."

export TIKTOKEN_CACHE_DIR="$PWD/tokenizer_cache/tiktoken"
export HF_HOME="$PWD/tokenizer_cache/hf"
mkdir -p "$TIKTOKEN_CACHE_DIR" "$HF_HOME"

python - <<'PY'
import warnings; warnings.filterwarnings("ignore")
import tiktoken
for n in ("cl100k_base", "o200k_base"):
    tiktoken.get_encoding(n).encode("populate cache")
    print("cached tiktoken:", n)

from transformers import AutoTokenizer
REPO = "hf-internal-testing/llama-tokenizer"
tk = AutoTokenizer.from_pretrained(REPO)
print("cached HF tokenizer:", REPO, "vocab", tk.vocab_size, "is_fast", tk.is_fast)

from huggingface_hub import hf_hub_download, HfApi
for f in ("tokenizer.json", "tokenizer.model"):
    hf_hub_download(REPO, f)
    print("cached artifact:", f)
try:
    print("revision:", HfApi().model_info(REPO).sha)
except Exception as e:
    print("revision lookup failed:", e)
PY

echo "cache ready:"
du -sh tokenizer_cache/* 2>/dev/null || true
echo "now: docker compose up --build -d"
