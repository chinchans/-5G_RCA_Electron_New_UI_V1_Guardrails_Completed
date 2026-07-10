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

# Layer 1 regex/literal injection patterns (set false to test Llama Prompt Guard in isolation)
GUARDRAILS_LAYER1_ENABLED = os.getenv(
    "GUARDRAILS_LAYER1_ENABLED", "true"
).lower() in ("1", "true", "yes")

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

# Test Script Generator — scan modified prompts (Test Case / Test Script / Custom) with Llama Guard
GUARDRAILS_TSG_PROMPT_ENABLED = os.getenv(
    "GUARDRAILS_TSG_PROMPT_ENABLED", "true"
).lower() in ("1", "true", "yes")
GUARDRAILS_TSG_FORCE_LAYER2 = os.getenv(
    "GUARDRAILS_TSG_FORCE_LAYER2", "true"
).lower() in ("1", "true", "yes")
# Block TSG prompt actions when full Llama Guard cannot load (strict; default fail-open like uploads)
GUARDRAILS_TSG_REQUIRE_LAYER2 = os.getenv(
    "GUARDRAILS_TSG_REQUIRE_LAYER2", "false"
).lower() in ("1", "true", "yes")
GUARDRAILS_TSG_REFINE_SCOPE_ENABLED = os.getenv(
    "GUARDRAILS_TSG_REFINE_SCOPE_ENABLED", "true"
).lower() in ("1", "true", "yes")
GUARDRAILS_SCRIPT_SCOPE_ENABLED = os.getenv(
    "GUARDRAILS_SCRIPT_SCOPE_ENABLED", "true"
).lower() in ("1", "true", "yes")
GUARDRAILS_REFINE_STRICT_OUTPUT = os.getenv(
    "GUARDRAILS_REFINE_STRICT_OUTPUT", "true"
).lower() in ("1", "true", "yes")
GUARDRAILS_BUG_DISCOVERY_LOG_ENABLED = os.getenv(
    "GUARDRAILS_BUG_DISCOVERY_LOG_ENABLED", "true"
).lower() in ("1", "true", "yes")
# Bug Discovery — Layer 1 regex + Layer 2 Llama Guard on log files (independent of telecom domain)
GUARDRAILS_BUG_DISCOVERY_INPUT_ENABLED = os.getenv(
    "GUARDRAILS_BUG_DISCOVERY_INPUT_ENABLED", "true"
).lower() in ("1", "true", "yes")

# Bug Discovery — OAI telecom domain validation (structural fingerprint + evidence scoring)
GUARDRAILS_BD_TELECOM_DOMAIN_ENABLED = os.getenv(
    "GUARDRAILS_BD_TELECOM_DOMAIN_ENABLED", "true"
).lower() in ("1", "true", "yes")
GUARDRAILS_BD_TELECOM_DOMAIN_MODE = os.getenv(
    "GUARDRAILS_BD_TELECOM_DOMAIN_MODE", "balanced"
).lower().strip()  # advisory | balanced | strict
GUARDRAILS_BD_TELECOM_MIN_OVERALL = float(
    os.getenv("GUARDRAILS_BD_TELECOM_MIN_OVERALL", "0.65")
)
GUARDRAILS_BD_TELECOM_MIN_STRUCTURAL = float(
    os.getenv("GUARDRAILS_BD_TELECOM_MIN_STRUCTURAL", "0.25")
)

# Bug Discovery — historical pattern matching (canonical steps + n-gram similarity)
GUARDRAILS_BD_HISTORICAL_PATTERN_ENABLED = os.getenv(
    "GUARDRAILS_BD_HISTORICAL_PATTERN_ENABLED", "true"
).lower() in ("1", "true", "yes")
GUARDRAILS_BD_HISTORICAL_PATTERN_MODE = os.getenv(
    "GUARDRAILS_BD_HISTORICAL_PATTERN_MODE", "advisory"
).lower().strip()  # advisory | balanced | strict
GUARDRAILS_BD_HISTORICAL_MIN_SIMILARITY = float(
    os.getenv("GUARDRAILS_BD_HISTORICAL_MIN_SIMILARITY", "0.65")
)
GUARDRAILS_BD_HISTORICAL_NGRAM_SIZE = int(
    os.getenv("GUARDRAILS_BD_HISTORICAL_NGRAM_SIZE", "3")
)
GUARDRAILS_BD_HISTORICAL_MIN_PATTERNS = int(
    os.getenv("GUARDRAILS_BD_HISTORICAL_MIN_PATTERNS", "1")
)
GUARDRAILS_BD_HISTORICAL_WEIGHT_LEVENSHTEIN = float(
    os.getenv("GUARDRAILS_BD_HISTORICAL_WEIGHT_LEVENSHTEIN", "0.6")
)
GUARDRAILS_BD_HISTORICAL_WEIGHT_COSINE = float(
    os.getenv("GUARDRAILS_BD_HISTORICAL_WEIGHT_COSINE", "0.4")
)

# Bug Discovery — data quality (truncation, timestamps, empty sections, completeness)
GUARDRAILS_BD_DATA_QUALITY_ENABLED = os.getenv(
    "GUARDRAILS_BD_DATA_QUALITY_ENABLED", "true"
).lower() in ("1", "true", "yes")
GUARDRAILS_BD_DATA_QUALITY_MODE = os.getenv(
    "GUARDRAILS_BD_DATA_QUALITY_MODE", "advisory"
).lower().strip()  # advisory | balanced | strict
GUARDRAILS_BD_DATA_QUALITY_MIN_COMPLETENESS = float(
    os.getenv("GUARDRAILS_BD_DATA_QUALITY_MIN_COMPLETENESS", "0.70")
)
GUARDRAILS_BD_DATA_QUALITY_MIN_TIMESTAMP_RATIO = float(
    os.getenv("GUARDRAILS_BD_DATA_QUALITY_MIN_TIMESTAMP_RATIO", "0.15")
)
GUARDRAILS_BD_DATA_QUALITY_EMPTY_GAP_LINES = int(
    os.getenv("GUARDRAILS_BD_DATA_QUALITY_EMPTY_GAP_LINES", "40")
)
# Flag as truncated when capture is shorter than this fraction of nearest learned pattern
GUARDRAILS_BD_DATA_QUALITY_MIN_LENGTH_RATIO = float(
    os.getenv("GUARDRAILS_BD_DATA_QUALITY_MIN_LENGTH_RATIO", "0.40")
)
# Minimum peer pattern step count before length comparison applies
GUARDRAILS_BD_DATA_QUALITY_MIN_PEER_STEPS = int(
    os.getenv("GUARDRAILS_BD_DATA_QUALITY_MIN_PEER_STEPS", "8")
)

# Generated test script traceability (test case ID + title comments)
GUARDRAILS_SCRIPT_TRACEABILITY_ENABLED = os.getenv(
    "GUARDRAILS_SCRIPT_TRACEABILITY_ENABLED", "true"
).lower() in ("1", "true", "yes")
GUARDRAILS_SCRIPT_TRACEABILITY_STRICT = os.getenv(
    "GUARDRAILS_SCRIPT_TRACEABILITY_STRICT", "true"
).lower() in ("1", "true", "yes")
GUARDRAILS_SCRIPT_TRACEABILITY_MIN_PERCENT = float(
    os.getenv("GUARDRAILS_SCRIPT_TRACEABILITY_MIN_PERCENT", "100")
)

# Generated test script groundedness vs source test cases (NLI + keyword)
# mode: level2 = per-function claim grounding (block on contradiction or very low scores)
#       level3 = level2 checks + every step/expected result must appear in script
GUARDRAILS_SCRIPT_GROUNDEDNESS_ENABLED = os.getenv(
    "GUARDRAILS_SCRIPT_GROUNDEDNESS_ENABLED", "true"
).lower() in ("1", "true", "yes")
GUARDRAILS_SCRIPT_GROUNDEDNESS_MODE = os.getenv(
    "GUARDRAILS_SCRIPT_GROUNDEDNESS_MODE", "level2"
).lower().strip()
SCRIPT_GROUNDEDNESS_LEVEL2_MIN_PERCENT = float(
    os.getenv("SCRIPT_GROUNDEDNESS_LEVEL2_MIN_PERCENT", "70")
)
SCRIPT_GROUNDEDNESS_LEVEL2_BLOCK_FLOOR_PERCENT = float(
    os.getenv("SCRIPT_GROUNDEDNESS_LEVEL2_BLOCK_FLOOR_PERCENT", "40")
)
SCRIPT_GROUNDEDNESS_ENTAILMENT_THRESHOLD = float(
    os.getenv("SCRIPT_GROUNDEDNESS_ENTAILMENT_THRESHOLD", "0.50")
)
SCRIPT_GROUNDEDNESS_MAX_CLAIMS_PER_FUNCTION = int(
    os.getenv("SCRIPT_GROUNDEDNESS_MAX_CLAIMS_PER_FUNCTION", "24")
)
SCRIPT_GROUNDEDNESS_MAX_PAIRS = int(os.getenv("SCRIPT_GROUNDEDNESS_MAX_PAIRS", "120"))

# NLI groundedness (cross-encoder) for Specification Intelligence output validation
NLI_GROUNDEDNESS_ENABLED = os.getenv("NLI_GROUNDEDNESS_ENABLED", "true").lower() in ("1", "true", "yes")
NLI_MODEL = os.getenv("NLI_MODEL", "cross-encoder/nli-deberta-v3-small")
NLI_CONTRADICTION_THRESHOLD = float(os.getenv("NLI_CONTRADICTION_THRESHOLD", "0.65"))
NLI_MAX_PAIRS = int(os.getenv("NLI_MAX_PAIRS", "40"))
NLI_MAX_PREMISE_CHARS = int(os.getenv("NLI_MAX_PREMISE_CHARS", "2000").replace("_", ""))
NLI_STRICT = os.getenv("NLI_STRICT", "false").lower() in ("1", "true", "yes")
NLI_SKIP_ON_MODEL_ERROR = os.getenv("NLI_SKIP_ON_MODEL_ERROR", "true").lower() in ("1", "true", "yes")

# Intent coverage — semantic (NLI) matching for generated test cases
# match_mode: hybrid = keyword/clause fast path + NLI for gaps; semantic = NLI only (+ explicit/clause)
INTENT_COVERAGE_MATCH_MODE = os.getenv("INTENT_COVERAGE_MATCH_MODE", "hybrid").lower().strip()
INTENT_COVERAGE_USE_NLI = os.getenv("INTENT_COVERAGE_USE_NLI", "true").lower() in ("1", "true", "yes")
INTENT_COVERAGE_NLI_THRESHOLD = float(os.getenv("INTENT_COVERAGE_NLI_THRESHOLD", "0.50"))
INTENT_COVERAGE_DOMAIN_GATE = os.getenv(
    "INTENT_COVERAGE_DOMAIN_GATE", "true"
).lower() in ("1", "true", "yes")
