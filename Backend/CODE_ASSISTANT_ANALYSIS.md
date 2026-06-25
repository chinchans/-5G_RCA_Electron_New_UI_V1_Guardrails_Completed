# Code Assistant 'Load Analysis' Functionality Analysis

## Overview
This document analyzes the PyQt UI_v3.py Code Assistant implementation to understand what should appear in the "Load Analysis" dropdown and its dependencies.

## 1. Dropdown Content Structure (`load_bug_history`)

### Location
- **History Directory**: `backend/resources/bug_history` (relative to project root)
- **File Pattern**: `bug_analysis_YYYYMMDD_HHMMSS.json`

### Dropdown Entry Format
Each entry in the dropdown displays:
```
[YYYY-MM-DD HH:MM] Error message (truncated to 100 chars)... [Code:X, Config:Y]
```

### Data Structure in Each History File
Each `bug_analysis_*.json` file contains:

```json
{
  "error_message": "Error text here",
  "log_file": "log_file_name.log",
  "log_path": "/path/to/log/file",
  "code_dir": "/path/to/openairinterface5g-develop",
  "timestamp": "2024-01-15T10:30:00",
  "results": {
    "phase3_fixes": {
      "fix_suggestion": {
        "code_patches": [...],
        "config_patches": [...],
        "suspected_functions": [...],
        "suspected_configs": [...],
        "reason": "...",
        "config_fix": "..."
      }
    },
    "phase4_commands": {
      "terminal_commands": [
        {
          "command": "command_string",
          "explanation": "explanation_text"
        }
      ]
    }
  },
  "history_file": "/path/to/bug_analysis_YYYYMMDD_HHMMSS.json"
}
```

## 2. What Happens on "Load Analysis" (`load_selected_bug_analysis`)

### Step 1: Load File
- Reads the selected JSON file from `bug_history_map`
- Stores in `self.loaded_bug_analysis`

### Step 2: Display Error Details
**Format:**
```
Error Message:
{error_message}

Log File: {log_file}
Timestamp: {timestamp}
```

### Step 3: Extract and Display Patches

#### Code Patches Structure:
Each code patch contains:
- `function_name` - Function to patch
- `file_path` - Full path to source file
- `patch_type` - Type of patch (modification, insertion, etc.)
- `line_number` or `line_numbers` - Line location info
- `description` - Patch description
- `original_code` - Original code to replace
- `suggested_code` or `patched_code` or `new_code` - Suggested fix
- Display format: `{function_name} ({file_name})` as checkbox text

#### Config Patches Structure:
Each config patch contains:
- `config_name` or `parameter_name` - Config parameter name
- `file_path` - Full path to config file
- `description` - Patch description
- `current_value` - Current config value
- `suggested_value` or `new_value` or `recommended_value` - Suggested value
- `line_number` or `line_numbers` - Line location info
- `reasoning` (optional) - Why this change is needed
- Display format: `{config_name} ({file_name})` as checkbox text

### Step 4: Save fix_suggestions.json
**Called**: `save_fix_suggestions_from_loaded_analysis(data)`

**Creates**: `backend/resources/fix_suggestions_YYYYMMDD_HHMMSS.json`

**Structure:**
```json
{
  "code_dir": "/path/to/codebase",
  "code_patches": [...],
  "config_patches": [...]
}
```

**Purpose**: Used by `apply_selected_patches` to apply patches via `UnifiedPatchApplicator`

### Step 5: Update Patch Preview
**Called**: `update_patch_preview()`

**Shows**:
- Selected code patches with:
  - Function name, file path, patch type, line info, description
  - Original code (red background)
  - Suggested code (green background, editable)
- Selected config patches with:
  - Config name, file path, description, line info
  - Current value (red)
  - Suggested value (green, editable)

## 3. Dependencies

### Required Files/Directories:

1. **History Files**
   - Location: `backend/resources/bug_history/`
   - Pattern: `bug_analysis_*.json`
   - Must be saved by Bug Discovery (`save_bug_analysis_to_history`)

2. **UnifiedPatchApplicator**
   - Location: `Error_fixing_pipelin/unified_patch_applicator.py`
   - Used for: Applying code and config patches
   - Requires: `fix_suggestions.json` file with structure:
     ```json
     {
       "code_dir": "...",
       "code_patches": [...],
       "config_patches": [...]
     }
     ```

3. **fix_suggestions.json**
   - Created when analysis is loaded
   - Location: `backend/resources/fix_suggestions_*.json`
   - Required for patch application
   - Must contain `code_dir` for patch applicator to work

4. **Code Directory (code_dir)**
   - Stored in analysis file: `data.code_dir`
   - Required for:
     - Determining `openair_codebase_file_name`
     - Patch application (UnifiedPatchApplicator needs it)
   - Example: `/path/to/openairinterface5g-develop`

### Data Flow Dependencies:

1. **Bug Discovery → History File**
   - Bug Discovery saves analysis via `save_bug_analysis_to_history()`
   - Saves to: `backend/resources/bug_history/bug_analysis_YYYYMMDD_HHMMSS.json`
   - Must include:
     - `error_message`
     - `log_file`, `log_path`
     - `code_dir`
     - `results.phase3_fixes.fix_suggestion` with patches
     - `results.phase4_commands.terminal_commands` (optional)

2. **History File → Code Assistant**
   - Code Assistant loads via `load_selected_bug_analysis()`
   - Extracts patches from `results.phase3_fixes.fix_suggestion`
   - Creates checkboxes for patches
   - Saves temporary `fix_suggestions.json`

3. **Code Assistant → Patch Application**
   - User selects patches via checkboxes
   - Creates filtered `fix_suggestions.json` with only selected patches
   - Calls `UnifiedPatchApplicator(filtered_file).apply_all_patches()`
   - Uses `code_dir` from loaded analysis

## 4. Key Data Structures

### Code Patch Structure:
```python
{
  "function_name": "function_name",
  "file_path": "openairinterface5g-develop/path/to/file.c",
  "patch_type": "modification" | "targeted_insertion_or_adjustment" | etc,
  "line_number": "123" or "after line containing \"...\"",
  "line_numbers": "123-125",
  "description": "Patch description",
  "original_code": "original code block",
  "suggested_code": "new code block",  # or "patched_code" or "new_code"
}
```

### Config Patch Structure:
```python
{
  "config_name": "CONFIG_PARAMETER",  # or "parameter_name"
  "file_path": "openairinterface5g-develop/path/to/config.conf",
  "description": "Config description",
  "current_value": "current_value",
  "suggested_value": "new_value",  # or "new_value" or "recommended_value"
  "line_number": "43",
  "reasoning": "Why this change is needed"  # optional
}
```

### Terminal Commands Structure:
```python
[
  {
    "command": "terminal_command_string",
    "explanation": "What this command does"
  }
]
```

## 5. Critical Requirements

1. **History Files Must Exist**
   - Saved by Bug Discovery after RCA analysis
   - Located in `backend/resources/bug_history/`

2. **Patch Data Must Be Complete**
   - `code_patches` and `config_patches` arrays must exist in `results.phase3_fixes.fix_suggestion`
   - Each patch must have required fields (function_name, file_path for code; config_name, file_path for config)

3. **Code Directory Must Be Present**
   - Stored in `data.code_dir`
   - Used to determine codebase name and for patch application
   - Must be a valid path to OpenAirInterface codebase

4. **fix_suggestions.json Creation**
   - Created on load via `save_fix_suggestions_from_loaded_analysis()`
   - Must include `code_dir` for patch applicator

5. **Terminal Commands (Optional)**
   - Stored in `results.phase4_commands.terminal_commands`
   - Used by "Run Investigation Commands" feature
   - Array of command objects with `command` and `explanation`

## 6. Display Format Details

### Dropdown Entry:
- Format: `[YYYY-MM-DD HH:MM] Error message (first 100 chars)... [Code:X, Config:Y]`
- Example: `[2024-01-15 10:30] No AMF is associated to the gNB... [Code:2, Config:2]`
- Mapping: `bug_history_map[display_text] = file_path`

### Error Details Display:
```
Error Message:
{error_message}

Log File: {log_file}
Timestamp: {timestamp}
```

### Patch Checkboxes:
- Code: `{function_name} ({basename(file_path)})`
- Config: `{config_name} ({basename(file_path)})`
- Tooltip: `File: {file_path}\nDescription: {description}`
- Default: All checked = True

### Patch Preview:
- Shows selected patches with full details
- Original code (red) and suggested code (green, editable)
- Current config value (red) and suggested value (green, editable)

## 7. File Path Dependencies

1. **History Directory**: `backend/resources/bug_history/`
2. **Fix Suggestions**: `backend/resources/fix_suggestions_*.json`
3. **Patch Applicator**: `Error_fixing_pipelin/unified_patch_applicator.py`
4. **Codebase**: Path stored in `code_dir` field

## 8. Function Call Chain

```
load_bug_history()
  └─> Reads bug_history/*.json files
  └─> Creates dropdown entries with patch counts
  └─> Stores mapping: bug_history_map[display_text] = file_path

load_selected_bug_analysis()
  └─> Loads JSON file from bug_history_map
  └─> Extracts: error_message, log_file, timestamp, code_dir
  └─> Extracts: code_patches, config_patches from results.phase3_fixes.fix_suggestion
  └─> Creates checkboxes for patches
  └─> save_fix_suggestions_from_loaded_analysis() → creates fix_suggestions.json
  └─> update_patch_preview() → shows selected patches

apply_selected_patches()
  └─> Gets selected patches from checkboxes
  └─> Creates filtered fix_suggestions.json
  └─> UnifiedPatchApplicator(filtered_file).apply_all_patches()
  └─> Requires: code_dir, filtered patches

run_code_terminal_commands()
  └─> Gets terminal_commands from results.phase4_commands.terminal_commands
  └─> Executes commands via subprocess
```

## 9. Summary

**What Should Appear in Dropdown:**
- List of bug analysis files from `backend/resources/bug_history/`
- Format: `[Timestamp] Error message... [Code:X, Config:Y]`
- Sorted by newest first (by filename timestamp)

**What Happens on Load:**
1. Error details displayed
2. Code patches shown as checkboxes
3. Config patches shown as checkboxes
4. fix_suggestions.json created for patch application
5. Patch preview updated

**Key Dependencies:**
1. Bug history files exist in `backend/resources/bug_history/`
2. Files contain complete `results.phase3_fixes.fix_suggestion` structure
3. `code_dir` field present in history file
4. `UnifiedPatchApplicator` available for patch application
5. `fix_suggestions.json` created on load (temporary file)

