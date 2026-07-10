# Guardrails — Quick Reference

Short overview of implemented guardrails, **page by page**.

**Global layers (where used):**
- **L1** — Regex / literal injection patterns
- **L2** — Llama Prompt Guard (injection / jailbreak)
- **Output** — Schema, traceability, NLI / intent checks on generated content

Config: `Backend/.env` · Code: `Backend/app/guardrails/`

---

## 1. Specification Intelligence (`dataset-generator`)

| When | Guardrail | Blocks if |
|------|-----------|-----------|
| Document upload | L1 + L2 input scan | Injection / jailbreak in PDF/DOCX/TXT |
| Extraction complete | Output validation | Invalid schema, bad clause hierarchy, broken source traceability |
| Extraction complete | NLI groundedness | Extracted claims not supported by source clauses |

**Not on this page:** Telecom log checks, script syntax checks.

---

## 2. Test Script Generator (`test-script-generator`)

| When | Guardrail | Blocks if |
|------|-----------|-----------|
| Generate / Save template | L2 prompt scan (L1 on save) | Prompt injection or off-topic refine text |
| Load dataset | Input scan (same as Spec Intel upload) | Malicious dataset file |
| Generate script | Script guardrails | Python syntax error, missing test-case traceability, groundedness fail, off-topic script |
| Generate test cases | Intent coverage | Mandatory intents from dataset not covered |
| Refine (test script) | Strict script + traceability + groundedness | Refined code fails quality checks |
| Refine (test cases) | Structure + intent coverage | Invalid JSON or intents not covered |

**Note:** Custom prompt-only generation (no dataset) skips strict script guardrails.

---

## 3. Bug Discovery (`bug-discovery`)

Runs on **log select**, **upload**, and **Start RCA**.

| Order | Guardrail | Blocks if |
|-------|-----------|-----------|
| 1 | **Telecom domain** (`telecom_domain_check.py`) | Not an OAI log (runtime, plain gNB, or build/compile) |
| 2 | **Historical pattern** (`historical_pattern_check.py`) | No close match to previously analyzed logs (mode-dependent) |
| 3 | **Data quality** (`data_quality_check.py`) | Truncated / missing timestamps / empty sections / incomplete event tail |
| 4 | **Input security** (optional) | L1 + L2 injection in log text |

**Telecom domain checks (short):**
- **Runtime fingerprint** — `[MAC]`, `[ITTI]`, timestamps, `TASK_*`, `LOG_*`
- **Plain gNB / GDB** — `[GNB_APP]`, `[NR_PHY]` without timestamps
- **Build / compile** — `OPENAIR_DIR`, `nr-softmodem`, `cmake`, `F1AP_`, linker errors
- **Negative domain** — Web, DB, Windows event logs
- **Score** — Weighted relevance; block below threshold (`balanced` mode)

**UI messages:**
- Domain fail → `Domain: Provided logs do not appear to be from a supported 5G network component.`
- Historical fail/warn → `This appears to be a new log file — human review is recommended.`
- Data quality warn/fail → `Log file appears incomplete; expected events are missing.`
- Security fail → `Log file blocked — input guardrails`

**Historical pattern pipeline (learned from past RCA):**
1. On completed RCA → milestone pattern saved to `learned_patterns.json`
2. On log select/upload → extract steps and compare to all learned patterns
3. **Known log** (similar to a previous analysis) → pass
4. **New log** (no close match) → warn: *human review recommended* (advisory mode)

Patterns are synced from `resources/bug_history/*.json` where `analysis_completed: true`.

**Data quality checks:**
- Truncated capture (mid-line EOF, truncation markers, abnormally short OAI logs)
- Missing / sparse timestamps on runtime OAI logs
- Empty sections (large blank gaps, mostly empty files)
- Incomplete event tail vs expected late-stage milestones for the scenario
- Peer length vs nearest similar learned pattern (stricter when the upload is a step-prefix of a known capture)

**Improving truncation accuracy:**
1. Restart backend after changing `data_quality_check.py` or `.env` flags.
2. Prefer uploading the real file path (not a pasted snippet) so EOF uses the true file tail.
3. Keep `GUARDRAILS_BD_DATA_QUALITY_MODE=advisory` while tuning; switch to `balanced` once false positives are low.
4. Lower `GUARDRAILS_BD_DATA_QUALITY_MIN_LENGTH_RATIO` (default `0.40`) only if short-but-complete logs are over-flagged; raise it (e.g. `0.55`) to catch more clean line-boundary cuts.
5. Grow `learned_patterns.json` via completed RCAs — peer comparison needs similar prior captures of the same scenario.
6. Mid-line cuts (`[MAC] [2`, `...: Pa`) are detected from the file/buffer tail; clean cuts that already contain a failure marker still rely on peer length / procedure heuristics.
### Bug Discovery `.env` flags

```env
GUARDRAILS_BUG_DISCOVERY_LOG_ENABLED=true      # master switch
GUARDRAILS_BUG_DISCOVERY_INPUT_ENABLED=false   # L1 + L2 security
GUARDRAILS_BD_TELECOM_DOMAIN_ENABLED=true      # OAI domain validation
GUARDRAILS_BD_TELECOM_DOMAIN_MODE=balanced     # advisory | balanced | strict
GUARDRAILS_BD_HISTORICAL_PATTERN_ENABLED=true  # historical pattern matching
GUARDRAILS_BD_HISTORICAL_PATTERN_MODE=advisory # advisory | balanced | strict
GUARDRAILS_BD_HISTORICAL_MIN_SIMILARITY=0.65
GUARDRAILS_BD_DATA_QUALITY_ENABLED=true        # truncation / completeness
GUARDRAILS_BD_DATA_QUALITY_MODE=advisory       # advisory | balanced | strict
GUARDRAILS_BD_DATA_QUALITY_MIN_COMPLETENESS=0.70
```

---

## 4. Pages — No guardrails yet

| Page | Status |
|------|--------|
| Code Assistant | Not implemented |
| Test Deployment | Not implemented |
| Test Execution | Not implemented |
| Code Evaluation | Not implemented |
| Prompt Templates | Not implemented (standalone) |
| User History / Activity Log | Display only — no scanning |

---

## 5. Module map

| Module | Used on |
|--------|---------|
| `input_guardrail.py` | Spec Intel, TSG, Bug Discovery (security) |
| `llama_guard_service.py` | L1 + L2 engine |
| `output_guardrail.py` / `output_validators.py` | Spec Intel extraction |
| `nli_groundedness_service.py` | Spec Intel output |
| `tsg_prompt_guardrail.py` | TSG prompts |
| `test_script_guardrail.py` | TSG script generate/refine |
| `test_script_traceability.py` | TSG scripts |
| `test_script_groundedness.py` | TSG scripts |
| `intent_coverage_service.py` | TSG test cases |
| `refine_guardrail.py` | TSG refine |
| `bug_discovery_log_guardrail.py` | Bug Discovery |
| `telecom_domain_check.py` | Bug Discovery domain |
| `log_milestone_extractor.py` | Bug Discovery historical |
| `historical_pattern_check.py` | Bug Discovery historical |
| `log_pattern_builder.py` | Build pattern corpus |
| `data_quality_check.py` | Bug Discovery data quality |

---

## 6. Tests

```bash
# Bug Discovery telecom domain
python3 "Backend/Guardrails/Bug Discovery/telecom_domain_check_test.py"

# Bug Discovery historical pattern matching
python3 "Backend/Guardrails/Bug Discovery/historical_pattern_check_test.py"

# Bug Discovery data quality
python3 "Backend/Guardrails/Bug Discovery/data_quality_check_test.py"
```

Valid corpus: `Backend/app/services/Error_fixing_pipelin/log_files/`  
Invalid fixtures: `Backend/Guardrails/Bug Discovery/fixtures/`

---

*Planned but not implemented:* scenario relevance, temporal window (see `Backend/Guardrails/Bug Discovery/targets/log_files_section`).
