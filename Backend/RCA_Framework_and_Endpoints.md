# RCA Framework Working and API Endpoints (Brief)

This document summarizes how the RCA backend flow works and lists all available API endpoints with short functionality notes.

## 1) How the RCA Framework Works

The backend is a FastAPI service (`main.py`) that mounts routes from `app/api/endpoints.py`. The overall runtime flow is:

1. Environment setup and service boot
   - Loads `.env` (Backend-first fallback strategy).
   - Initializes API routes and health/root endpoints.
2. Input collection
   - Uploads logs/documents/configs from UI.
   - Stores uploaded assets in `resources/*` or pipeline-specific folders.
3. RCA analysis execution
   - `POST /api/rca/analyze` runs RCA scripts on uploaded logs and produces structured JSON output.
   - Supports analysis views such as `error`, `function`, `impact`, `kt`, and `ai`.
4. Error-fixing pipeline execution
   - `POST /api/error-fixing/analyze` runs the complete fixing pipeline.
   - Can process normal error flow or crash-analysis flow.
   - Produces suspected functions/configs, fix suggestions, and investigation commands.
5. Existing-fix intelligence
   - `POST /api/error-fixing/check-existing-fix` searches commit embeddings to detect prior similar fixes.
6. Patch and code-assistant operations
   - Applies patches, runs investigations, and supports Git commit/push actions through dedicated endpoints.
7. Persistence and history
   - Saves RCA analyses to bug history.
   - Logs history for test script generation and bug discovery tracking.
8. Evaluation/verification
   - Code evaluation endpoints load previous analyses and trigger test/evaluation runs.

## 2) API Endpoints and Functionalities (Brief)

Base file: `app/api/endpoints.py`  
Linux variant: `app/api/endpoints_linux.py` (same route set)

### Core

| Method | Endpoint | Functionality |
|---|---|---|
| GET | `/` | Backend welcome/status message. |
| GET | `/health` | Health check for service readiness. |

### General File Upload

| Method | Endpoint | Functionality |
|---|---|---|
| POST | `/api/upload` | Uploads a file into uploaded docs storage. |
| GET | `/api/uploaded-files` | Lists uploaded files and metadata. |

### Dataset

| Method | Endpoint | Functionality |
|---|---|---|
| POST | `/api/dataset/upload-document` | Uploads source document for dataset generation. |
| GET | `/api/dataset/document-sections/{file_id}` | Returns top-level sections from uploaded document. |
| GET | `/api/dataset/document-subsections/{file_id}/{section}` | Returns subsections for selected section. |
| POST | `/api/dataset/set-working-directory` | Sets dataset generation working directory. |
| POST | `/api/dataset/set-output-directory` | Sets dataset output directory. |
| POST | `/api/dataset/generate` | Starts dataset generation job. |
| GET | `/api/dataset/status/{job_id}` | Gets current dataset job status. |
| GET | `/api/dataset/download/{job_id}` | Downloads generated dataset output. |
| GET | `/api/dataset/files/{job_id}` | Lists output files for dataset job. |
| POST | `/api/dataset/extract-pyqt-style` | Runs simplified PyQt-style extraction flow. |
| GET | `/api/dataset/extract-folder-path` | Returns extracted/default folder path details. |
| POST | `/api/dataset/open-folder` | Opens a folder path for user navigation. |

### Test Script Generation

| Method | Endpoint | Functionality |
|---|---|---|
| GET | `/api/test-script/prompts` | Returns prompt templates for script generation. |
| POST | `/api/test-script/generate` | Generates test script from request/prompt inputs. |
| POST | `/api/test-script/history` | Fetches test script generation history. |
| POST | `/api/history/user` | Retrieves user-scoped history entries. |
| POST | `/api/test-script/refine` | Refines an existing generated test script. |
| POST | `/api/test-script/upload-reference` | Uploads reference code/spec for script generation. |
| POST | `/api/test-script/load-dataset` | Loads uploaded dataset files for script generation context. |
| GET | `/api/test-script/test-types` | Lists supported test types. |
| POST | `/api/test-script/generate-by-type` | Generates test script by selected test type. |
| POST | `/api/save-test-script` | Saves generated test script. |
| POST | `/api/test-script/save-template` | Saves a custom script template. |
| DELETE | `/api/test-script/delete-template` | Deletes a custom script template. |
| GET | `/api/test-script/custom-templates` | Lists available custom templates. |

### Deployment

| Method | Endpoint | Functionality |
|---|---|---|
| POST | `/api/deployment/deploy` | Starts deployment job for test scripts/config. |
| GET | `/api/deployment/status/{job_id}` | Returns deployment job status. |
| GET | `/api/deployment/configs` | Returns available deployment configuration options. |
| GET | `/api/deployment/test-connection` | Checks deployment connectivity/availability. |
| POST | `/api/deployment/upload-config` | Uploads deployment config file. |
| GET | `/api/deployment/config-files` | Lists uploaded deployment config files. |
| DELETE | `/api/deployment/config-files/{file_id}` | Deletes a deployment config file. |

### Test Execution

| Method | Endpoint | Functionality |
|---|---|---|
| POST | `/api/test-execution/execute` | Starts test execution job. |
| GET | `/api/test-execution/status/{job_id}` | Returns test execution status. |
| GET | `/api/test-execution/configs` | Returns test execution configuration options. |

### RCA / Bug Discovery

| Method | Endpoint | Functionality |
|---|---|---|
| POST | `/api/rca/upload-logs` | Uploads one or more log files for RCA. |
| POST | `/api/rca/analyze` | Runs RCA engine and returns selected/full analysis data. |
| POST | `/api/rca/save-analysis` | Saves RCA/fix analysis to bug history storage. |

### Error Fixing Pipeline

| Method | Endpoint | Functionality |
|---|---|---|
| POST | `/api/error-fixing/analyze` | Runs complete error-fixing pipeline and generates fixes. |
| POST | `/api/error-fixing/update-embeddings` | Updates commit/code embeddings after patch application. |
| GET | `/api/error-fixing/status` | Returns pipeline availability and integration status. |
| GET | `/api/error-fixing/log-files` | Lists available `.log` files for analysis. |
| POST | `/api/error-fixing/upload-log` | Uploads a log into pipeline log directory. |
| GET | `/api/error-fixing/deployment-context-defaults` | Returns default deployment context from patterns DB. |
| POST | `/api/error-fixing/check-existing-fix` | Searches Git-history embeddings for similar existing fixes. |
| POST | `/api/error-fixing/impact-analysis` | Performs impact analysis from selected log/context. |

### Code Assistant

| Method | Endpoint | Functionality |
|---|---|---|
| GET | `/api/code-assistant/bug-history` | Lists saved bug analysis history entries. |
| GET | `/api/code-assistant/load-analysis/{filename}` | Loads a specific saved bug analysis file. |
| POST | `/api/code-assistant/apply-patches` | Applies selected code/config patches. |
| POST | `/api/code-assistant/git-commit-push` | Performs Git commit/push workflow from API request. |
| POST | `/api/code-assistant/run-investigation` | Runs investigation commands and returns outputs. |

### History Logging

| Method | Endpoint | Functionality |
|---|---|---|
| POST | `/api/history/test-script` | Appends history record for test script generation. |
| POST | `/api/history/test-case` | Appends history record for test case generation. |
| POST | `/api/history/bug-discovery` | Appends bug discovery analysis history. |

### Code Evaluation

| Method | Endpoint | Functionality |
|---|---|---|
| GET | `/api/code-evaluation/bug-history` | Lists bug history for evaluation workflow. |
| GET | `/api/code-evaluation/load-analysis/{filename}` | Loads selected analysis for evaluation. |
| POST | `/api/code-evaluation/run-tests` | Runs evaluation tests on chosen analysis/configuration. |

## Notes

- Route registration is done via `app.include_router(router)` in `main.py`.
- Current route inventory in `endpoints.py`: **61 endpoints**.
- Job-state handling for some flows is in-memory (`job_status` dict), so persistence behavior depends on process lifecycle.
