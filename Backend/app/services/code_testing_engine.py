"""Code Testing engine to run validation layers outside of UI code."""

import difflib
import os
import re
import shutil
import subprocess
import tempfile
import json
from pathlib import Path
from dataclasses import asdict
from typing import Dict, List, Optional, Sequence, Tuple, Set, Any

# Try relative import first (for FastAPI), then fallback to absolute (for PyQt)
try:
    from .variable_impact_evaluator import VariableImpactEvaluator, VariableImpactResult, VariableChange
except ImportError:
    # Fallback for PyQt UI which may have different import context
    from variable_impact_evaluator import VariableImpactEvaluator, VariableImpactResult, VariableChange

class CodeTestingEngine:
    """Encapsulates non-UI logic for code testing layers."""

    def __init__(self) -> None:
        self._compiler_cache: Optional[Dict[str, Optional[str]]] = None
        self._cppcheck_path: Optional[str] = None
        self._config = self._load_config()
        self._function_db_loaded = False
        self._functions_by_name: Dict[str, List[Dict[str, Any]]] = {}
        self._functions_by_file: Dict[str, List[Dict[str, Any]]] = {}
        self._call_graph_loaded = False
        self._call_graph_index: Dict[str, Dict[str, Any]] = {}
        self._variable_impact_evaluator = VariableImpactEvaluator()

    def run_layer1_syntax_validation(
        self,
        patches: Sequence[Dict],
        code_dir: Optional[str] = None,
        *,
        config_patches: Optional[Sequence[Dict]] = None,
    ) -> List[str]:
        """Run syntax and structural validation for selected code/config patches."""

        results: List[str] = ["Layer 1: Syntax & Structural Validation"]

        total_passed = 0
        total_failed = 0
        total_skipped = 0

        has_code_patches = bool(patches)
        code_summary_label = "cppcheck primary"

        if has_code_patches:
            cppcheck_path = self._get_cppcheck_path()
            if cppcheck_path:
                code_lines, (code_passed, code_failed, code_skipped) = self._run_primary_cppcheck(
                    cppcheck_path,
                    patches,
                    code_dir,
                )
            else:
                results.append("  ⚠️ cppcheck not available; attempting clang-based validation.")
                code_lines, (code_passed, code_failed, code_skipped) = self._run_clang_validation(
                    patches,
                    code_dir,
                )

            results.extend(code_lines)
            if code_lines and code_lines[-1] != "":
                results.append("")

            results.append(
                f"  Summary (Code): {code_passed} passed, {code_failed} failed, {code_skipped} skipped ({code_summary_label})."
            )
            results.append("")
        else:
            code_passed = code_failed = code_skipped = 0
            results.append("  ⚠️ No code patches selected – skipping syntax validation.")
            results.append("")

        total_passed += code_passed
        total_failed += code_failed
        total_skipped += code_skipped

        config_patches = tuple(config_patches or [])
        has_config_patches = bool(config_patches)

        if has_config_patches:
            config_lines, (config_passed, config_failed, config_skipped) = self._run_config_patch_validation(
                config_patches,
                code_dir,
            )
            results.extend(config_lines)
            results.append("")
            results.append(
                f"  Summary (Config): {config_passed} passed, {config_failed} failed, {config_skipped} skipped."
            )
            results.append("")

            total_passed += config_passed
            total_failed += config_failed
            total_skipped += config_skipped

        total_items = total_passed + total_failed + total_skipped
        if total_items:
            results.append(
                "  Overall Summary: "
                f"{total_passed} passed, {total_failed} failed, {total_skipped} skipped (total {total_items})."
            )

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_primary_cppcheck(
        self,
        cppcheck_path: str,
        patches: Sequence[Dict],
        code_dir: Optional[str],
    ) -> Tuple[List[str], Tuple[int, int, int]]:
        """Run cppcheck on the patched files as the primary validation step."""

        results: List[str] = []
        results.append("  ⚙️ Running cppcheck (primary validation).")

        if not code_dir:
            failure_count = len(tuple(patches))
            results.append(
                "  ❌ Original code directory missing in analysis data. Cannot run cppcheck."
            )
            return results, (0, failure_count, 0)

        temp_root = tempfile.mkdtemp(prefix="code_testing_cppcheck_")
        success_count = 0
        failure_count = 0
        skipped_count = 0

        try:
            for index, patch in enumerate(patches, start=1):
                patch_label = (
                    patch.get("function_name")
                    or patch.get("file_path")
                    or f"Patch {index}"
                )
                results.append(f"  → {patch_label}")

                prepared = self._prepare_temp_file_for_patch(patch, temp_root, code_dir)
                if not prepared["success"]:
                    if prepared["status"] == "error":
                        failure_count += 1
                        prefix = "    ❌"
                    else:
                        skipped_count += 1
                        prefix = "    ⚠️"
                    results.append(f"{prefix} {prepared['message']}")
                    continue

                if self._run_cppcheck(
                    cppcheck_path,
                    prepared["temp_file"],
                    patch,
                    code_dir,
                    prepared.get("original_dir"),
                    results,
                    timeout=180,
                ):
                    success_count += 1
                    continue

                failure_count += 1

        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

        return results, (success_count, failure_count, skipped_count)

    def _run_clang_validation(
        self,
        patches: Sequence[Dict],
        code_dir: Optional[str],
    ) -> Tuple[List[str], Tuple[int, int, int]]:
        """Run clang-based validation (legacy path)."""

        results: List[str] = []

        compilers = self._detect_clang_compilers()
        if compilers is None:
            results.append(
                "  ❌ Unable to locate clang/clang++ compilers. Install LLVM clang to enable syntax checks."
            )
            return results, (0, len(tuple(patches)), 0)

        if not code_dir:
            results.append(
                "  ❌ Original code directory missing in analysis data. Cannot apply patches for validation."
            )
            return results, (0, len(tuple(patches)), 0)

        temp_root = tempfile.mkdtemp(prefix="code_testing_layer1_")
        success_count = 0
        failure_count = 0
        skipped_count = 0

        try:
            for index, patch in enumerate(patches, start=1):
                patch_label = (
                    patch.get("function_name")
                    or patch.get("file_path")
                    or f"Patch {index}"
                )
                results.append(f"  → {patch_label}")

                prepared = self._prepare_temp_file_for_patch(patch, temp_root, code_dir)
                if not prepared["success"]:
                    if prepared["status"] == "error":
                        failure_count += 1
                        prefix = "    ❌"
                    else:
                        skipped_count += 1
                        prefix = "    ⚠️"
                    results.append(f"{prefix} {prepared['message']}")
                    continue

                compiler_cmd = self._build_clang_command(
                    prepared["temp_file"],
                    patch,
                    compilers,
                    code_dir,
                    prepared.get("original_dir"),
                )
                if compiler_cmd is None:
                    skipped_count += 1
                    results.append("    ⚠️ Unsupported file extension – skipped syntax validation.")
                    continue

                try:
                    completed = subprocess.run(
                        compiler_cmd,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                except subprocess.TimeoutExpired:
                    failure_count += 1
                    results.append("    ❌ Syntax check timed out after 60 seconds.")
                    continue
                except Exception as exc:  # pylint: disable=broad-except
                    failure_count += 1
                    results.append(f"    ❌ Failed to execute compiler: {exc}")
                    continue

                if completed.returncode == 0:
                    success_count += 1
                    results.append("    ✅ Syntax check passed.")
                else:
                    failure_count += 1
                    header_missing = self._report_compiler_failure(
                        results,
                        completed.stdout or "",
                        completed.stderr or "",
                        completed.returncode,
                    )
                    if header_missing:
                        cppcheck_path = self._get_cppcheck_path()
                        if cppcheck_path:
                            if self._run_cppcheck(
                                cppcheck_path,
                                prepared["temp_file"],
                                patch,
                                code_dir,
                                prepared.get("original_dir"),
                                results,
                                timeout=120,
                            ):
                                success_count += 1
                                failure_count -= 1
                                results.append(
                                    "    ✅ Fallback cppcheck passed (missing header bypassed)."
                                )
                                continue
                        else:
                            results.append(
                                "    ⚠️ cppcheck not available. Install cppcheck to enable fallback analysis."
                            )

        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

        return results, (success_count, failure_count, skipped_count)

    def _detect_clang_compilers(self) -> Optional[Dict[str, Optional[str]]]:
        """Locate clang and clang++ compilers on the system (cached)."""

        if self._compiler_cache is not None:
            return self._compiler_cache

        clang_c = shutil.which("clang") or shutil.which("clang.exe")
        clang_cpp = shutil.which("clang++") or shutil.which("clang++.exe") or clang_c

        if not clang_c and not clang_cpp:
            self._compiler_cache = None
            return None

        self._compiler_cache = {"c": clang_c or clang_cpp, "cpp": clang_cpp or clang_c}
        return self._compiler_cache

    def _prepare_temp_file_for_patch(
        self, patch: Dict, temp_root: str, code_dir: str
    ) -> Dict[str, Optional[str]]:
        """Apply a patch to a temporary copy of the target file."""

        response: Dict[str, Optional[str]] = {
            "success": False,
            "message": None,
            "temp_file": None,
            "status": "error",
        }

        file_path = patch.get("file_path")
        if not file_path:
            response["message"] = "Patch is missing 'file_path' information."
            return response

        resolved_path = self._resolve_patch_path(file_path, code_dir)
        if resolved_path is None:
            response["message"] = "File path could not be resolved."
            return response

        abs_path = resolved_path

        if not abs_path.exists():
            response["message"] = f"File not found: {abs_path}"
            return response

        try:
            with abs_path.open("r", encoding="utf-8") as source_file:
                original_text = source_file.read()
        except Exception as exc:  # pylint: disable=broad-except
            response["message"] = f"Unable to read original file: {exc}"
            return response

        patched_content, error_message, status = self._generate_patched_content(
            original_text, patch
        )
        if patched_content is None:
            response["message"] = error_message or "Unable to generate patched file content."
            response["status"] = status or "error"
            return response

        if code_dir:
            code_root = Path(code_dir)
            try:
                relative_path = abs_path.relative_to(code_root)
            except ValueError:
                relative_path = Path(abs_path.name)
        else:
            relative_path = Path(abs_path.name)

        temp_file_path = Path(temp_root).joinpath(relative_path)
        temp_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with temp_file_path.open("w", encoding="utf-8") as temp_file:
                temp_file.write(patched_content)
        except Exception as exc:  # pylint: disable=broad-except
            response["message"] = f"Failed to write temporary file: {exc}"
            return response

        response.update(
            {
                "success": True,
                "message": "Temporary file prepared successfully.",
                "temp_file": temp_file_path,
                "status": "ok",
                "original_dir": abs_path.parent,
            }
        )
        return response

    def _generate_patched_content(
        self, original_text: str, patch: Dict
    ) -> Tuple[Optional[str], Optional[str], str]:
        """Generate patched file content using patch metadata."""

        return self._apply_patch_text(original_text, patch)

    def _apply_patch_text(
        self,
        base_text: str,
        patch: Dict,
    ) -> Tuple[Optional[str], Optional[str], str]:
        """Apply a patch description to a block of text using multiple strategies."""

        new_code = patch.get("suggested_code") or patch.get("patched_code") or patch.get("new_code")
        if not new_code:
            return None, "Patch is missing new code content.", "skip"

        original_code = patch.get("original_code") or patch.get("existing_code")
        original_not_found_message: Optional[str] = None

        if original_code:
            if original_code in base_text:
                return base_text.replace(original_code, new_code, 1), None, "ok"

            stripped_original = original_code.strip()
            stripped_new = new_code.strip()
            if stripped_original and stripped_original in base_text:
                return base_text.replace(stripped_original, stripped_new, 1), None, "ok"

            original_not_found_message = "Original code block not found in source file."

        line_number = patch.get("line_number") or patch.get("start_line")
        if line_number is not None:
            try:
                line_index = max(int(str(line_number).strip()) - 1, 0)
            except ValueError:
                return None, "Invalid line number provided in patch.", "error"

            lines = base_text.split("\n")
            if 0 <= line_index < len(lines):
                lines[line_index] = new_code
                result = "\n".join(lines)
                if base_text.endswith("\n") and not result.endswith("\n"):
                    result += "\n"
                return result, None, "ok"
            return None, "Line number out of range for source file.", "error"

        descriptor = patch.get("line_numbers")
        if descriptor:
            # If we have original_code that wasn't found, try to replace at the line_numbers location
            if original_code and original_not_found_message:
                lines = base_text.split("\n")
                insert_idx = self._determine_insertion_index(lines, descriptor)
                if insert_idx is not None and 0 <= insert_idx < len(lines):
                    # Try to replace the line(s) at that location
                    # Count how many lines the original_code spans
                    original_lines = original_code.split("\n")
                    if len(original_lines) == 1:
                        # Single line replacement
                        lines[insert_idx] = new_code
                        result = "\n".join(lines)
                        if base_text.endswith("\n") and not result.endswith("\n"):
                            result += "\n"
                        return result, None, "ok"
                    else:
                        # Multi-line: replace from insert_idx
                        end_idx = min(insert_idx + len(original_lines), len(lines))
                        new_lines = lines[:insert_idx] + new_code.split("\n") + lines[end_idx:]
                        result = "\n".join(new_lines)
                        if base_text.endswith("\n") and not result.endswith("\n"):
                            result += "\n"
                        return result, None, "ok"
            
            # Otherwise, try insertion
            inserted = self._insert_snippet_using_descriptor(base_text, new_code, descriptor)
            if inserted is not None:
                return inserted, None, "ok"
            # Provide more helpful error message
            descriptor_str = str(descriptor)[:100]  # Truncate if too long
            return (
                None,
                f"Unable to align patch using the provided 'line_numbers' context: '{descriptor_str}'. "
                f"Try providing 'original_code' or a more specific 'line_numbers' descriptor.",
                "error",
            )

        if original_not_found_message:
            return None, original_not_found_message, "error"

        return None, "Patch is missing original code context needed for replacement.", "skip"

    def _insert_snippet_using_descriptor(
        self,
        base_text: str,
        snippet: str,
        descriptor: Any,
    ) -> Optional[str]:
        """Insert snippet based on contextual instructions such as 'after line containing ...'."""

        descriptor_text = str(descriptor or "").strip()
        if not descriptor_text:
            return None

        lines = base_text.split("\n")
        insert_idx = self._determine_insertion_index(lines, descriptor_text)
        if insert_idx is None:
            return None

        snippet_lines = snippet.split("\n")
        insert_idx = max(0, min(insert_idx, len(lines)))

        snippet_starts_with_closing = snippet.lstrip().startswith("}")
        if snippet_starts_with_closing and insert_idx < len(lines):
            next_line = lines[insert_idx]
            if next_line.strip().startswith("}"):
                lines = list(lines)
                lines.pop(insert_idx)

        new_lines = list(lines[:insert_idx]) + snippet_lines + list(lines[insert_idx:])
        result = "\n".join(new_lines)
        if base_text.endswith("\n") and not result.endswith("\n"):
            result += "\n"
        return result

    def _determine_insertion_index(self, lines: Sequence[str], descriptor: str) -> Optional[int]:
        """Interpret textual line instructions to determine insertion index."""

        descriptor = str(descriptor).strip()
        descriptor_lower = descriptor.lower()
        relation = "after"
        if "before" in descriptor_lower and "after" not in descriptor_lower:
            relation = "before"

        # First, check if descriptor is just a number (e.g., "1964" or "1964-1965")
        # This handles simple numeric line_numbers
        numeric_match = re.match(r'^\s*(\d+)(?:\s*-\s*(\d+))?\s*$', descriptor)
        if numeric_match:
            try:
                line_no = int(numeric_match.group(1))
                # If it's a range, use the first number
                idx = max(line_no - 1, 0)
                idx = min(idx, len(lines))
                # Default to "after" for simple line numbers
                return min(idx + 1, len(lines))
            except ValueError:
                pass

        # Check for "line N" pattern
        match_line = re.search(r'\bline\s+(\d+)', descriptor, re.IGNORECASE)
        if match_line:
            try:
                line_no = int(match_line.group(1))
            except ValueError:
                return None
            idx = max(line_no - 1, 0)
            idx = min(idx, len(lines))
            return idx if relation == "before" else min(idx + 1, len(lines))

        # Check for "containing ..." pattern
        search_text: Optional[str] = None
        match_quote = re.search(r'containing\s*["\']([^"\']+)["\']', descriptor, re.IGNORECASE)
        if match_quote:
            search_text = match_quote.group(1)
        else:
            match_plain = re.search(r'containing\s+([^\n]+)', descriptor, re.IGNORECASE)
            if match_plain:
                search_text = match_plain.group(1).strip()

        if search_text:
            search_text = search_text.strip()
            matches: List[int] = []
            for idx, line in enumerate(lines):
                if search_text in line:
                    matches.append(idx)
            if matches:
                use_last = any(token in descriptor_lower for token in ["last", "final", "bottom", "end"])
                chosen = matches[-1] if use_last else matches[0]
                return chosen if relation == "before" else chosen + 1

        return None

    def _build_clang_command(
        self,
        temp_file_path: str,
        patch: Dict,
        compilers: Dict[str, Optional[str]],
        code_dir: Optional[str],
        original_dir: Optional[Path],
    ) -> Optional[List[str]]:
        """Construct clang command for syntax checking a temporary file."""

        temp_file_path = Path(temp_file_path)
        extension = temp_file_path.suffix.lower()

        if extension == ".c":
            compiler = compilers.get("c")
            flags = ["-std=c11"]
        elif extension in {".cpp", ".cxx", ".cc", ".c++"}:
            compiler = compilers.get("cpp")
            flags = ["-std=c++17"]
        else:
            return None

        if compiler is None:
            return None

        include_dirs = self._collect_include_dirs(patch, code_dir, original_dir)

        command: List[str] = [compiler, "-fsyntax-only", "-Werror"] + flags

        for include_dir in include_dirs:
            command.extend(["-I", include_dir])

        defines = patch.get("defines") or []
        for definition in defines:
            command.extend(["-D", definition])

        config_defines = self._config.get("extra_defines", [])
        for definition in config_defines:
            command.extend(["-D", definition])

        target = self._config.get("target")
        if target:
            command.extend(["-target", target])

        extra_flags = self._config.get("extra_compiler_flags", [])
        if extra_flags:
            command.extend(extra_flags)

        command.append(str(temp_file_path))
        return command

    def _collect_include_dirs(
        self,
        patch: Dict,
        code_dir: Optional[str],
        original_dir: Optional[Path],
    ) -> List[str]:
        """Gather include directories from multiple sources."""

        include_dirs: List[str] = []

        if code_dir:
            include_dirs.append(code_dir)

        if original_dir is not None:
            include_dirs.append(str(original_dir))

        patch_includes = patch.get("include_dirs") or []
        for include_dir in patch_includes:
            if include_dir not in include_dirs:
                include_dirs.append(include_dir)

        config_includes = self._config.get("extra_include_dirs", [])
        for include_dir in config_includes:
            if include_dir not in include_dirs:
                include_dirs.append(include_dir)

        return include_dirs

    def _resolve_patch_path(
        self, file_path: Optional[str], code_dir: Optional[str]
    ) -> Optional[Path]:
        """Normalize and resolve the filesystem path for a patch."""

        if not file_path:
            return None

        sanitized = str(file_path).strip()
        if not sanitized:
            return None

        candidate = Path(sanitized)
        if candidate.is_absolute():
            return candidate

        if not code_dir:
            return candidate

        code_root = Path(code_dir)
        parts = [part for part in sanitized.replace("\\", "/").split("/") if part and part != "."]

        if parts:
            code_parts = [part.lower() for part in code_root.parts]
            parts_lower = [part.lower() for part in parts]
            max_prefix = min(len(parts), len(code_parts))
            for i in range(max_prefix, 0, -1):
                if parts_lower[:i] == code_parts[-i:]:
                    parts = parts[i:]
                    parts_lower = parts_lower[i:]
                    break
            if parts and parts[0].lower() == code_root.name.lower():
                parts = parts[1:]

        normalized = code_root.joinpath(*parts) if parts else code_root
        try:
            return normalized.resolve()
        except Exception:  # File may not exist yet; fallback to absolute without resolve
            return normalized

    # ------------------------------------------------------------------
    # Configuration helpers & reporting utilities
    # ------------------------------------------------------------------

    def _load_config(self) -> Dict[str, List[str]]:
        """Load optional engine configuration from resources."""

        default: Dict[str, List[str]] = {
            "extra_include_dirs": [],
            "extra_defines": [],
            "extra_compiler_flags": [],
        }

        # Resolve path relative to Backend directory
        # This file is at: Backend/app/services/code_testing_engine.py
        # So Backend is: __file__.parent.parent.parent
        backend_dir = Path(__file__).resolve().parent.parent.parent
        config_path = backend_dir / "resources" / "code_testing_config.json"
        if not config_path.exists():
            return default

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return default
        except Exception:  # pylint: disable=broad-except
            return default

        config: Dict[str, List[str]] = default.copy()
        for key in [
            "extra_include_dirs",
            "extra_defines",
            "extra_compiler_flags",
        ]:
            value = data.get(key)
            if isinstance(value, list):
                config[key] = [str(item) for item in value]

        target = data.get("target")
        if isinstance(target, str):
            config["target"] = target.strip()

        hint = data.get("missing_header_hint")
        if isinstance(hint, str) and hint.strip():
            config["missing_header_hint"] = hint.strip()

        return config

    def _report_compiler_failure(
        self,
        results: List[str],
        stdout_text: str,
        stderr_text: str,
        exit_code: int,
    ) -> Optional[str]:
        """Append human-friendly compiler failure details. Returns missing header name if detected."""

        header_missing = self._extract_missing_header(stderr_text)
        if header_missing:
            results.append(
                f"    ❌ Missing header '{header_missing}' (exit code {exit_code})."
            )
            hint = self._config.get(
                "missing_header_hint",
                "Provide the appropriate system headers or update backend/resources/code_testing_config.json with extra include directories.",
            )
            results.append(f"      › Hint: {hint}")
            return header_missing

        results.append(f"    ❌ Syntax check failed (exit code {exit_code}).")

        if stdout_text:
            results.append(self._indent_multiline_output(stdout_text))
        if stderr_text:
            results.append(self._indent_multiline_output(stderr_text))
        return None

    @staticmethod
    def _extract_missing_header(stderr_text: str) -> Optional[str]:
        """Detect missing header messages in compiler stderr."""

        marker = "fatal error: '"
        if marker not in stderr_text:
            return None

        try:
            start = stderr_text.index(marker) + len(marker)
            end = stderr_text.index("' file not found", start)
            header = stderr_text[start:end].strip()
            return header or None
        except ValueError:
            return None

    @staticmethod
    def _indent_multiline_output(text: str, prefix: str = "      › ") -> str:
        """Indent multi-line compiler output for readability."""

        lines = [prefix + line for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def _get_cppcheck_path(self) -> Optional[str]:
        """Locate cppcheck executable."""

        if self._cppcheck_path is not None:
            return self._cppcheck_path

        # First try shutil.which (checks PATH)
        self._cppcheck_path = shutil.which("cppcheck") or shutil.which("cppcheck.exe")
        if self._cppcheck_path:
            return self._cppcheck_path

        # On Windows, check common installation locations and PATH manually
        if os.name == 'nt':  # Windows
            # Check common installation paths
            common_paths = [
                r"C:\Program Files\Cppcheck\cppcheck.exe",
                r"C:\Program Files (x86)\Cppcheck\cppcheck.exe",
                os.path.expanduser(r"~\AppData\Local\Programs\Cppcheck\cppcheck.exe"),
            ]
            
            for path in common_paths:
                if os.path.isfile(path):
                    self._cppcheck_path = path
                    return self._cppcheck_path
            
            # Manually check PATH directories (sometimes shutil.which doesn't catch all)
            path_dirs = os.environ.get("PATH", "").split(os.pathsep)
            for path_dir in path_dirs:
                if path_dir.strip():
                    potential_path = os.path.join(path_dir, "cppcheck.exe")
                    if os.path.isfile(potential_path):
                        self._cppcheck_path = potential_path
                        return self._cppcheck_path

        return self._cppcheck_path

    def _run_cppcheck(
        self,
        cppcheck_path: str,
        temp_file_path: Path,
        patch: Dict,
        code_dir: Optional[str],
        original_dir: Optional[Path],
        results: List[str],
        timeout: int = 60,
    ) -> bool:
        """Run cppcheck as a fallback static analyser."""

        temp_file_path = Path(temp_file_path)
        extension = temp_file_path.suffix.lower()

        if extension == ".c":
            language = "c"
            std = "c11"
        elif extension in {".cpp", ".cxx", ".cc", ".c++"}:
            language = "c++"
            std = "c++17"
        else:
            language = "c"
            std = "c11"

        include_dirs = self._collect_include_dirs(patch, code_dir, original_dir)

        command: List[str] = [
            cppcheck_path,
            "--enable=warning,style,performance",
            "--error-exitcode=1",
            f"--language={language}",
            f"--std={std}",
            "--quiet",
            "--force",
        ]

        for include_dir in include_dirs:
            command.extend(["-I", include_dir])

        command.append(str(temp_file_path))

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            results.append("    ❌ cppcheck fallback timed out after 60 seconds.")
            return False
        except Exception as exc:  # pylint: disable=broad-except
            results.append(f"    ❌ Failed to execute cppcheck: {exc}")
            return False

        stdout_text = completed.stdout or ""
        stderr_text = completed.stderr or ""

        messages = self._parse_cppcheck_messages(stdout_text, stderr_text)
        target_lines = self._collect_patch_target_lines(patch)
        relevant, others = self._split_cppcheck_messages(
            messages, Path(temp_file_path), target_lines
        )

        if relevant:
            results.append("    ❌ cppcheck reported issues in modified code.")
            for msg in relevant:
                results.append(self._indent_multiline_output(msg["raw"]))
            return False

        results.append("    ✅ No issues found in modified lines.")
        return True

    def _run_config_patch_validation(
        self,
        config_patches: Sequence[Dict],
        code_dir: Optional[str],
    ) -> Tuple[List[str], Tuple[int, int, int]]:
        """Validate configuration patches by checking applicability in target files."""

        lines: List[str] = ["Config Patch Validation"]
        success_count = 0
        failure_count = 0
        skipped_count = 0

        if not code_dir:
            failure_count = len(tuple(config_patches))
            lines.append(
                "  ❌ Original code directory missing in analysis data. Cannot validate config patches."
            )
            return lines, (0, failure_count, 0)

        for index, patch in enumerate(config_patches, start=1):
            param_name = (
                patch.get("config_name")
                or patch.get("parameter_name")
                or patch.get("setting")
                or patch.get("description")
                or f"Config Patch {index}"
            )
            lines.append(f"  → {param_name}")

            file_path = patch.get("file_path")
            if not file_path:
                failure_count += 1
                lines.append("    ❌ Config patch is missing 'file_path'.")
                continue

            resolved_path = self._resolve_patch_path(file_path, code_dir)
            if resolved_path is None:
                failure_count += 1
                lines.append("    ❌ File path could not be resolved.")
                continue

            if not resolved_path.exists():
                failure_count += 1
                lines.append(f"    ❌ File not found: {resolved_path}")
                continue

            try:
                try:
                    file_text = resolved_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    file_text = resolved_path.read_text(encoding="latin-1")
            except Exception as exc:  # pylint: disable=broad-except
                failure_count += 1
                lines.append(f"    ❌ Unable to read config file: {exc}")
                continue

            file_text_normalized = re.sub(r"\s+", "", file_text)

            current_value = patch.get("current_value")
            new_value = patch.get("new_value") or patch.get("suggested_value") or patch.get("patched_value")
            if new_value is None or str(new_value).strip() == "":
                failure_count += 1
                lines.append("    ❌ Config patch is missing 'new_value'.")
                continue

            current_value_str = str(current_value) if current_value is not None else ""
            new_value_str = str(new_value)

            if current_value_str.strip() and current_value_str.strip() == new_value_str.strip():
                failure_count += 1
                lines.append("    ❌ New value matches the current value; no change required.")
                continue

            current_value_normalized = re.sub(r"\s+", "", current_value_str)
            new_value_normalized = re.sub(r"\s+", "", new_value_str)

            line_number = patch.get("line_number")
            line_index: Optional[int] = None
            if line_number is not None:
                match = re.search(r"\d+", str(line_number))
                if match:
                    try:
                        line_index = int(match.group()) - 1
                    except ValueError:
                        line_index = None

            file_lines = file_text.splitlines()
            line_text = ""
            if line_index is not None:
                if 0 <= line_index < len(file_lines):
                    line_text = file_lines[line_index]
                else:
                    failure_count += 1
                    lines.append(
                        f"    ❌ Reported line number {line_number} is outside the bounds of the file."
                    )
                    continue

            line_text_normalized = re.sub(r"\s+", "", line_text)

            found_new_value = new_value_normalized and new_value_normalized in file_text_normalized
            found_current_value = (
                current_value_normalized
                and current_value_normalized in file_text_normalized
            )
            line_has_new_value = new_value_normalized and new_value_normalized in line_text_normalized
            line_has_current_value = (
                current_value_normalized
                and current_value_normalized in line_text_normalized
            )

            if line_has_new_value or (found_new_value and not found_current_value):
                success_count += 1
                lines.append("    ✅ Desired value already present in the configuration.")
                continue

            if line_has_current_value or found_current_value:
                success_count += 1
                message = "    ✅ Current value located; ready to update to the new value."
                if line_index is not None:
                    message += f" (line {line_index + 1})"
                lines.append(message)
                continue

            param_marker = str(param_name).strip()
            if param_marker and re.sub(r"\s+", "", param_marker) in file_text_normalized:
                # Parameter present but values not matched—treat as warning but pass.
                success_count += 1
                lines.append(
                    "    ⚠️ Parameter located, but existing value did not match the expected current value. Review manually."
                )
                continue

            failure_count += 1
            lines.append(
                "    ❌ Unable to locate current or desired values in the target configuration file."
            )

        return lines, (success_count, failure_count, skipped_count)

    def run_variable_impact_analysis(
        self,
        patches: Sequence[Dict],
        code_dir: Optional[str],
        *,
        error_summary: Optional[str] = None,
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Assess whether variable changes in patches have wider impact."""

        lines: List[str] = ["Layer 4: Variable Impact Analysis"]
        structured_results: List[Dict[str, Any]] = []

        if not patches:
            lines.append("  ⚠️ No code patches selected – skipping variable impact analysis.")
            return lines, structured_results

        for index, patch in enumerate(patches, start=1):
            function_name = patch.get("function_name") or patch.get("target_function") or patch.get("symbol")
            file_path = patch.get("file_path") or "Unknown file"
            patch_label = function_name or file_path or f"Patch {index}"
            lines.append(f"  → {patch_label}")

            context = self._extract_function_context_for_patch(patch, code_dir)
            if context is None:
                lines.append("    ❌ Unable to extract function context for analysis.")
                structured_results.append(
                    {
                        "patch_label": patch_label,
                        "function_name": function_name,
                        "file_path": file_path,
                        "status": "error",
                        "messages": ["Unable to extract function context for analysis."],
                    }
                )
                continue

            original_fn = context["original"]
            patched_fn = context["patched"]
            diff_text = context.get("diff")

            detected, detector_messages = self._variable_impact_evaluator.detect_variable_changes(
                function_name=function_name or "unknown_function",
                file_path=file_path,
                original_function=original_fn,
                patched_function=patched_fn,
                diff_text=diff_text,
            )

            for message in detector_messages:
                lines.append(self._indent_multiline_output(message, prefix="    › "))

            if not detected:
                lines.append("    ✅ No variable-level behavioural changes detected.")
                structured_results.append(
                    {
                        "patch_label": patch_label,
                        "function_name": function_name,
                        "file_path": file_path,
                        "status": "success",
                        "verdict": "PASS",
                        "variables": [],
                        "summary": "No variable-level behavioural changes detected.",
                        "messages": detector_messages,
                    }
                )
                continue

            non_local = [change for change in detected if not change.is_local_only and change.should_review]
            if not non_local:
                lines.append("    ✅ Variable changes are confined to local scope.")
                structured_results.append(
                    {
                        "patch_label": patch_label,
                        "function_name": function_name,
                        "file_path": file_path,
                        "status": "success",
                        "verdict": "PASS",
                        "variables": [asdict(change) for change in detected],
                        "summary": "Variable changes appear local to the function.",
                        "messages": detector_messages,
                    }
                )
                continue

            variable_payload = self._build_variable_payload(
                function_name=function_name,
                file_path=file_path,
                variable_changes=non_local,
                code_dir=code_dir,
            )

            impact_result = self._variable_impact_evaluator.evaluate_variable_impact(
                function_name=function_name or "unknown_function",
                file_path=file_path,
                patched_function=patched_fn,
                diff_text=diff_text,
                variables=variable_payload,
            )

            if impact_result.status != "success":
                for message in impact_result.messages:
                    lines.append(self._indent_multiline_output(message, prefix="    › "))
                structured_results.append(
                    {
                        "patch_label": patch_label,
                        "function_name": function_name,
                        "file_path": file_path,
                        "status": "error",
                        "variables": [asdict(change) for change in detected],
                        "messages": detector_messages + impact_result.messages,
                    }
                )
                continue

            verdict = (impact_result.verdict or "UNKNOWN").upper()
            confidence = impact_result.confidence
            verdict_icon = {"PASS": "✅", "NEEDS_REVIEW": "⚠️", "FAIL": "❌"}.get(verdict, "ℹ️")
            verdict_line = f"    {verdict_icon} Verdict: {verdict.replace('_', ' ').title()}"
            if confidence is not None:
                verdict_line += f" (Confidence: {confidence:.2f})"
            lines.append(verdict_line)

            if impact_result.summary:
                lines.append("    Summary:")
                lines.append(self._indent_multiline_output(impact_result.summary, prefix="      › "))

            structured_results.append(
                {
                    "patch_label": patch_label,
                    "function_name": function_name,
                    "file_path": file_path,
                    "status": "success",
                    "verdict": verdict,
                    "confidence": confidence,
                    "variables": [asdict(change) for change in detected],
                    "analysis_variables": variable_payload,
                    "per_variable": impact_result.per_variable,
                    "summary": impact_result.summary,
                    "issues": impact_result.issues,
                    "recommendations": impact_result.recommendations,
                    "messages": detector_messages + impact_result.messages,
                }
            )

        return lines, structured_results

    def _collect_patch_target_lines(self, patch: Dict) -> Set[int]:
        """Determine which line numbers in the original file correspond to the patched code."""

        target_lines: Set[int] = set()
        line_numbers = patch.get("line_numbers")
        if line_numbers is None:
            return target_lines

        if isinstance(line_numbers, str):
            bases = [line_numbers]
        elif isinstance(line_numbers, (list, tuple)):
            bases = line_numbers
        else:
            bases = [line_numbers]

        patched_code = patch.get("patched_code") or patch.get("suggested_code") or patch.get("new_code")
        patched_length = 1
        if isinstance(patched_code, str):
            patched_lines = patched_code.splitlines() or [patched_code]
            patched_length = max(1, len(patched_lines))

        for base in bases:
            try:
                base_int = int(str(base).strip())
            except (TypeError, ValueError):
                continue
            for offset in range(patched_length):
                target_lines.add(base_int + offset)
        return target_lines

    def _parse_cppcheck_messages(
        self,
        stdout_text: str,
        stderr_text: str,
    ) -> List[Dict[str, Optional[str]]]:
        """Parse cppcheck output into structured messages."""

        combined = []
        if stdout_text:
            combined.extend(stdout_text.splitlines())
        if stderr_text:
            combined.extend(stderr_text.splitlines())

        pattern = re.compile(
            r"^(?P<path>[^:\s][^:]*)"
            r":(?P<line>\d+)"
            r":(?P<column>\d+)"
            r": (?P<severity>\w+)"
            r": (?P<message>.*)$"
        )

        messages: List[Dict[str, Optional[str]]] = []
        for raw_line in combined:
            line = raw_line.strip()
            if not line:
                continue
            match = pattern.match(line)
            if match:
                data = match.groupdict()
                data["line"] = int(data["line"])
                data["column"] = int(data["column"])
                data["raw"] = line
                messages.append(data)
            else:
                messages.append(
                    {
                        "path": None,
                        "line": None,
                        "column": None,
                        "severity": "info",
                        "message": line,
                        "raw": line,
                    }
                )
        return messages

    def _split_cppcheck_messages(
        self,
        messages: Sequence[Dict[str, Optional[str]]],
        temp_file_path: Path,
        target_lines: Set[int],
    ) -> Tuple[List[Dict[str, Optional[str]]], List[Dict[str, Optional[str]]]]:
        """Separate messages that affect the modified lines from the rest."""

        relevant: List[Dict[str, Optional[str]]] = []
        others: List[Dict[str, Optional[str]]] = []

        temp_filename = temp_file_path.name
        for message in messages:
            path = message.get("path")
            line = message.get("line")
            if path and Path(path).name == temp_filename and isinstance(line, int):
                if not target_lines or line in target_lines:
                    relevant.append(message)
                else:
                    others.append(message)
            else:
                others.append(message)
        return relevant, others

    def _build_variable_payload(
        self,
        *,
        function_name: Optional[str],
        file_path: str,
        variable_changes: Sequence[VariableChange],
        code_dir: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Prepare payload entries for the variable impact evaluator."""

        payload: List[Dict[str, Any]] = []
        for change in variable_changes:
            related_functions = self._collect_related_functions_for_variable(
                function_name=function_name,
                file_path=file_path,
                variable_name=change.name,
                code_dir=code_dir,
            )
            entry = asdict(change)
            entry["related_functions"] = related_functions
            payload.append(entry)
        return payload

    def _extract_function_context_for_patch(
        self,
        patch: Dict,
        code_dir: Optional[str],
    ) -> Optional[Dict[str, Optional[str]]]:
        """Extract original and patched function bodies for a patch."""

        file_path = patch.get("file_path")
        function_name = patch.get("function_name")

        resolved_path: Optional[Path] = None
        original_text: Optional[str] = None
        if file_path and code_dir:
            resolved_path = self._resolve_patch_path(file_path, code_dir)
            if resolved_path and resolved_path.exists():
                try:
                    original_text = resolved_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    original_text = resolved_path.read_text(encoding="latin-1")
                except Exception:
                    original_text = None

        if original_text is None:
            original_text = patch.get("original_code") or patch.get("existing_code")

        patched_text: Optional[str] = None
        if original_text is not None:
            patched_content, _, status = self._generate_patched_content(original_text, patch)
            if status == "ok" and patched_content is not None:
                patched_text = patched_content

        if patched_text is None:
            patched_text = patch.get("patched_code") or patch.get("suggested_code") or patch.get("new_code")

        if original_text is None or patched_text is None:
            return None

        original_function = None
        patched_function = None

        if function_name:
            original_function = self._locate_function_text(original_text, function_name, patch.get("original_code"))
            patched_function = self._locate_function_text(patched_text, function_name, patch.get("patched_code"))

        if original_function is None:
            original_function = original_text
        if patched_function is None:
            patched_function = patched_text

        diff_text = self._build_function_diff(
            original_function,
            patched_function,
            from_label=f"{file_path or 'original'}",
            to_label=f"{file_path or 'patched'} (new)",
        )

        return {
            "original": original_function,
            "patched": patched_function,
            "diff": diff_text,
        }

    @staticmethod
    def _build_function_diff(
        original_text: str,
        patched_text: str,
        *,
        from_label: str,
        to_label: str,
        max_lines: int = 400,
    ) -> str:
        original_lines = original_text.splitlines()
        patched_lines = patched_text.splitlines()
        diff_iter = difflib.unified_diff(
            original_lines,
            patched_lines,
            fromfile=from_label,
            tofile=to_label,
            n=3,
            lineterm="",
        )
        diff_lines: List[str] = []
        for idx, line in enumerate(diff_iter):
            if idx >= max_lines:
                diff_lines.append("... (diff truncated)")
                break
            diff_lines.append(line)
        return "\n".join(diff_lines)

    def _locate_function_text(
        self,
        content: str,
        function_name: str,
        fallback_snippet: Optional[str] = None,
    ) -> Optional[str]:
        """Attempt to extract the full function text from source content."""

        if not content or not function_name:
            return fallback_snippet

        token = f"{function_name}("
        matches: List[Tuple[int, int]] = []
        search_pos = 0
        while True:
            idx = content.find(token, search_pos)
            if idx == -1:
                break

            line_start = content.rfind("\n", 0, idx)
            signature_start = 0 if line_start == -1 else line_start + 1

            while signature_start > 0:
                prev_newline = content.rfind("\n", 0, signature_start - 1)
                if prev_newline == -1:
                    signature_start = 0
                    break
                candidate_line = content[prev_newline + 1:signature_start].strip()
                if not candidate_line or candidate_line.startswith("#"):
                    break
                signature_start = prev_newline + 1

            brace_idx = content.find("{", idx)
            if brace_idx == -1:
                search_pos = idx + len(token)
                continue

            brace_depth = 0
            end_pos = None
            pos = brace_idx
            while pos < len(content):
                char = content[pos]
                if char == "{":
                    brace_depth += 1
                elif char == "}":
                    brace_depth -= 1
                    if brace_depth == 0:
                        end_pos = pos + 1
                        break
                pos += 1

            if end_pos is None:
                search_pos = idx + len(token)
                continue

            matches.append((signature_start, end_pos))
            search_pos = end_pos

        if not matches:
            return fallback_snippet

        if fallback_snippet:
            snippet = fallback_snippet.strip()
            for start, end in matches:
                candidate = content[start:end]
                if snippet and snippet in candidate:
                    return candidate

        start, end = matches[0]
        return content[start:end]

    def _ensure_function_metadata_loaded(self) -> None:
        if self._function_db_loaded:
            return

        # Resolve path relative to Error_fixing_pipelin directory
        # This file is at: Backend/app/services/code_testing_engine.py
        # Error_fixing_pipelin is at: Backend/app/services/Error_fixing_pipelin
        error_pipeline_dir = Path(__file__).resolve().parent / "Error_fixing_pipelin"
        path = error_pipeline_dir / "database" / "functions.json"
        if not path.exists():
            self._function_db_loaded = True
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            self._function_db_loaded = True
            return

        for entry in data:
            function_name = entry.get("function_name")
            file_path = entry.get("file_path")
            if not function_name or not file_path:
                continue
            normalized = self._normalize_repo_path(file_path)
            entry["_normalized_file_path"] = normalized
            self._functions_by_name.setdefault(function_name, []).append(entry)
            self._functions_by_file.setdefault(normalized, []).append(entry)

        self._function_db_loaded = True

    def _ensure_call_graph_loaded(self) -> None:
        if self._call_graph_loaded:
            return

        # Resolve path relative to Error_fixing_pipelin directory
        # This file is at: Backend/app/services/code_testing_engine.py
        # Error_fixing_pipelin is at: Backend/app/services/Error_fixing_pipelin
        error_pipeline_dir = Path(__file__).resolve().parent / "Error_fixing_pipelin"
        path = error_pipeline_dir / "database" / "function_calls.json"
        if not path.exists():
            self._call_graph_loaded = True
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            self._call_graph_loaded = True
            return

        for entry in data:
            name = entry.get("function")
            if not name:
                continue
            info = self._call_graph_index.setdefault(name, {"calls": set(), "called_by": set(), "files": set()})
            for called in entry.get("calls", []):
                info["calls"].add(called)
            for caller in entry.get("called_by", []):
                info["called_by"].add(caller)
            file_path = entry.get("file")
            if file_path:
                info["files"].add(self._normalize_repo_path(file_path))

        self._call_graph_loaded = True

    @staticmethod
    def _normalize_repo_path(path: Optional[str]) -> str:
        if not path:
            return ""
        normalized = path.replace("\\", "/").strip()
        return normalized.lower()

    def _collect_related_functions_for_variable(
        self,
        *,
        function_name: Optional[str],
        file_path: str,
        variable_name: str,
        code_dir: Optional[str],
        max_functions: int = 6,
    ) -> List[Dict[str, Any]]:
        self._ensure_function_metadata_loaded()
        self._ensure_call_graph_loaded()

        related: List[Dict[str, Any]] = []
        seen: Set[Tuple[str, str]] = set()
        normalized_file = self._normalize_repo_path(file_path)

        candidate_entries: List[Tuple[Dict[str, Any], str]] = []

        if function_name:
            for entry in self._get_function_entries(function_name, normalized_file):
                candidate_entries.append((entry, "self"))

            graph_info = self._call_graph_index.get(function_name)
            if graph_info:
                neighbours = graph_info.get("calls", set()) | graph_info.get("called_by", set())
                for neighbor in neighbours:
                    for entry in self._get_function_entries(neighbor, None):
                        candidate_entries.append((entry, "graph"))

        for entry in self._functions_by_file.get(normalized_file, []):
            candidate_entries.append((entry, "file"))

        pattern = re.compile(rf"\b{re.escape(variable_name)}\b")

        variable_matches = 0
        for entry_dict, source in candidate_entries:
            entry = entry_dict
            fname = entry.get("function_name") or "<unknown>"
            fpath = entry.get("file_path") or ""
            normalized_entry_path = entry.get("_normalized_file_path") or self._normalize_repo_path(fpath)
            key = (fname, normalized_entry_path)
            if key in seen:
                continue
            code_body = entry.get("code_body")
            if not isinstance(code_body, str):
                continue
            if pattern.search(code_body):
                seen.add(key)
                usage_snippet = self._extract_usage_snippet(code_body, variable_name)
                related.append(
                    {
                        "function_name": fname,
                        "file_path": fpath,
                        "usage_snippet": usage_snippet,
                        "code_excerpt": self._truncate_code_excerpt(code_body),
                        "full_code": code_body,
                        "match_reason": "variable_usage",
                    }
                )
                variable_matches += 1
                if len(related) >= max_functions:
                    break

        if variable_matches == 0:
            for entry_dict, source in candidate_entries:
                if source not in {"self", "graph"}:
                    continue
                entry = entry_dict
                fname = entry.get("function_name") or "<unknown>"
                fpath = entry.get("file_path") or ""
                normalized_entry_path = entry.get("_normalized_file_path") or self._normalize_repo_path(fpath)
                key = (fname, normalized_entry_path)
                if key in seen:
                    continue
                code_body = entry.get("code_body")
                snippet = ""
                full_code = ""
                if isinstance(code_body, str):
                    snippet = self._truncate_code_excerpt(code_body, max_chars=400)
                    full_code = code_body
                related.append(
                    {
                        "function_name": fname,
                        "file_path": fpath,
                        "usage_snippet": snippet,
                        "code_excerpt": snippet,
                        "full_code": full_code,
                        "match_reason": "call_graph_neighbor",
                    }
                )
                seen.add(key)
                if len(related) >= max_functions:
                    break

        return related

    def _get_function_entries(
        self,
        function_name: Optional[str],
        normalized_file: Optional[str],
    ) -> List[Dict[str, Any]]:
        if not function_name:
            return []
        self._ensure_function_metadata_loaded()
        entries = list(self._functions_by_name.get(function_name, []))
        if normalized_file:
            filtered = [entry for entry in entries if entry.get("_normalized_file_path") == normalized_file]
            if filtered:
                return filtered
        return entries

    @staticmethod
    def _extract_usage_snippet(code_body: str, variable_name: str, context_lines: int = 2) -> str:
        lines = code_body.splitlines()
        pattern = re.compile(rf"\b{re.escape(variable_name)}\b")
        for idx, line in enumerate(lines):
            if pattern.search(line):
                start = max(0, idx - context_lines)
                end = min(len(lines), idx + context_lines + 1)
                snippet = "\n".join(lines[start:end])
                return snippet
        return "\n".join(lines[: min(len(lines), 6)])

    @staticmethod
    def _truncate_code_excerpt(code_body: str, max_chars: int = 800) -> str:
        text = code_body.strip()
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 15] + "\n... (truncated)"


    def _format_cppcheck_preview(
        self,
        messages: Sequence[Dict[str, Optional[str]]],
        limit: int = 5,
    ) -> Optional[str]:
        """Create a concise preview of cppcheck messages."""

        if not messages:
            return None

        severity_totals: Dict[str, int] = {}
        for msg in messages:
            severity = str(msg.get("severity") or "info").upper()
            severity_totals[severity] = severity_totals.get(severity, 0) + 1

        summary_parts = [
            f"{count} {severity.lower()}{'s' if count != 1 else ''}"
            for severity, count in sorted(severity_totals.items())
        ]
        summary = ", ".join(summary_parts)
        total = len(messages)
        text = (
            f"{total} diagnostic{'s' if total != 1 else ''} outside modified lines"
            + (f" ({summary})" if summary else "")
        )
        return self._indent_multiline_output(text)


