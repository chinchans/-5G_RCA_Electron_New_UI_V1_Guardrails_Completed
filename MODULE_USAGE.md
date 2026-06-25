# RCA Electron Application - Complete Module Usage Guide

This document provides detailed instructions for using each module in the RCA Electron application, including required files, paths, dependencies, and step-by-step execution procedures.

## Table of Contents
- [Module 1: Dataset Generator](#module-1-dataset-generator)
- [Module 2: Test Script Generator](#module-2-test-script-generator)
- [Module 3: Test Deployment](#module-3-test-deployment)
- [Module 4: Test Execution](#module-4-test-execution)
- [Module 5: Bug Discovery](#module-5-bug-discovery)
- [Module 6: Code Evaluation](#module-6-code-evaluation)
- [Module 7: Code Assistant](#module-7-code-assistant)
- [Module 8: Error Fixing](#module-8-error-fixing)

---

## Module 1: Dataset Generator

### Overview
Extracts structured datasets from 5G specification documents (DOCX/PDF) by processing sections, subsections, and extracting 3GPP references and clauses.

### Functionalities
- Upload and process specification documents (DOCX/PDF format)
- Extract main sections and subsections from documents
- Extract 3GPP references and clauses recursively
- Download and process referenced 3GPP specifications
- Generate knowledge graphs from extracted data
- Export datasets in JSON format

### Required Technologies & Libraries
**Backend Dependencies:**
- `python-docx` - DOCX document processing
- `PyMuPDF` (fitz) - PDF document processing
- `beautifulsoup4` - HTML/XML parsing
- `networkx` - Graph generation
- `openai` (Azure OpenAI) - LLM processing
- `requests` - HTTP requests for downloading specs
- `python-dotenv` - Environment variable management

**Frontend Dependencies:**
- Electron framework
- Fetch API for HTTP requests

### Required Files & Paths

#### Input Files
- **Specification Document**: DOCX or PDF file containing 5G specifications
  - **Path**: `Backend/resources/uploaded_docs/`
  - **Format**: `.docx` or `.pdf`
  - **Example**: `23502-j50.docx`, `37340-j00.docx`

#### Output Files
- **Main Dataset File**: `{subsection_name}_output.json`
  - **Path**: `Backend/resources/extract/datasets/`
  - **Format**: JSON
- **Total Content File**: `{subsection_name}_total_content.txt`
  - **Path**: `Backend/resources/extract/datasets/`
  - **Format**: Plain text
- **Clause Files**: Multiple `{clause_reference}.txt` files
  - **Path**: `Backend/resources/extract/datasets/`
  - **Format**: Plain text

#### Directory Structure
```
Backend/
├── resources/
│   ├── uploaded_docs/          # Input: Upload specification documents here
│   └── extract/
│       └── datasets/            # Output: Generated datasets saved here
```

### Step-by-Step Usage Instructions

#### Step 1: Start Backend Server
```bash
cd RCA_Electron-main/Backend
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# OR
venv\Scripts\activate.bat     # Windows CMD
# OR
source venv/bin/activate      # macOS/Linux

python main.py
```
**Expected Output**: Server running on `http://localhost:8000`

#### Step 2: Start Frontend Application
```bash
cd RCA_Electron-main/Frontend
npm start
```
**Expected Output**: Electron window opens

#### Step 3: Navigate to Dataset Generator
1. In the Electron app, click on **"Tasks"** in the left sidebar
2. Click **"Launch"** button on the **"Dataset Generator"** module card

#### Step 4: Upload Specification Document
1. Click **"Upload Document"** button or drag-and-drop area
2. Select a DOCX or PDF file (e.g., `23502-j50.docx`)
3. Wait for upload confirmation
4. **File Location**: Uploaded to `Backend/resources/uploaded_docs/{uuid}.{extension}`

#### Step 5: Select Section and Subsection
1. After upload, main sections will appear in dropdown
2. Select a **Main Section** (e.g., "5.2.1 Initial Access")
3. Select a **Subsection** from the subsection dropdown
4. **Note**: Sections are extracted from Heading 1, subsections from Heading 2

#### Step 6: Set Working and Output Directories
1. **Working Directory**: Defaults to `Backend/resources/extract`
   - Can be changed via "Set Working Directory" button
   - Creates `datasets/` and `test_scripts/` subdirectories
2. **Output Directory**: Defaults to `Backend/resources/extract`
   - Can be changed via "Set Output Directory" button

#### Step 7: Generate Dataset
1. Click **"Generate Dataset"** button
2. **Process Flow**:
   - Extracts text from selected subsection (10% progress)
   - Extracts 3GPP references and clauses (20% progress)
   - Downloads referenced 3GPP specifications (30% progress)
   - Checks reference documents (40% progress)
   - Performs recursive clause extraction (70% progress)
   - Builds knowledge graph (90% progress)
   - Completes generation (100% progress)
3. **Status**: Monitor progress in status bar
4. **Completion**: Success message with file paths

#### Step 8: View Results
1. Generated files appear in the results section
2. **Output Files**:
   - `{subsection_name}_output.json` - Main dataset with graph structure
   - `{subsection_name}_total_content.txt` - Complete extracted text
   - Multiple `{clause_reference}.txt` files - Individual clause files
3. **File Location**: `Backend/resources/extract/datasets/`

### Execution Commands (Backend API)

#### Upload Document
```bash
POST http://localhost:8000/api/dataset/upload-document
Content-Type: multipart/form-data
Body: file={document_file}
```

#### Get Document Sections
```bash
GET http://localhost:8000/api/dataset/document-sections/{file_id}
```

#### Get Document Subsections
```bash
GET http://localhost:8000/api/dataset/document-subsections/{file_id}/{section}
```

#### Generate Dataset
```bash
POST http://localhost:8000/api/dataset/extract-pyqt-style
Content-Type: multipart/form-data
Body:
  file_id={file_id}
  section={section_name}
  subsection={subsection_name}
  working_directory={working_dir_path}
  output_directory={output_dir_path}
```

### Environment Variables Required
```env
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
AZURE_OPENAI_MODEL_NAME=gpt-4  # Optional, defaults to gpt-4
```

### Output File Structure
```json
{
  "references": ["3GPP TS 38.331", "3GPP TS 38.213"],
  "clauses": ["5.2.1.1", "5.2.1.2"],
  "present_references": [...],
  "missing_references": [...],
  "output_file": "path/to/output.json",
  "total_content_file": "path/to/total_content.txt",
  "clause_files_count": 15,
  "files_created": {
    "clause_files": [...],
    "graph_file": "path/to/graph.json"
  }
}
```

---

## Module 2: Test Script Generator

### Overview
Generates automated test scripts in Python or other languages based on datasets extracted from 5G specifications.

### Functionalities
- Generate test scripts from dataset files
- Support multiple programming languages (Python, Java, etc.)
- Use customizable prompt templates
- Refine generated scripts with new prompts
- Save generated scripts to files
- Manage custom prompt templates

### Required Technologies & Libraries
**Backend Dependencies:**
- `openai` (Azure OpenAI) - LLM for script generation
- `python-dotenv` - Environment variable management
- Standard library: `json`, `pathlib`, `datetime`

**Frontend Dependencies:**
- Electron framework
- Fetch API

### Required Files & Paths

#### Input Files
- **Dataset File**: JSON file from Dataset Generator
  - **Path**: `Backend/resources/extract/datasets/`
  - **Format**: `.json` (output from Dataset Generator)
  - **Example**: `5G SA registration and deregistration of single UE_output.json`
- **Reference Code File** (Optional): Existing code for reference
  - **Path**: `Backend/resources/Test Script Generator Input/`
  - **Format**: `.txt` or `.py`
  - **Example**: `Reference_code.txt`

#### Output Files
- **Generated Test Script**: Python or other language file
  - **Path**: `Backend/resources/extract/test_scripts/`
  - **Format**: `.py`, `.java`, etc. (based on selected language)
  - **Example**: `test_5g_attach_procedure.py`

#### Template Files
- **Custom Templates**: `Backend/resources/custom_templates.json`
- **User Saved Templates**: `Backend/resources/user_saved_templates.json`

#### Directory Structure
```
Backend/
├── resources/
│   ├── extract/
│   │   ├── datasets/            # Input: Dataset files from Dataset Generator
│   │   └── test_scripts/        # Output: Generated test scripts
│   ├── Test Script Generator Input/  # Optional: Reference code files
│   ├── custom_templates.json     # System templates
│   └── user_saved_templates.json # User-defined templates
```

### Step-by-Step Usage Instructions

#### Step 1: Ensure Backend and Frontend are Running
- Backend: `http://localhost:8000`
- Frontend: Electron app window open

#### Step 2: Navigate to Test Script Generator
1. Click **"Tasks"** in left sidebar
2. Click **"Launch"** on **"Test Script Generator"** card

#### Step 3: Load Dataset File
1. Click **"Browse"** or **"Select Dataset File"** button
2. Navigate to `Backend/resources/extract/datasets/`
3. Select a dataset JSON file (e.g., `5G SA registration_output.json`)
4. File content loads into the text area

#### Step 4: Select Prompt Template
1. **Template Dropdown**: Select from available templates
   - "Test Script" (default)
   - Custom templates (if saved)
2. **Template Variables** (if applicable):
   - Domain: 5G, LTE, etc.
   - System Type: gNB, UE, etc.
   - Primary Feature: RRC, NAS, etc.
   - Connection Method: SSH, Local, etc.
   - Login Credentials: User credentials
   - Access Mode: Read, Write, etc.
   - Language: Python, Java, etc.

#### Step 5: Configure Variables
1. Fill in template variables if required:
   - **Language**: Select Python, Java, etc.
   - **Domain**: Select 5G, LTE, etc.
   - **System Type**: Select gNB, UE, etc.
   - Other variables as needed

#### Step 6: Generate Test Script
1. Click **"Generate Test Script"** button
2. **Process**:
   - Sends dataset and template to Azure OpenAI
   - Generates test script code
   - Displays generated script in output area
3. **Wait Time**: 30-60 seconds depending on script complexity

#### Step 7: Refine Script (Optional)
1. Enter a new prompt in **"New Prompt"** text area
2. Click **"Generate with New Prompt"** button
3. Script regenerates based on new prompt

#### Step 8: Save Test Script
1. Click **"Save Test Script"** button
2. **File Location**: `Backend/resources/extract/test_scripts/`
3. **Filename**: Auto-generated or user-specified
4. **Format**: Based on selected language (`.py`, `.java`, etc.)

#### Step 9: Save Custom Template (Optional)
1. Modify prompt template as needed
2. Click **"Save Template"** button
3. Enter template name
4. **Saved To**: `Backend/resources/user_saved_templates.json`

### Execution Commands (Backend API)

#### Get Available Templates
```bash
GET http://localhost:8000/api/test-script/templates
```

#### Generate Test Script
```bash
POST http://localhost:8000/api/test-script/generate
Content-Type: application/json
Body:
{
  "prompt_key": "Test Script",
  "text_content": "{dataset_json_content}",
  "variables": {
    "language": "Python",
    "domain": "5G",
    "system_type": "gNB"
  },
  "custom_prompt": null
}
```

#### Refine Script
```bash
POST http://localhost:8000/api/test-script/refine
Content-Type: application/json
Body:
{
  "text_content": "{dataset_content}",
  "new_prompt": "{refinement_prompt}",
  "previous_response": "{previous_generated_script}"
}
```

#### Save Test Script
```bash
POST http://localhost:8000/api/test-script/save
Content-Type: application/json
Body:
{
  "content": "{generated_script_code}",
  "template_type": "Test Script",
  "language": "Python"
}
```

### Environment Variables Required
```env
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
AZURE_OPENAI_API_VERSION=2024-02-01  # Optional
AZURE_OPENAI_MODEL_NAME=gpt-4  # Optional
```

---

## Module 3: Test Deployment

### Overview
Deploy test environments and manage deployment configuration files for 5G RAN testing.

### Functionalities
- Upload deployment configuration files (.cfg format)
- List and manage deployment configs
- View configuration file contents
- Delete configuration files
- Open deployment directories

### Required Technologies & Libraries
**Backend Dependencies:**
- Standard library: `pathlib`, `json`
- FastAPI file handling

**Frontend Dependencies:**
- Electron framework
- File system access (via Electron IPC)

### Required Files & Paths

#### Input Files
- **Deployment Configuration Files**: Configuration files for test deployment
  - **Path**: `Backend/resources/deployment_configs/`
  - **Format**: `.cfg`
  - **Example**: `Simnovus_single_ue.cfg`, `Simnovus_multi_ue.cfg`

#### Directory Structure
```
Backend/
├── resources/
│   └── deployment_configs/      # Deployment configuration files
│       ├── Simnovus_single_ue.cfg
│       └── Simnovus_multi_ue.cfg
```

### Step-by-Step Usage Instructions

#### Step 1: Navigate to Test Deployment
1. Click **"Tasks"** in left sidebar
2. Click **"Launch"** on **"Test Deployment"** card

#### Step 2: Upload Configuration File
1. Click **"Upload Config File"** button
2. Select a `.cfg` file (e.g., `Simnovus_single_ue.cfg`)
3. File uploads to `Backend/resources/deployment_configs/`
4. File appears in the configuration files list

#### Step 3: View Configuration
1. Click on a configuration file name in the list
2. Configuration content displays in the viewer
3. Can edit and save changes (if implemented)

#### Step 4: Delete Configuration (Optional)
1. Select a configuration file
2. Click **"Delete"** button
3. Confirms deletion
4. File removed from `Backend/resources/deployment_configs/`

#### Step 5: Open Deployment Directory
1. Click **"Open Folder"** button
2. Opens `Backend/resources/deployment_configs/` in file explorer

### Execution Commands (Backend API)

#### Upload Configuration File
```bash
POST http://localhost:8000/api/deployment/upload-config
Content-Type: multipart/form-data
Body: file={config_file.cfg}
```

#### List Configuration Files
```bash
GET http://localhost:8000/api/deployment/config-files
```

#### Get Configuration File Content
```bash
GET http://localhost:8000/api/deployment/config-files/{file_id}
```

#### Delete Configuration File
```bash
DELETE http://localhost:8000/api/deployment/config-files/{file_id}
```

#### Open Deployment Directory
```bash
POST http://localhost:8000/api/deployment/open-folder
```

---

## Module 4: Test Execution

### Overview
Execute test scenarios and run automated test scripts generated by the Test Script Generator.

### Functionalities
- Execute test scripts
- Monitor test execution progress
- View test execution logs
- Manage test execution results

### Required Technologies & Libraries
**Backend Dependencies:**
- `subprocess` - For executing test scripts
- Standard library: `pathlib`, `json`

**Frontend Dependencies:**
- Electron framework
- WebSocket or polling for progress updates

### Required Files & Paths

#### Input Files
- **Test Scripts**: Generated test scripts from Test Script Generator
  - **Path**: `Backend/resources/extract/test_scripts/`
  - **Format**: `.py`, `.java`, etc.
  - **Example**: `test_5g_attach_procedure.py`

#### Output Files
- **Test Execution Logs**: Log files from test execution
  - **Path**: `Backend/resources/test_logs/`
  - **Format**: `.log`
  - **Example**: `test_execution_20241202_120000.log`

#### Directory Structure
```
Backend/
├── resources/
│   ├── extract/
│   │   └── test_scripts/        # Input: Test scripts to execute
│   └── test_logs/               # Output: Test execution logs
```

### Step-by-Step Usage Instructions

#### Step 1: Navigate to Test Execution
1. Click **"Tasks"** in left sidebar
2. Click **"Launch"** on **"Test Execution"** card

#### Step 2: Select Test Script
1. Click **"Select Test Script"** button
2. Navigate to `Backend/resources/extract/test_scripts/`
3. Select a test script file (e.g., `test_5g_attach_procedure.py`)

#### Step 3: Configure Execution Parameters
1. **Environment**: Select test environment (if applicable)
2. **Timeout**: Set execution timeout (if applicable)
3. **Output Directory**: Set log output directory (default: `Backend/resources/test_logs/`)

#### Step 4: Execute Test
1. Click **"Execute Test"** button
2. **Process**:
   - Script executes in background
   - Progress updates in real-time
   - Logs stream to output area
3. **Wait Time**: Depends on test script complexity

#### Step 5: View Results
1. **Execution Status**: Success/Failure indicator
2. **Log Output**: Full execution log displayed
3. **Log File**: Saved to `Backend/resources/test_logs/`
4. **Results**: Test results summary (if available)

### Execution Commands (Backend API)

#### Execute Test Script
```bash
POST http://localhost:8000/api/test-execution/run
Content-Type: application/json
Body:
{
  "script_path": "resources/extract/test_scripts/test_5g_attach_procedure.py",
  "timeout": 3600,
  "output_dir": "resources/test_logs"
}
```

#### Get Execution Status
```bash
GET http://localhost:8000/api/test-execution/status/{job_id}
```

#### Get Execution Logs
```bash
GET http://localhost:8000/api/test-execution/logs/{job_id}
```

---

## Module 5: Bug Discovery

### Overview
Analyze test execution logs to discover bugs, perform root cause analysis (RCA), and generate fix suggestions.

### Functionalities
- Upload test execution log files
- Perform root cause analysis (RCA)
- Analyze error patterns
- Identify suspected functions and configurations
- Generate code and config patches
- View investigation steps and recommendations
- Search Git history for similar fixes

### Required Technologies & Libraries
**Backend Dependencies:**
- `CompleteErrorFixingPipeline` - Error fixing pipeline module
- `subprocess` - For executing RCA scripts
- `git` - For Git history search (if available)
- Standard library: `pathlib`, `json`, `re`

**Frontend Dependencies:**
- Electron framework
- File system access

### Required Files & Paths

#### Input Files
- **Log Files**: Test execution log files
  - **Path**: `Backend/resources/rca_logs/`
  - **Format**: `.log`, `.txt`
  - **Example**: `TC_pdcp_integrity_failure_handover_8245.log`, `cu_ngap_failure.log`
- **Source Code Directory**: OpenAirInterface codebase directory
  - **Path**: User-selected directory
  - **Format**: Directory containing source code
  - **Example**: `Backend/app/services/Error_fixing_pipelin/openairinterface5g-develop/`

#### Output Files
- **RCA Analysis Results**: JSON files with analysis results
  - **Path**: `Backend/resources/rca_results/`
  - **Format**: `.rca.json`
  - **Example**: `971c4643-86ee-454d-b2d7-07aefc1f3892_TC_pdcp_integrity_failure_handover_8245.rca.json`
- **Bug Analysis History**: Historical analysis records
  - **Path**: `Backend/resources/bug_history/`
  - **Format**: `.json`
  - **Example**: `bug_analysis_20251202_090538.json`
- **Fix Suggestions**: Generated fix suggestions
  - **Path**: `Backend/app/services/Error_fixing_pipelin/output/`
  - **Format**: `.json`
  - **Example**: `fix_suggestions.json`

#### Directory Structure
```
Backend/
├── resources/
│   ├── rca_logs/                # Input: Test execution log files
│   ├── rca_results/             # Output: RCA analysis results
│   └── bug_history/             # Output: Bug analysis history
├── app/
│   └── services/
│       └── Error_fixing_pipelin/
│           ├── output/          # Output: Fix suggestions
│           └── openairinterface5g-develop/  # Source code directory (if using OAI)
```

### Step-by-Step Usage Instructions

#### Step 1: Navigate to Bug Discovery
1. Click **"Tasks"** in left sidebar
2. Click **"Launch"** on **"Bug Discovery"** card

#### Step 2: Upload Log Files
1. Click **"Load Log Folder"** button or drag-and-drop log files
2. Select log files (`.log` or `.txt` format)
3. **File Location**: Uploaded to `Backend/resources/rca_logs/`
4. Files appear in log file dropdown

#### Step 3: Select Log File
1. Click **"Select Log File"** dropdown
2. Choose a log file from the list
3. Selected file displays in the interface

#### Step 4: Select Source Code Directory
1. Click **"Select Source Code Directory"** button
2. Navigate to source code directory (e.g., OpenAirInterface codebase)
3. **Example Path**: `Backend/app/services/Error_fixing_pipelin/openairinterface5g-develop/`
4. Directory path displays in the interface

#### Step 5: Start RCA Analysis
1. Click **"Start RCA Analysis"** button
2. **Process Flow**:
   - Phase 1: Error Pattern Detection (20% progress)
   - Phase 2: Root Cause Analysis (40% progress)
   - Phase 3: Fix Generation (60% progress)
   - Phase 4: Command Generation (80% progress)
   - Phase 5: Completion (100% progress)
3. **Wait Time**: 2-5 minutes depending on log complexity

#### Step 6: View Analysis Results
1. **Summary Statistics**:
   - Error Type
   - Suspected Functions Count
   - Suspected Configs Count
   - Code Patches Count
   - Config Patches Count
2. **Suspected Functions Table**: List of functions likely causing the issue
3. **Suspected Configurations Table**: List of config parameters to check
4. **Code Patches Table**: Suggested code changes with:
   - Function name
   - File path
   - Patch type
   - Original code
   - Patched code
   - Description
5. **Config Patches Table**: Suggested configuration changes with:
   - Config name
   - File path
   - Current value
   - New value
   - Description
6. **Investigation Steps**: Step-by-step debugging guide
7. **Root Cause Analysis**: Detailed analysis of the issue
8. **Recommendation**: Summary and next steps

#### Step 7: Search Git History (Optional)
1. Click **"Search Git History"** button
2. **Process**:
   - Searches Git commits for similar error fixes
   - Displays matching commits with similarity scores
   - Shows code and config patches from commits
3. **Results**: Similar fixes from Git history displayed

#### Step 8: Save Analysis to History
1. Click **"Save to History"** button
2. **File Location**: `Backend/resources/bug_history/bug_analysis_{timestamp}.json`
3. Analysis saved for future reference

#### Step 9: Load Previous Analysis
1. Click **"Bug History"** dropdown
2. Select a previous analysis
3. Click **"Load Analysis"** button
4. Previous analysis loads with all patches and recommendations

### Execution Commands (Backend API)

#### Upload Log Files
```bash
POST http://localhost:8000/api/rca/upload-logs
Content-Type: multipart/form-data
Body: files={log_file1.log, log_file2.log, ...}
```

#### Start RCA Analysis
```bash
POST http://localhost:8000/api/rca/analyze
Content-Type: application/json
Body:
{
  "log_file_name": "TC_pdcp_integrity_failure_handover_8245.log",
  "code_dir": "Backend/app/services/Error_fixing_pipelin/openairinterface5g-develop/",
  "analysis_type": "error"
}
```

#### Get Bug History
```bash
GET http://localhost:8000/api/rca/bug-history
```

#### Load Bug Analysis
```bash
GET http://localhost:8000/api/rca/bug-history/{analysis_id}
```

### Environment Variables Required
```env
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
```

### Output File Structure (RCA Results)
```json
{
  "error_message": "Segmentation fault in RRC",
  "log_file": "TC_pdcp_integrity_failure_handover_8245.log",
  "log_path": "Backend/resources/rca_logs/...",
  "code_dir": "Backend/app/services/Error_fixing_pipelin/openairinterface5g-develop/",
  "results": {
    "phase1_error_detection": {
      "error_type": "Segmentation Fault",
      "error_pattern": "SIGSEGV"
    },
    "phase2_analysis": {
      "root_cause": "Null pointer dereference",
      "suspected_functions": ["rrc_gNB_process_rrc_setup_request"],
      "suspected_configs": ["max_ue_count"]
    },
    "phase3_fixes": {
      "fix_suggestion": {
        "code_patches": [...],
        "config_patches": [...],
        "fix_strategy": "...",
        "confidence_level": "High"
      }
    },
    "phase4_commands": {
      "terminal_commands": [...]
    }
  }
}
```

---

## Module 6: Code Evaluation

### Overview
Evaluate code changes, test modifications, and assess code quality using multiple evaluation methods.

### Functionalities
- Evaluate code changes against specifications
- Test code modifications
- Assess code quality
- Compare code versions
- Generate evaluation reports

### Required Technologies & Libraries
**Backend Dependencies:**
- `CodeTestingEngine` - Code testing engine
- `SpecReferenceEvaluator` - Specification reference evaluator
- `LLMJudgeEvaluator` - LLM-based code evaluation
- `VariableImpactEvaluator` - Variable impact analysis
- Standard library: `pathlib`, `json`

**Frontend Dependencies:**
- Electron framework

### Required Files & Paths

#### Input Files
- **Code Files**: Modified code files to evaluate
  - **Path**: User-selected directory
  - **Format**: `.c`, `.h`, `.py`, etc.
- **Specification Documents**: Reference specifications
  - **Path**: `Backend/resources/specifications/`
  - **Format**: `.docx`, `.pdf`
- **Test Scripts**: Test scripts for code evaluation
  - **Path**: `Backend/resources/extract/test_scripts/`
  - **Format**: `.py`, etc.

#### Output Files
- **Evaluation Reports**: Evaluation results
  - **Path**: `Backend/resources/outputs/`
  - **Format**: `.json`
  - **Example**: `code_evaluation_20241202_120000.json`

#### Directory Structure
```
Backend/
├── resources/
│   ├── specifications/          # Input: Reference specifications
│   ├── extract/
│   │   └── test_scripts/         # Input: Test scripts
│   └── outputs/                 # Output: Evaluation reports
```

### Step-by-Step Usage Instructions

#### Step 1: Navigate to Code Evaluation
1. Click **"Tasks"** in left sidebar
2. Click **"Launch"** on **"Code Evaluation"** card

#### Step 2: Select Code Directory
1. Click **"Select Code Directory"** button
2. Navigate to directory containing code files to evaluate
3. Directory path displays in the interface

#### Step 3: Select Evaluation Method
1. **Specification Reference Evaluation**: Compare code against specifications
2. **LLM Judge Evaluation**: Use LLM to evaluate code quality
3. **Variable Impact Evaluation**: Analyze variable impact on code
4. **Code Testing**: Run tests on code

#### Step 4: Configure Evaluation Parameters
1. **Specification File**: Select reference specification (if using spec evaluation)
2. **Test Script**: Select test script (if using code testing)
3. **Evaluation Criteria**: Set evaluation criteria
4. **Output Directory**: Set output directory (default: `Backend/resources/outputs/`)

#### Step 5: Run Evaluation
1. Click **"Run Evaluation"** button
2. **Process**:
   - Code files analyzed
   - Evaluations performed based on selected method
   - Results generated
3. **Wait Time**: 1-3 minutes depending on code size

#### Step 6: View Evaluation Results
1. **Evaluation Summary**: Overall evaluation score
2. **Detailed Results**: Per-file evaluation results
3. **Recommendations**: Suggestions for improvement
4. **Report**: Full evaluation report

#### Step 7: Save Evaluation Report
1. Click **"Save Report"** button
2. **File Location**: `Backend/resources/outputs/`
3. **Filename**: Auto-generated with timestamp

### Execution Commands (Backend API)

#### Run Code Evaluation
```bash
POST http://localhost:8000/api/code-evaluation/evaluate
Content-Type: application/json
Body:
{
  "code_dir": "path/to/code/directory",
  "evaluation_type": "spec_reference",
  "spec_file": "path/to/specification.docx",
  "test_script": "path/to/test_script.py"
}
```

#### Get Evaluation Results
```bash
GET http://localhost:8000/api/code-evaluation/results/{evaluation_id}
```

### Environment Variables Required
```env
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
```

---

## Module 7: Code Assistant

### Overview
Review and apply code patches generated from Bug Discovery analysis. Provides interface to select, preview, and apply fixes.

### Functionalities
- Load bug analysis from history
- View code and config patches
- Preview patch details
- Select/deselect patches
- Apply selected patches to codebase
- View patch application results

### Required Technologies & Libraries
**Backend Dependencies:**
- `UnifiedPatchApplicator` - Patch application engine
- `CompleteErrorFixingPipeline` - Error fixing pipeline
- Standard library: `pathlib`, `json`

**Frontend Dependencies:**
- Electron framework
- File system access

### Required Files & Paths

#### Input Files
- **Bug Analysis History**: Previous bug analysis results
  - **Path**: `Backend/resources/bug_history/`
  - **Format**: `.json`
  - **Example**: `bug_analysis_20251202_090538.json`
- **Fix Suggestions**: Generated fix suggestions
  - **Path**: `Backend/app/services/Error_fixing_pipelin/output/`
  - **Format**: `.json`
  - **Example**: `fix_suggestions.json`

#### Output Files
- **Applied Patches**: Backup and applied patch files
  - **Path**: Source code directory (with `.backup` extensions)
  - **Format**: Original file format with `.backup` suffix
- **Patch Application Log**: Log of applied patches
  - **Path**: `Backend/resources/log_files/`
  - **Format**: `.log`

#### Directory Structure
```
Backend/
├── resources/
│   ├── bug_history/             # Input: Bug analysis history
│   └── log_files/               # Output: Patch application logs
├── app/
│   └── services/
│       └── Error_fixing_pipelin/
│           └── output/          # Input: Fix suggestions
```

### Step-by-Step Usage Instructions

#### Step 1: Navigate to Code Assistant
1. Click **"Tasks"** in left sidebar
2. Click **"Launch"** on **"Code Assistant"** card

#### Step 2: Load Bug Analysis
1. Click **"Bug History"** dropdown
2. Select a previous bug analysis from the list
3. Click **"Load Analysis"** button
4. **Process**:
   - Analysis loads from `Backend/resources/bug_history/`
   - Code patches and config patches extracted
   - Patches displayed in checkboxes

#### Step 3: Review Patches
1. **Code Patches Section**:
   - List of code patches with checkboxes
   - Each patch shows:
     - Function name
     - File path
     - Patch type
     - Description
2. **Config Patches Section**:
   - List of config patches with checkboxes
   - Each patch shows:
     - Config name
     - File path
     - Current value
     - New value
     - Description

#### Step 4: Select Patches
1. **Individual Selection**: Check/uncheck individual patches
2. **Select All**: Click **"Select All"** button to select all patches
3. **Unselect All**: Click **"Unselect All"** button to deselect all patches

#### Step 5: Preview Patch Details
1. Click on a patch in the list
2. **Patch Preview** displays:
   - Original code (red, with `-` prefix)
   - Patched code (green, with `+` prefix)
   - File path and line numbers
   - Description and confidence level

#### Step 6: Apply Patches
1. Ensure desired patches are selected
2. Click **"Apply Selected Patches"** button
3. **Process**:
   - Creates backup files (`.backup` extension)
   - Applies patches to source files
   - Generates application log
4. **Wait Time**: 10-30 seconds depending on number of patches

#### Step 7: View Application Results
1. **Success Message**: Confirmation of applied patches
2. **Applied Patches List**: List of successfully applied patches
3. **Failed Patches List**: List of patches that failed (if any)
4. **Backup Files**: Original files saved with `.backup` extension

#### Step 8: Run Investigation (Optional)
1. Click **"Run Investigation"** button
2. **Process**:
   - Runs additional analysis on applied patches
   - Generates investigation report
3. **Results**: Investigation findings displayed

### Execution Commands (Backend API)

#### Load Bug Analysis
```bash
GET http://localhost:8000/api/code-assistant/load-analysis/{analysis_id}
```

#### Apply Patches
```bash
POST http://localhost:8000/api/code-assistant/apply-patches
Content-Type: application/json
Body:
{
  "analysis_id": "bug_analysis_20251202_090538",
  "selected_code_patches": [0, 1, 2],
  "selected_config_patches": [0, 1],
  "code_dir": "path/to/source/code"
}
```

#### Run Investigation
```bash
POST http://localhost:8000/api/code-assistant/run-investigation
Content-Type: application/json
Body:
{
  "analysis_id": "bug_analysis_20251202_090538",
  "code_dir": "path/to/source/code"
}
```

### Environment Variables Required
```env
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
```

---

## Module 8: Error Fixing

### Overview
Comprehensive error fixing pipeline that combines error detection, root cause analysis, and fix generation in a unified workflow.

### Functionalities
- Error pattern detection
- Root cause analysis
- Fix suggestion generation
- Context-aware retrieval
- Git history search for similar fixes
- Patch generation and application

### Required Technologies & Libraries
**Backend Dependencies:**
- `CompleteErrorFixingPipeline` - Main error fixing pipeline
- `context_aware_retrieval` - Context-aware fix retrieval
- `crash_phase2_grading` - Crash analysis grading
- `crash_phase3_fix_generation` - Crash fix generation
- `smart_commit_selector` - Git commit selection
- `unified_patch_applicator` - Patch application
- `faiss-cpu` - Vector similarity search
- `sentence-transformers` - Embedding generation
- `torch` - Deep learning framework

**Frontend Dependencies:**
- Electron framework

### Required Files & Paths

#### Input Files
- **Log Files**: Error log files
  - **Path**: `Backend/app/services/Error_fixing_pipelin/log_files/`
  - **Format**: `.log`
  - **Example**: `segmentation_fault.log`, `cu_ngap_failure.log`
- **Source Code Directory**: Codebase to fix
  - **Path**: User-selected or default OAI directory
  - **Format**: Directory containing source code
- **Function Database**: Function call database
  - **Path**: `Backend/app/services/Error_fixing_pipelin/database/`
  - **Format**: `.json`
  - **Example**: `function_calls.json`
- **Error Patterns**: Error pattern database
  - **Path**: `Backend/app/services/Error_fixing_pipelin/database/`
  - **Format**: `.json`
  - **Example**: `error_patterns_enhanced.json`

#### Output Files
- **Fix Suggestions**: Generated fix suggestions
  - **Path**: `Backend/app/services/Error_fixing_pipelin/output/`
  - **Format**: `.json`
  - **Example**: `fix_suggestions.json`
- **FAISS Indices**: Vector search indices
  - **Path**: `Backend/app/services/Error_fixing_pipelin/faiss_indices/`
  - **Format**: `.faiss`, `.json`
- **Embeddings**: Code and function embeddings
  - **Path**: `Backend/app/services/Error_fixing_pipelin/resources/embeddings/`
  - **Format**: `.npy`, `.json`

#### Directory Structure
```
Backend/
├── app/
│   └── services/
│       └── Error_fixing_pipelin/
│           ├── database/        # Input: Function and error pattern databases
│           ├── faiss_indices/  # Output: Vector search indices
│           ├── log_files/       # Input: Error log files
│           ├── output/         # Output: Fix suggestions
│           ├── resources/      # Output: Embeddings and resources
│           └── openairinterface5g-develop/  # Source code directory
```

### Step-by-Step Usage Instructions

#### Step 1: Navigate to Error Fixing
1. Click **"Error Fixing"** in left sidebar (or from Tasks)
2. Error Fixing interface opens

#### Step 2: Upload Log File
1. Click **"Upload Log File"** button
2. Select error log file (`.log` format)
3. **File Location**: `Backend/app/services/Error_fixing_pipelin/log_files/`
4. Log file content displays

#### Step 3: Select Source Code Directory
1. Click **"Select Code Directory"** button
2. Navigate to source code directory
3. **Default**: `Backend/app/services/Error_fixing_pipelin/openairinterface5g-develop/`
4. Directory path displays

#### Step 4: Configure Analysis Options
1. **Analysis Type**: Select analysis type
   - Error analysis
   - Function analysis
   - Impact analysis
   - Knowledge transfer
   - AI-assisted
2. **Options**:
   - Enable crash analysis (if applicable)
   - Enable Git history search
   - Set confidence threshold

#### Step 5: Run Error Fixing Pipeline
1. Click **"Run Error Fixing"** button
2. **Process Flow**:
   - Phase 1: Error Detection (20% progress)
   - Phase 2: Context Retrieval (40% progress)
   - Phase 3: Fix Generation (60% progress)
   - Phase 4: Git History Search (80% progress)
   - Phase 5: Patch Generation (90% progress)
   - Phase 6: Completion (100% progress)
3. **Wait Time**: 3-10 minutes depending on complexity

#### Step 6: View Fix Suggestions
1. **Error Summary**: Error type and description
2. **Root Cause**: Identified root cause
3. **Code Patches**: Suggested code changes
4. **Config Patches**: Suggested configuration changes
5. **Git Matches**: Similar fixes from Git history
6. **Confidence Scores**: Confidence levels for each fix

#### Step 7: Apply Fixes
1. Review suggested fixes
2. Select fixes to apply
3. Click **"Apply Fixes"** button
4. **Process**:
   - Creates backup files
   - Applies patches
   - Generates application log
5. **Results**: Applied fixes confirmation

#### Step 8: Update Embeddings (Optional)
1. Click **"Update Embeddings"** button
2. **Process**:
   - Regenerates code embeddings
   - Updates FAISS indices
   - Improves future fix suggestions
3. **Wait Time**: 5-15 minutes depending on codebase size

### Execution Commands (Backend API)

#### Run Error Fixing Pipeline
```bash
POST http://localhost:8000/api/error-fixing/run
Content-Type: application/json
Body:
{
  "log_file": "segmentation_fault.log",
  "code_dir": "Backend/app/services/Error_fixing_pipelin/openairinterface5g-develop/",
  "analysis_type": "error",
  "enable_crash_analysis": true,
  "enable_git_search": true
}
```

#### Get Fix Suggestions
```bash
GET http://localhost:8000/api/error-fixing/suggestions/{job_id}
```

#### Apply Fixes
```bash
POST http://localhost:8000/api/error-fixing/apply
Content-Type: application/json
Body:
{
  "job_id": "fix_job_uuid",
  "selected_patches": [0, 1, 2],
  "code_dir": "path/to/source/code"
}
```

#### Update Embeddings
```bash
POST http://localhost:8000/api/error-fixing/update-embeddings
Content-Type: application/json
Body:
{
  "code_dir": "path/to/source/code"
}
```

### Environment Variables Required
```env
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
```

### Database Files Required
- `function_calls.json` - Function call database
- `error_patterns_enhanced.json` - Error pattern database
- `functions.json` - Function definitions
- FAISS indices (auto-generated)

---

## General Notes

### Common Paths Summary

#### Input Paths
- **Documents**: `Backend/resources/uploaded_docs/`
- **Datasets**: `Backend/resources/extract/datasets/`
- **Log Files**: `Backend/resources/rca_logs/` or `Backend/app/services/Error_fixing_pipelin/log_files/`
- **Source Code**: User-selected or `Backend/app/services/Error_fixing_pipelin/openairinterface5g-develop/`
- **Config Files**: `Backend/resources/deployment_configs/`

#### Output Paths
- **Datasets**: `Backend/resources/extract/datasets/`
- **Test Scripts**: `Backend/resources/extract/test_scripts/`
- **RCA Results**: `Backend/resources/rca_results/`
- **Bug History**: `Backend/resources/bug_history/`
- **Fix Suggestions**: `Backend/app/services/Error_fixing_pipelin/output/`
- **Evaluation Reports**: `Backend/resources/outputs/`
- **Log Files**: `Backend/resources/log_files/` or `Backend/resources/test_logs/`

### Environment Variables (All Modules)
```env
# Required for all modules using LLM
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint

# Optional
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_MODEL_NAME=gpt-4
GOOGLE_API_KEY=your_google_api_key  # For Gemini features (if used)
```

### Common Dependencies (All Modules)
- Python 3.8+
- Node.js 16+
- Electron 38.2.0+
- FastAPI
- Uvicorn
- All packages from `Backend/requirements.txt`

### Troubleshooting

#### Module Not Loading
- Check backend is running on `http://localhost:8000`
- Verify environment variables are set
- Check file paths exist

#### File Upload Fails
- Verify file permissions
- Check disk space
- Ensure file format is supported

#### Analysis Takes Too Long
- Check log file size (large files take longer)
- Verify API keys are valid
- Check network connectivity (for API calls)

#### Patches Not Applying
- Verify source code directory is correct
- Check file permissions
- Ensure backup files can be created

---

**Last Updated**: Based on application version 1.0.0

