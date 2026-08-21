#!/usr/bin/env python3
"""Prefetch Hugging Face models required by Backend guardrails.

Run after installing Guardrails/requirements.txt (from Backend/):

  ./venv/bin/pip install -r Guardrails/requirements.txt
  ./venv/bin/python Guardrails/download_models.py

Loads HF_TOKEN from Backend/.env when present.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

GUARDRAILS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = GUARDRAILS_DIR.parent


def _load_dotenv() -> None:
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path)


def _hf_token() -> Optional[str]:
    return os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN") or None


def _download_hub(repo_id: str, *, gated: bool = False) -> None:
    from huggingface_hub import snapshot_download

    token = _hf_token()
    print(f"\n==> Downloading {repo_id}")
    if gated and not token:
        print(
            "ERROR: HF_TOKEN / HUGGINGFACE_HUB_TOKEN is required for gated model "
            f"{repo_id}. Set it in Backend/.env and accept the license on Hugging Face."
        )
        sys.exit(1)
    kwargs = {"repo_id": repo_id}
    if token:
        kwargs["token"] = token
    path = snapshot_download(**kwargs)
    print(f"    cached at: {path}")


def _warm_prompt_guard() -> None:
    """Trigger the same load path the app uses (validates transformers + token)."""
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    from app.guardrails.config import PROMPT_GUARD_MODEL
    from app.guardrails.llama_guard_service import ensure_prompt_guard_loaded

    print(f"\n==> Warming Prompt Guard via app loader ({PROMPT_GUARD_MODEL})")
    ok = ensure_prompt_guard_loaded()
    if not ok:
        print(
            "WARNING: Prompt Guard did not load. Check HF_TOKEN, Meta license acceptance, "
            "and network access. Layer 2 may fail open depending on env flags."
        )
    else:
        print("    Prompt Guard ready.")


def _warm_nli() -> None:
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    from app.guardrails.config import NLI_MODEL
    from app.guardrails.nli_groundedness_service import _nli_model

    print(f"\n==> Warming NLI model ({NLI_MODEL})")
    ok = _nli_model.load()
    if not ok:
        print(f"WARNING: NLI model failed to load: {_nli_model.load_error}")
    else:
        print("    NLI model ready.")


def _check_local_classifier() -> None:
    from app.guardrails.config import GUARDRAIL_CLASSIFIER_MODEL_PATH

    path = Path(GUARDRAIL_CLASSIFIER_MODEL_PATH)
    weights = path / "model.safetensors"
    print(f"\n==> Checking local RoBERTa classifier at {path}")
    if not path.exists():
        print("WARNING: classifier directory missing.")
        return
    if not weights.exists():
        print("WARNING: model.safetensors missing.")
        return
    size = weights.stat().st_size
    if size < 1_000_000:
        print(
            f"WARNING: model.safetensors is only {size} bytes — likely a Git LFS pointer. "
            "Run: git lfs pull --include="
            '"Backend/Guardrails/Fine-tuning/fine_tuned_guardrail_roberta/model.safetensors"'
        )
    else:
        print(f"    weights ok ({size / (1024 * 1024):.1f} MB)")


def main() -> None:
    _load_dotenv()
    os.chdir(BACKEND_DIR)

    prompt_guard = os.getenv("PROMPT_GUARD_MODEL", "meta-llama/Llama-Prompt-Guard-2-86M")
    nli_model = os.getenv("NLI_MODEL", "cross-encoder/nli-deberta-v3-small")

    print("Guardrails model download")
    print(f"  Backend: {BACKEND_DIR}")
    print(f"  HF token set: {bool(_hf_token())}")

    _download_hub(prompt_guard, gated=True)
    _download_hub(nli_model, gated=False)

    _warm_prompt_guard()
    _warm_nli()
    _check_local_classifier()

    print("\nDone. Guardrail models are cached for runtime use.")


if __name__ == "__main__":
    main()
