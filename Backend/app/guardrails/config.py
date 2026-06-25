"""Configuration for Specification Intelligence input guardrails."""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

# Specification Intelligence extract layout (primary)
SPEC_INTEL_EXTRACT_ROOT = BACKEND_DIR / "extract"
SPEC_INTEL_DATASETS_DIR = SPEC_INTEL_EXTRACT_ROOT / "datasets"
SPEC_INTEL_UPLOAD_JSON_DIR = SPEC_INTEL_EXTRACT_ROOT / "JSON files"
# Legacy path kept for resolving older datasets
LEGACY_SPEC_INTEL_EXTRACT_ROOT = BACKEND_DIR / "resources" / "extract"

GUARDRAILS_ENABLED = os.getenv("GUARDRAILS_ENABLED", "true").lower() in ("1", "true", "yes")

MAX_UPLOAD_BYTES = int(os.getenv("GUARDRAILS_MAX_UPLOAD_MB", "25")) * 1024 * 1024
MAX_SCAN_CHARS = int(os.getenv("GUARDRAILS_MAX_SCAN_CHARS", "100_000").replace("_", ""))
MAX_LLM_INPUT_CHARS = int(os.getenv("GUARDRAILS_MAX_LLM_CHARS", "50_000").replace("_", ""))

ALLOWED_EXTENSIONS = frozenset({".pdf", ".docx", ".doc", ".txt", ".html", ".htm"})

# transformers = Meta Llama Prompt Guard (injection); ollama = Llama Guard 3; rules_only = regex only
LLAMA_GUARD_BACKEND = os.getenv("LLAMA_GUARD_BACKEND", "transformers").lower().strip()

PROMPT_GUARD_MODEL = os.getenv(
    "PROMPT_GUARD_MODEL",
    "meta-llama/Llama-Prompt-Guard-2-86M",
)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_GUARD_MODEL = os.getenv("OLLAMA_GUARD_MODEL", "llama-guard3")

HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")

# Probability/score above which injection is flagged (Prompt Guard softmax)
INJECTION_THRESHOLD = float(os.getenv("GUARDRAILS_INJECTION_THRESHOLD", "0.65"))

# When Layer 2 model cannot load, do not block entire uploads — fall back to tiered Layer 1 only
GUARDRAILS_FAIL_OPEN_ON_MODEL_ERROR = os.getenv(
    "GUARDRAILS_FAIL_OPEN_ON_MODEL_ERROR", "true"
).lower() in ("1", "true", "yes")

# Max tokens per Prompt Guard chunk (model limit ~512 tokens)
PROMPT_GUARD_MAX_LENGTH = int(os.getenv("PROMPT_GUARD_MAX_LENGTH", "512"))

BLOCK_ON_UNSAFE = os.getenv("GUARDRAILS_BLOCK_ON_UNSAFE", "true").lower() in ("1", "true", "yes")

# Azure Prompt Shields flag anti-jailbreak wrapper text as jailbreak — use plain formatting for LLM calls
GUARDRAILS_AZURE_SAFE_MODE = os.getenv("GUARDRAILS_AZURE_SAFE_MODE", "true").lower() in ("1", "true", "yes")

# Document already scanned at upload; skip re-scan on each extraction LLM chunk
GUARDRAILS_SKIP_EXTRACT_RESCAN = os.getenv("GUARDRAILS_SKIP_EXTRACT_RESCAN", "true").lower() in ("1", "true", "yes")

# For /api/dataset/upload-document: run Llama Guard on every chunk (not only Layer-1-suspicious)
GUARDRAILS_UPLOAD_FORCE_LAYER2 = os.getenv("GUARDRAILS_UPLOAD_FORCE_LAYER2", "true").lower() in ("1", "true", "yes")

# For /api/dataset/upload-document: require successful Layer 2 (Llama Guard) coverage.
# If model is unavailable, upload is blocked as unverified (opt-in strict mode).
GUARDRAILS_REQUIRE_UPLOAD_LAYER2 = os.getenv(
    "GUARDRAILS_REQUIRE_UPLOAD_LAYER2", "false"
).lower() in ("1", "true", "yes")

# NLI groundedness (cross-encoder) for Specification Intelligence output validation
NLI_GROUNDEDNESS_ENABLED = os.getenv("NLI_GROUNDEDNESS_ENABLED", "true").lower() in ("1", "true", "yes")
NLI_MODEL = os.getenv("NLI_MODEL", "cross-encoder/nli-deberta-v3-small")
NLI_CONTRADICTION_THRESHOLD = float(os.getenv("NLI_CONTRADICTION_THRESHOLD", "0.65"))
NLI_MAX_PAIRS = int(os.getenv("NLI_MAX_PAIRS", "40"))
NLI_MAX_PREMISE_CHARS = int(os.getenv("NLI_MAX_PREMISE_CHARS", "2000").replace("_", ""))
NLI_STRICT = os.getenv("NLI_STRICT", "false").lower() in ("1", "true", "yes")
NLI_SKIP_ON_MODEL_ERROR = os.getenv("NLI_SKIP_ON_MODEL_ERROR", "true").lower() in ("1", "true", "yes")
