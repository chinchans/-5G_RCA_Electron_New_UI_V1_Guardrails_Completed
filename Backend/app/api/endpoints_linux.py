from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import Optional, List, Dict, Any
import os
import sys
import json
import shutil
import uuid
import asyncio
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
from app.services.dataset_generator import DatasetExtractor
from app.services.recursive_test_graph_attach import (
    get_main_sections,
    get_subsections,
    extract_text_from_subsection,
    build_graph,
    generate_test_scenarios,
    save_graph_to_json
)
from app.services.test_script_generator import TestScriptGenerator
from app.services.history_logger import append_history_record, load_history_entries
from app.services.code_testing_engine import CodeTestingEngine
from app.services.spec_reference_evaluator import SpecReferenceEvaluator
from app.services.llm_judge_evaluator import LLMJudgeEvaluator
from app.services.variable_impact_evaluator import VariableImpactEvaluator
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Import error fixing pipeline directly
import sys
import os
from pathlib import Path

# Get Backend directory path for resolving resource paths
# This file is at: Backend/app/api/endpoints.py
# So Backend is: __file__.parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

# Add the Error_fixing_pipelin directory to the Python path (matching PyQt UI)
current_dir = Path(__file__).parent.parent
# Add the outer Error_fixing_pipelin module path (for PyQt-style import)
outer_error_pipeline_path = current_dir / "services" / "Error_fixing_pipelin"
if str(outer_error_pipeline_path) not in sys.path:
    sys.path.append(str(outer_error_pipeline_path))

# The Error_fixing_pipelin directory path (no nested subdirectory exists)
error_pipeline_path = current_dir / "services" / "Error_fixing_pipelin"
if str(error_pipeline_path) not in sys.path:
    sys.path.append(str(error_pipeline_path))

# Also add the Backend directory to sys.path as fallback
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

# Load environment variables from .env file (check multiple locations)
try:
    from dotenv import load_dotenv
    import os
    
    # Try loading from multiple possible locations (matching UI_v3.py behavior)
    env_loaded = False
    
    # 1. Try Backend directory (where main.py is)
    backend_env_path = backend_dir / ".env"
    if backend_env_path.exists():
        load_dotenv(backend_env_path, override=True)
        print(f"✅ Loaded environment variables from: {backend_env_path}")
        env_loaded = True
    else:
        print(f"⚠️ .env file not found at: {backend_env_path}")
    
    # 2. Try Error_fixing_pipelin directory
    error_pipeline_env_path = current_dir / "services" / "Error_fixing_pipelin" / ".env"
    if error_pipeline_env_path.exists():
        load_dotenv(error_pipeline_env_path, override=False)  # Don't override if already loaded
        if not env_loaded:
            print(f"✅ Loaded environment variables from: {error_pipeline_env_path}")
            env_loaded = True
        else:
            print(f"ℹ️  Also found .env at: {error_pipeline_env_path} (using Backend .env)")
    
    # 3. Try current working directory (like UI_v3.py does)
    cwd_env_path = Path(os.getcwd()) / ".env"
    if cwd_env_path.exists() and cwd_env_path != backend_env_path and cwd_env_path != error_pipeline_env_path:
        load_dotenv(cwd_env_path, override=False)
        if not env_loaded:
            print(f"✅ Loaded environment variables from: {cwd_env_path}")
            env_loaded = True
    
    # 4. Final fallback - try loading from current directory without specifying path (dotenv default behavior)
    if not env_loaded:
        load_dotenv()  # This will look for .env in current directory and parent directories
        print(f"ℹ️  Attempted to load .env using default dotenv behavior")
    
    # Verify required environment variables are set
    # Prefer AZURE_OPENAI_API_KEY, but also accept AZURE_OPENAI_KEY for backward compatibility
    api_key = os.getenv('AZURE_OPENAI_API_KEY') or os.getenv('AZURE_OPENAI_KEY')
    endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    
    missing_vars = []
    if not api_key:
        missing_vars.append('AZURE_OPENAI_API_KEY (or AZURE_OPENAI_KEY for backward compatibility)')
    if not endpoint:
        missing_vars.append('AZURE_OPENAI_ENDPOINT')
    
    if missing_vars:
        print(f"⚠️ Warning: Some environment variables may be missing: {missing_vars}")
        print(f"   Note: Pipeline will check for these at runtime")
    else:
        print(f"✅ All required environment variables are set")
        print(f"   Using API key from: {'AZURE_OPENAI_API_KEY' if os.getenv('AZURE_OPENAI_API_KEY') else 'AZURE_OPENAI_KEY'}")
        
except Exception as e:
    print(f"⚠️ Could not load .env file: {e}")
    import traceback
    traceback.print_exc()

# Import the complete error fixing pipeline (matching PyQt UI approach)
ERROR_FIXING_AVAILABLE = False
CompleteErrorFixingPipeline = None
update_embeddings_from_ui = None

try:
    print(f"🔍 Attempting to import Error fixing pipeline from app.services.Error_fixing_pipelin...")
    from app.services.Error_fixing_pipelin import CompleteErrorFixingPipeline
    from app.services.Error_fixing_pipelin import update_embeddings_from_ui
    ERROR_FIXING_AVAILABLE = True
    print("✅ Error fixing pipeline loaded successfully (package import method)")
except ImportError as e:
    print(f"⚠️ Package import failed: {e}")
    print(f"   Attempting fallback import methods...")
    # Fallback: try direct import with path manipulation (matching PyQt UI)
    try:
        print(f"   Current working directory: {os.getcwd()}")
        print(f"   Looking for module in: {outer_error_pipeline_path}")
        print(f"   Module exists: {outer_error_pipeline_path.exists()}")
        print(f"   Contains complete_error_fixing_pipeline.py: {(outer_error_pipeline_path / 'complete_error_fixing_pipeline.py').exists()}")
        
        # Try importing directly from the module files
        from app.services.Error_fixing_pipelin.complete_error_fixing_pipeline import CompleteErrorFixingPipeline
        from app.services.Error_fixing_pipelin.ui_integration import update_embeddings_from_ui
        ERROR_FIXING_AVAILABLE = True
        print("✅ Error fixing pipeline loaded successfully (direct import method)")
    except ImportError as e2:
        print(f"⚠️ Direct import failed: {e2}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        # Final fallback: try importing with sys.path manipulation (like UI_v3.py)
        try:
            print(f"   Attempting sys.path manipulation method...")
            # Add the Error_fixing_pipelin directory to sys.path
            if str(outer_error_pipeline_path) not in sys.path:
                sys.path.insert(0, str(outer_error_pipeline_path))
                print(f"   Added to sys.path: {outer_error_pipeline_path}")
            
            # Now try importing using the module name directly (like UI_v3.py does)
            from app.services.Error_fixing_pipelin.complete_error_fixing_pipeline import CompleteErrorFixingPipeline
            from app.services.Error_fixing_pipelin.ui_integration import update_embeddings_from_ui
            ERROR_FIXING_AVAILABLE = True
            print("✅ Error fixing pipeline loaded successfully (sys.path method)")
        except ImportError as e3:
            # Final fallback if the module is not found
            print(f"❌ ERROR: All import methods failed!")
            print(f"   Last error: {e3}")
            import traceback
            print(f"   Full traceback: {traceback.format_exc()}")
            CompleteErrorFixingPipeline = None
            update_embeddings_from_ui = None
            ERROR_FIXING_AVAILABLE = False
except Exception as e:
    print(f"❌ ERROR: Unexpected error while loading error fixing pipeline: {e}")
    import traceback
    print(f"   Full traceback: {traceback.format_exc()}")
    CompleteErrorFixingPipeline = None
    update_embeddings_from_ui = None
    ERROR_FIXING_AVAILABLE = False

router = APIRouter()

@router.get("/")
async def root():
    """Root endpoint - returns a welcome message"""
    return {"message": "Welcome to RCA Backend API", "status": "running"}

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "RCA Backend"}


# File Upload endpoint
@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file and store it in the resources/uploaded_docs folder"""
    try:
        # Create the upload directory if it doesn't exist
        upload_dir = BACKEND_DIR / "resources" / "uploaded_docs"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a unique filename to avoid conflicts
        import uuid
        file_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "saved_as": unique_filename,
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

# Get uploaded files endpoint
@router.get("/api/uploaded-files")
async def get_uploaded_files():
    """Get list of all uploaded files"""
    try:
        upload_dir = BACKEND_DIR / "resources" / "uploaded_docs"
        if not upload_dir.exists():
            return {"files": []}
        
        files = []
        for file_path in upload_dir.iterdir():
            if file_path.is_file() and file_path.name != ".gitkeep":
                files.append({
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "path": str(file_path)
                })
        
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


# Dataset Generator Endpoints

# Global storage for job status (in production, use Redis or database)
job_status = {}

@router.post("/api/dataset/upload-document")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document for dataset generation."""
    print("="*80)
    print("📤 DATASET UPLOAD ENDPOINT CALLED")
    print("="*80)
    print(f"📁 File name: {file.filename}")
    print(f"📁 Content type: {file.content_type}")
    try:
        # Create the upload directory if it doesn't exist
        upload_dir = BACKEND_DIR / "resources" / "uploaded_docs"
        upload_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Upload directory: {upload_dir}")
        
        # Generate a unique filename to avoid conflicts
        file_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_dir / unique_filename
        print(f"📁 Saving to: {file_path}")
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = file_path.stat().st_size
        print(f"✅ File saved successfully: {file_size} bytes")
        
        result = {
            "message": "Document uploaded successfully",
            "file_id": unique_filename,
            "filename": file.filename,
            "file_path": str(file_path),
            "file_size": file_size
        }
        print(f"📤 Returning result: {result}")
        print("="*80)
        return result
    except Exception as e:
        print(f"❌ ERROR in upload_document: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*80)
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")

@router.get("/api/dataset/document-sections/{file_id}")
async def get_document_sections(file_id: str):
    """Get main sections from an uploaded document."""
    print("="*80)
    print("📋 GET DOCUMENT SECTIONS ENDPOINT CALLED")
    print(f"📁 File ID: {file_id}")
    print("="*80)
    try:
        file_path = Path("resources/uploaded_docs") / file_id
        print(f"📁 Looking for file: {file_path}")
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        print("✅ File found, initializing DatasetExtractor...")
        extractor = DatasetExtractor()
        print("✅ Extracting sections...")
        sections = extractor.get_main_sections(str(file_path))
        print(f"✅ Found {len(sections)} sections: {sections[:5]}...")  # Show first 5
        
        result = {
            "file_id": file_id,
            "sections": sections
        }
        print(f"📤 Returning result with {len(sections)} sections")
        print("="*80)
        return result
    except Exception as e:
        print(f"❌ ERROR in get_document_sections: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*80)
        raise HTTPException(status_code=500, detail=f"Failed to extract sections: {str(e)}")

@router.get("/api/dataset/document-subsections/{file_id}/{section}")
async def get_document_subsections(file_id: str, section: str):
    """Get subsections for a specific section."""
    try:
        file_path = Path("resources/uploaded_docs") / file_id
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document not found")
        
        extractor = DatasetExtractor()
        subsections = extractor.get_subsections(str(file_path), section)
        
        return {
            "file_id": file_id,
            "section": section,
            "subsections": subsections
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract subsections: {str(e)}")

@router.post("/api/dataset/set-working-directory")
async def set_working_directory(directory_path: str = Form(...)):
    """Set the working directory for dataset generation."""
    try:
        # Use Backend/resources/extract as default if path matches old dummy path
        # Project root: C:\Users\ChanduVangala\Desktop\RCA_Electron-main\RCA_Electron-main
        default_working_dir = BACKEND_DIR / "resources" / "extract"
        
        # Handle old dummy paths or use provided path
        if directory_path in [
            "C:/Users/ChanduVangala/Documents/GenAI/extract",
            "C:/Users/JayasviBattu/Downloads/GenAI_5G_TA-main/GenAI_5G_TA-main/extract"
        ]:
            # Use the project default directory
            working_dir = default_working_dir
        else:
            working_dir = Path(directory_path)
        
        if not working_dir.exists():
            working_dir.mkdir(parents=True, exist_ok=True)
        
        # Create necessary subdirectories
        (working_dir / "datasets").mkdir(exist_ok=True)
        (working_dir / "test_scripts").mkdir(exist_ok=True)
        
        return {
            "message": "Working directory set successfully",
            "directory": str(working_dir),
            "created_subdirs": ["datasets", "test_scripts"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set working directory: {str(e)}")

@router.post("/api/dataset/set-output-directory")
async def set_output_directory(directory_path: str = Form(...)):
    """Set the output directory for dataset generation."""
    try:
        # Use Backend/resources/output as default if path matches old dummy path
        # Project root: C:\Users\ChanduVangala\Desktop\RCA_Electron-main\RCA_Electron-main
        default_output_dir = BACKEND_DIR / "resources" / "output"
        
        # Handle old dummy paths or use provided path
        if directory_path in [
            "C:/Users/ChanduVangala/Documents/AgenticRAN-V8_azure_key/output",
            "C:/Users/JayasviBattu/Downloads/GenAI_5G_TA-main/GenAI_5G_TA-main/output"
        ]:
            # Use the project default directory
            output_dir = default_output_dir
        else:
            output_dir = Path(directory_path)
        
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            "message": "Output directory set successfully",
            "directory": str(output_dir)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set output directory: {str(e)}")

async def process_dataset_generation(job_id: str, file_id: str, section: str, subsection: str, 
                                  working_directory: str, output_directory: str):
    """Background task for dataset generation with detailed progress tracking."""
    try:
        job_status[job_id] = {
            "status": "processing",
            "progress": 0,
            "message": "Starting dataset generation...",
            "error": None,
            "output_path": None
        }
        
        file_path = BACKEND_DIR / "resources" / "uploaded_docs" / file_id
        extractor = DatasetExtractor()
        
        # Always use backend/resources/extract for storing extracted files (per user preference)
        # This ensures all extracted text files are stored in the backend resources folder
        working_dir = str(BACKEND_DIR / "resources" / "extract")
        output_dir = str(BACKEND_DIR / "resources" / "extract")
        
        # Ensure the extract directory exists
        Path(working_dir).mkdir(parents=True, exist_ok=True)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Using backend resources folder for extraction:")
        print(f"   Working directory: {working_dir}")
        print(f"   Output directory: {output_dir}")
        
        # Step 1: Extract text from subsection
        job_status[job_id]["progress"] = 10
        job_status[job_id]["message"] = "Extracting text from subsection..."
        
        # Step 2: Extract references and clauses
        job_status[job_id]["progress"] = 20
        job_status[job_id]["message"] = "Extracting 3GPP references and clauses..."
        
        # Step 3: Download specifications
        job_status[job_id]["progress"] = 30
        job_status[job_id]["message"] = "Downloading 3GPP specifications..."
        
        # Step 4: Check references
        job_status[job_id]["progress"] = 40
        job_status[job_id]["message"] = "Checking reference documents..."
        
        # Step 5: Recursive clause extraction
        job_status[job_id]["progress"] = 70
        job_status[job_id]["message"] = "Performing recursive clause extraction..."
        
        # Step 6: Build graph
        job_status[job_id]["progress"] = 90
        job_status[job_id]["message"] = "Building knowledge graph..."
        
        # Extract dataset with full recursive processing
        result = extractor.extract_dataset(
            str(file_path),
            section,
            subsection,
            output_dir,
            working_dir
        )
        
        # Step 7: Complete
        job_status[job_id]["progress"] = 100
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["message"] = f"Dataset generation completed! Created {result.get('clause_files_count', 0)} clause files + 2 main files"
        job_status[job_id]["output_path"] = result["output_file"]
        job_status[job_id]["result"] = {
            "references_found": len(result["references"]),
            "clauses_found": len(result["clauses"]),
            "present_references": len(result["present_references"]),
            "missing_references": len(result["missing_references"]),
            "output_file": result["output_file"],
            "total_content_file": result.get("total_content_file", ""),
            "clause_files_count": result.get("clause_files_count", 0),
            "files_created": result.get("files_created", {})
        }
        
    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["error"] = str(e)
        job_status[job_id]["message"] = f"Dataset generation failed: {str(e)}"
        job_status[job_id]["progress"] = 0

@router.post("/api/dataset/generate")
async def generate_dataset(
    background_tasks: BackgroundTasks,
    file_id: str = Form(...),
    section: str = Form(...),
    subsection: str = Form(...),
    working_directory: str = Form(...),
    output_directory: str = Form(...)
):
    """Start dataset generation process."""
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Validate inputs
        file_path = Path("resources/uploaded_docs") / file_id
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Start background task
        background_tasks.add_task(
            process_dataset_generation,
            job_id, file_id, section, subsection, working_directory, output_directory
        )
        
        return {
            "job_id": job_id,
            "status": "started",
            "message": "Dataset generation started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start dataset generation: {str(e)}")

@router.get("/api/dataset/status/{job_id}")
async def get_dataset_status(job_id: str):
    """Get the status of a dataset generation job."""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_status[job_id]

@router.get("/api/dataset/download/{job_id}")
async def download_dataset(job_id: str):
    """Download the generated dataset."""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_status[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Dataset generation not completed")
    
    # Return download information
    return {
        "job_id": job_id,
        "status": "completed",
        "download_url": f"/api/dataset/files/{job_id}",
        "result": job.get("result", {})
    }

@router.get("/api/dataset/files/{job_id}")
async def get_dataset_files(job_id: str):
    """Get the actual dataset files."""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_status[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Dataset generation not completed")
    
    # Return file information
    result = job.get("result", {})
    return {
        "files": [
            {
                "name": "output.json",
                "path": result.get("output_file", ""),
                "type": "graph_data"
            }
        ],
        "summary": {
            "references_found": result.get("references_found", 0),
            "clauses_found": result.get("clauses_found", 0),
            "present_references": result.get("present_references", 0),
            "missing_references": result.get("missing_references", 0)
        }
    }


# ===== NEW SIMPLIFIED PYQT-STYLE ENDPOINT =====
@router.post("/api/dataset/extract-pyqt-style")
async def extract_dataset_pyqt_style(
    file_id: str = Form(...),
    section: str = Form(...),
    subsection: str = Form(...),
    working_directory: str = Form(...),
    output_directory: str = Form(...)
):
    """
    Simple synchronous dataset extraction - EXACT REPLICA of PyQt flow.
    This directly calls the dataset generator without background tasks or status tracking.
    """
    try:
        print("=" * 60)
        print("STARTING PYQT-STYLE DATASET EXTRACTION")
        print("=" * 60)
        
        # Validate inputs
        file_path = Path("resources/uploaded_docs") / file_id
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Always use backend/resources/extract for storing extracted files (per user preference)
        # This ensures all extracted text files are stored in the backend resources folder
        working_dir = str(Path("resources") / "extract")
        output_dir = str(Path("resources") / "extract")
        
        # Ensure the extract directory exists
        Path(working_dir).mkdir(parents=True, exist_ok=True)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Using backend resources folder for extraction:")
        print(f"   Working directory: {working_dir}")
        print(f"   Output directory: {output_dir}")
        
        print(f"File: {file_path}")
        print(f"Section: {section}")
        print(f"Subsection: {subsection}")
        print(f"Working Directory: {working_dir}")
        print(f"Output Directory: {output_dir}")
        
        # Initialize extractor
        extractor = DatasetExtractor()
        
        # Call the PyQt-style extraction method (synchronous)
        result = extractor.extract_dataset_pyqt_style(
            str(file_path),
            section,
            subsection,
            output_dir,
            working_dir
        )
        
        print("=" * 60)
        print("DATASET EXTRACTION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
        # Return results immediately (no job tracking needed)
        return {
            "success": True,
            "message": result["message"],
            "output_file": result["output_file"],
            "total_content_file": result["total_content_file"],
            "clause_files_count": result["clause_files_count"],
            "references_found": len(result["references"]),
            "clauses_found": len(result["clauses"]),
            "present_references": len(result["present_references"]),
            "missing_references": len(result["missing_references"]),
            "files_created": result["files_created"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in dataset extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Dataset extraction failed: {str(e)}")


# Pydantic Models for Test Script Generator
class TestScriptVariables(BaseModel):
    domain: Optional[str] = None
    system_type: Optional[str] = None
    primary_feature: Optional[str] = None
    connection_method: Optional[str] = None
    login_credentials: Optional[str] = None
    access_mode: Optional[str] = None
    language: Optional[str] = None

class TestScriptRequest(BaseModel):
    prompt_key: str
    text_content: str
    variables: Optional[TestScriptVariables] = None
    custom_prompt: Optional[str] = None

class TestScriptResponse(BaseModel):
    success: bool
    generated_script: str
    file_path: Optional[str] = None
    message: Optional[str] = None

class PromptTemplateResponse(BaseModel):
    success: bool
    templates: Dict[str, Any]
    message: Optional[str] = None

class RefineScriptRequest(BaseModel):
    text_content: str
    new_prompt: str
    previous_response: Optional[str] = None

class TestScriptSaveRequest(BaseModel):
    content: str
    template_type: str
    language: str = "Python"

class TemplateSaveRequest(BaseModel):
    template_name: str
    template_content: str

class TemplateDeleteRequest(BaseModel):
    template_name: str

class OpenFolderRequest(BaseModel):
    folder_path: str

class TestGenerationHistoryRequest(BaseModel):
    template_name: str
    prompt: str
    output: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BugDiscoveryHistoryRequest(BaseModel):
    log_file: str
    output: str
    analysis_type: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Initialize Test Script Generator
test_script_generator = TestScriptGenerator()

# ----------------------
# SQLite logging helpers
# ----------------------
_TSG_DB_PATH = BACKEND_DIR / "resources" / "TestScriptGenerator" / "tsg_history.db"

def _ensure_tsg_db() -> None:
    try:
        _TSG_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(_TSG_DB_PATH) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_name TEXT,
                    prompt TEXT,
                    response TEXT,
                    stored_at TEXT,
                    file_path TEXT
                )
                """
            )
            conn.commit()
    except Exception as e:
        print(f"⚠️ Could not initialize Test Script Generator DB: {e}")

def _log_tsg_generation(template_name: str, prompt: str, response: str, file_path: str = None) -> None:
    try:
        _ensure_tsg_db()
        with sqlite3.connect(_TSG_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO generations (template_name, prompt, response, stored_at, file_path) VALUES (?, ?, ?, ?, ?)",
                (
                    template_name or "",
                    prompt or "",
                    response or "",
                    datetime.now().isoformat(timespec="seconds"),
                    file_path or "",
                ),
            )
            conn.commit()
    except Exception as e:
        print(f"⚠️ Failed to log Test Script generation to SQLite: {e}")

# Test Script Generator Endpoints
@router.get("/api/test-script/prompts")
async def get_prompt_templates():
    """Get available prompt templates"""
    try:
        prompts = test_script_generator.get_prompts()
        return PromptTemplateResponse(
            success=True,
            templates=prompts,
            message="Prompt templates retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving prompts: {str(e)}")

@router.post("/api/test-script/generate")
async def generate_test_script(request: TestScriptRequest):
    """Generate test script based on prompt and dataset"""
    try:
        # Set variables if provided
        if request.variables:
            test_script_generator.set_variables(
                domain=request.variables.domain,
                system_type=request.variables.system_type,
                primary_feature=request.variables.primary_feature,
                connection_method=request.variables.connection_method,
                login_credentials=request.variables.login_credentials,
                access_mode=request.variables.access_mode,
                language=request.variables.language
            )
        
        # Handle custom prompt
        if request.prompt_key == "Custom" and request.custom_prompt:
            test_script_generator.latest_custom_prompt = request.custom_prompt
            selected_prompt = request.custom_prompt
        else:
            # Get prompt from templates (includes any saved modifications)
            prompts = test_script_generator.get_prompts()
            print(f"🔍 DEBUG: Getting template '{request.prompt_key}' from backend prompts")
            print(f"🔍 DEBUG: Template preview (first 100 chars): {str(prompts.get(request.prompt_key, 'NOT FOUND'))[:100]}...")
            
            if request.prompt_key not in prompts:
                raise HTTPException(status_code=400, detail=f"Unknown prompt template: {request.prompt_key}")
            
            if request.prompt_key == "Test Case" and isinstance(prompts[request.prompt_key], dict):
                # Merge system and user prompts
                system_prompt = prompts[request.prompt_key].get("System Prompt", "")
                user_prompt = prompts[request.prompt_key].get("User Prompt", "")
                selected_prompt = f"{system_prompt}\n\n{user_prompt}"
            else:
                selected_prompt = prompts[request.prompt_key]
            
            print(f"✅ Using template from backend (length: {len(selected_prompt)} chars)")
        
        # Set current prompt key
        test_script_generator.current_prompt_key = request.prompt_key
        
        # Generate test script
        generated_script = test_script_generator.generate_response_from_text(
            request.text_content, 
            selected_prompt
        )
        
        # Save to file
        output_dir = BACKEND_DIR / "resources" / "TestScriptGenerator"
        success, file_path = test_script_generator.save_response_to_file(
            generated_script, 
            str(output_dir)
        )
        # Log to SQLite (template name, prompt, response, timestamp, file path)
        try:
            _log_tsg_generation(
                template_name=request.prompt_key,
                prompt=selected_prompt,
                response=generated_script,
                file_path=file_path if success else None,
            )
        except Exception as e:
            print(f"⚠️ Logging to SQLite failed: {e}")
        
        history_filename = None
        normalized_prompt_key = (request.prompt_key or "").strip().lower()
        if normalized_prompt_key == "test case":
            history_filename = "test_case_history.json"
        elif normalized_prompt_key == "test script":
            history_filename = "test_script_history.json"

        if history_filename:
            try:
                record_metadata = {}
                if request.variables:
                    try:
                        record_metadata["variables"] = request.variables.dict(exclude_none=True)
                    except Exception:
                        record_metadata["variables"] = {}
                if success and file_path:
                    record_metadata["file_path"] = file_path

                append_history_record(
                    history_filename,
                    {
                        "template_name": request.prompt_key,
                        "prompt": selected_prompt,
                        "output": generated_script,
                        "metadata": record_metadata,
                    },
                )
            except Exception as history_error:
                print(f"⚠️ Failed to append history to {history_filename}: {history_error}")

        return TestScriptResponse(
            success=True,
            generated_script=generated_script,
            file_path=file_path if success else None,
            message="Test script generated successfully"
        )
        
    except Exception as e:
        print(f"❌ ERROR in generate_test_script endpoint: {str(e)}")
        print(f"❌ Request data: prompt_key={request.prompt_key}, text_content_length={len(request.text_content) if request.text_content else 0}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error generating test script: {str(e)}")

# ----------------------
# History Query Endpoints
# ----------------------
class HistoryQuery(BaseModel):
    # High-level activity shortcut: one of
    #   "today", "last_7_days", "last_30_days", "last_90_days", "all_time"
    activity_time: Optional[str] = None
    days: Optional[int] = None  # e.g., last N days
    start_date: Optional[str] = None  # ISO date "YYYY-MM-DD"
    end_date: Optional[str] = None    # ISO date "YYYY-MM-DD"
    template_name: Optional[str] = None  # e.g., "Test Script", "Test Case", "Refine"
    offset: Optional[int] = None  # optional when limit is None
    limit: Optional[int] = None   # if None → return all rows


class UserHistoryRequest(BaseModel):
    time_period: Optional[str] = "all"
    activity_type: Optional[str] = "all"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: Optional[int] = 100


_USER_HISTORY_ACTIVITY_MAP: Dict[str, Dict[str, Any]] = {
    "test-script": {
        "filename": "test_script_history.json",
        "label": "Test Script Generation",
    },
    "test-case": {
        "filename": "test_case_history.json",
        "label": "Test Case Creation",
    },
    "bug-analysis": {
        "filename": "bug_discovery_history.json",
        "label": "Bug Discovery Analysis",
    },
    "code-assistant": {
        "filename": "code_assistant_history.json",
        "label": "Code Assistant",
    },
    # Legacy mapping for prompt-templates
    "prompt-templates": {
        "filename": "code_assistant_history.json",
        "label": "Code Assistant",
    },
}


def _resolve_history_time_range(query: UserHistoryRequest) -> Dict[str, Optional[datetime]]:
    now = datetime.utcnow()
    period = (query.time_period or "all").lower()
    start: Optional[datetime] = None
    end: Optional[datetime] = None

    if period in {"today"}:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period in {"7days", "last_7_days"}:
        start = now - timedelta(days=7)
    elif period in {"30days", "last_30_days"}:
        start = now - timedelta(days=30)
    elif period in {"90days", "last_90_days"}:
        start = now - timedelta(days=90)

    # Explicit start/end override the derived ones
    if query.start_date:
        try:
            start = datetime.fromisoformat(f"{query.start_date}T00:00:00")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid start_date value: {query.start_date}")
    if query.end_date:
        try:
            end = datetime.fromisoformat(f"{query.end_date}T23:59:59")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid end_date value: {query.end_date}")

    return {"start": start, "end": end}


def _build_history_entry(
    raw: Dict[str, Any],
    activity_key: str,
    activity_meta: Dict[str, Any],
    source_filename: str,
) -> Dict[str, Any]:
    timestamp_val = _parse_history_timestamp(raw.get("timestamp"))

    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    output_value = raw.get("output")
    if isinstance(output_value, (dict, list)):
        try:
            output_text = json.dumps(output_value, ensure_ascii=False)
        except (TypeError, ValueError):
            output_text = str(output_value)
    elif output_value is None:
        output_text = ""
    else:
        output_text = str(output_value).strip()

    output_truncated = len(output_text) > 400
    output_preview = output_text[:400]

    if activity_key == "test-script":
        title = raw.get("template_name") or "Test Script Generation"
        summary = f"Generated test script using template '{title}'."
    elif activity_key == "test-case":
        title = raw.get("template_name") or "Test Case Creation"
        summary = f"Generated test case using template '{title}'."
    elif activity_key == "bug-analysis":
        title = raw.get("metadata", {}).get("analysis_type") or raw.get("log_file") or "Bug Analysis"
        summary = f"Bug discovery analysis for {title}."
    elif activity_key == "code-assistant" or raw.get("activity_type") == "git-commit":
        # Handle code assistant history entries (git commits)
        title = raw.get("title") or raw.get("record", {}).get("analysis_filename") or "Git Commit"
        commit_msg = raw.get("record", {}).get("commit_message", "")
        if commit_msg:
            # Extract first line of commit message (usually the subject)
            first_line = commit_msg.split("\n")[0].strip()
            summary = f"Git commit: {first_line[:50]}..." if len(first_line) > 50 else f"Git commit: {first_line}"
        else:
            summary = "Git Commit"
    else:
        title = raw.get("template_name") or activity_meta.get("label") or "User Activity"
        summary = title

    # For code-assistant entries, the record structure is nested
    # If raw has a 'record' field, use it directly; otherwise use raw as the record
    if activity_key == "code-assistant" and "record" in raw:
        record_data = raw.get("record", {})
    else:
        record_data = raw
    
    return {
        "activity_type": activity_key,
        "activity_label": activity_meta.get("label") or raw.get("activity_label"),
        "timestamp": timestamp_val.isoformat() if timestamp_val else None,
        "title": title,
        "summary": summary,
        "metadata": metadata,
        "output_preview": output_preview,
        "output_truncated": output_truncated,
        "source_file": source_filename,
        "record": record_data,
    }


def _collect_user_history(query: UserHistoryRequest) -> List[Dict[str, Any]]:
    time_bounds = _resolve_history_time_range(query)
    selected_activity = (query.activity_type or "all").lower()

    entries: List[Dict[str, Any]] = []
    for activity_key, activity_meta in _USER_HISTORY_ACTIVITY_MAP.items():
        if selected_activity not in {"all", activity_key}:
            continue

        filename = activity_meta.get("filename")
        if not filename:
            # Skip activities that do not have a backing history file yet
            continue

        try:
            history_rows = load_history_entries(filename)
            # If file doesn't exist, load_history_entries returns empty list, which is fine
        except Exception as exc:
            # Log but don't fail - just skip this activity type
            print(f"⚠️ Warning: Could not read history file '{filename}': {exc}")
            continue

        for raw in history_rows:
            entry = _build_history_entry(raw, activity_key, activity_meta, filename)
            timestamp_str = entry.get("timestamp")
            timestamp_dt = datetime.fromisoformat(timestamp_str) if timestamp_str else None

            if time_bounds["start"] and timestamp_dt and timestamp_dt < time_bounds["start"]:
                continue
            if time_bounds["end"] and timestamp_dt and timestamp_dt > time_bounds["end"]:
                continue

            entries.append(entry)

    entries.sort(
        key=lambda item: (
            datetime.fromisoformat(item["timestamp"]) if item.get("timestamp") else datetime.min
        ),
        reverse=True,
    )

    if query.limit is not None and query.limit > 0:
        entries = entries[: query.limit]

    return entries

@router.post("/api/test-script/history")
async def get_test_script_history(query: HistoryQuery):
    """Return history rows from SQLite with optional time and template filters.

    - If days is provided, filters rows with stored_at >= now - days
    - Else, if start_date/end_date provided, uses that range (inclusive)
    - If template_name provided, filters by template_name
    - Supports pagination via offset/limit
    """
    try:
        _ensure_tsg_db()
        params: List[Any] = []
        where_clauses: List[str] = []

        # Time filtering (priority: activity_time > days > start/end)
        if query.activity_time:
            now = datetime.now()
            if query.activity_time == "today":
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end = now.replace(hour=23, minute=59, second=59, microsecond=0)
                where_clauses.append("stored_at >= ?")
                params.append(start.isoformat(timespec="seconds"))
                where_clauses.append("stored_at <= ?")
                params.append(end.isoformat(timespec="seconds"))
            elif query.activity_time == "last_7_days":
                threshold = now - timedelta(days=7)
                where_clauses.append("stored_at >= ?")
                params.append(threshold.isoformat(timespec="seconds"))
            elif query.activity_time == "last_30_days":
                threshold = now - timedelta(days=30)
                where_clauses.append("stored_at >= ?")
                params.append(threshold.isoformat(timespec="seconds"))
            elif query.activity_time == "last_90_days":
                threshold = now - timedelta(days=90)
                where_clauses.append("stored_at >= ?")
                params.append(threshold.isoformat(timespec="seconds"))
            elif query.activity_time == "all_time":
                pass  # no time filter
        elif query.days is not None and query.days > 0:
            threshold = datetime.now() - timedelta(days=query.days)
            where_clauses.append("stored_at >= ?")
            params.append(threshold.isoformat(timespec="seconds"))
        else:
            if query.start_date:
                where_clauses.append("stored_at >= ?")
                params.append(f"{query.start_date}T00:00:00")
            if query.end_date:
                where_clauses.append("stored_at <= ?")
                params.append(f"{query.end_date}T23:59:59")

        # Template filter
        if query.template_name:
            where_clauses.append("template_name = ?")
            params.append(query.template_name)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Fetch rows and total count
        base_select = (
            "SELECT id, template_name, prompt, response, stored_at, file_path "
            "FROM generations"
            f"{where_sql} "
            "ORDER BY stored_at DESC, id DESC "
        )
        count_sql = f"SELECT COUNT(*) FROM generations{where_sql}"

        with sqlite3.connect(_TSG_DB_PATH) as conn:
            # Count
            cur = conn.execute(count_sql, params)
            total = cur.fetchone()[0]

            # Page or full
            if query.limit is None:
                cur = conn.execute(base_select, params)
            else:
                # Ensure offset has a default when limit provided
                eff_offset = query.offset or 0
                sql = base_select + "LIMIT ? OFFSET ?"
                page_params = params + [query.limit, eff_offset]
                cur = conn.execute(sql, page_params)
            rows = [
                {
                    # omit internal id in API response
                    "template_name": r[1],
                    "prompt": r[2],
                    "response": r[3],
                    "stored_at": r[4],
                    "file_path": r[5],
                }
                for r in cur.fetchall()
            ]

        return {
            "success": True,
            "total": total,
            "rows": rows,
            "offset": query.offset if query.limit is not None else None,
            "limit": query.limit,
        }
    except Exception as e:
        print(f"❌ Error querying history: {e}")
        raise HTTPException(status_code=500, detail=f"Error querying history: {str(e)}")


@router.post("/api/history/user")
async def get_user_history(request: UserHistoryRequest):
    try:
        entries = _collect_user_history(request)
        return {
            "success": True,
            "count": len(entries),
            "entries": entries,
            "applied_filters": {
                "time_period": request.time_period or "all",
                "activity_type": request.activity_type or "all",
                "start_date": request.start_date,
                "end_date": request.end_date,
                "limit": request.limit,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"❌ Failed to load user history: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to load user history: {exc}")

@router.post("/api/test-script/refine")
async def refine_test_script(request: RefineScriptRequest):
    """Refine existing test script with new prompt"""
    try:
        refined_script = test_script_generator.generate_with_new_prompt(
            request.text_content,
            request.new_prompt,
            request.previous_response
        )
        
        # Log to SQLite
        try:
            _log_tsg_generation(
                template_name="Refine",
                prompt=request.new_prompt,
                response=refined_script,
            )
        except Exception as e:
            print(f"⚠️ Logging refine to SQLite failed: {e}")

        return TestScriptResponse(
            success=True,
            generated_script=refined_script,
            message="Test script refined successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refining test script: {str(e)}")

@router.post("/api/test-script/upload-reference")
async def upload_reference_code(file: UploadFile = File(...)):
    """Upload reference code file"""
    try:
        # Create upload directory
        upload_dir = Path("resources/reference_code")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process with test script generator
        file_name = test_script_generator.upload_reference_code(str(file_path))
        
        return {
            "success": True,
            "filename": file_name,
            "message": "Reference code uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading reference code: {str(e)}")

@router.post("/api/test-script/load-dataset")
async def load_test_dataset(files: List[UploadFile] = File(...)):
    """Load dataset from multiple files for test script generation"""
    try:
        # Create upload directory
        upload_dir = Path("resources/datasets")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_paths = []
        for file in files:
            # Generate unique filename
            file_extension = Path(file.filename).suffix if file.filename else ""
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = upload_dir / unique_filename
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_paths.append(str(file_path))
        
        # Load dataset
        dataset_content = test_script_generator.load_dataset(file_paths)
        
        return {
            "success": True,
            "content": dataset_content,
            "files_loaded": len(file_paths),
            "message": "Dataset loaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading dataset: {str(e)}")

@router.get("/api/test-script/test-types")
async def get_test_types():
    """Get available test types for generation"""
    test_types = {
        "unit": "Unit Tests",
        "integration": "Integration Tests", 
        "performance": "Performance Tests",
        "conformance": "Conformance Tests"
    }
    return {
        "success": True,
        "test_types": test_types,
        "message": "Test types retrieved successfully"
    }

@router.post("/api/test-script/generate-by-type")
async def generate_test_by_type(
    test_type: str = Form(...),
    input_text: str = Form(...),
    output_directory: Optional[str] = Form(None)
):
    """Generate test script by specific test type"""
    try:
        generated_script, file_path = test_script_generator.handle_test_generation(
            test_type,
            input_text,
            output_directory
        )
        
        # Log to SQLite (use test_type as template name)
        try:
            _log_tsg_generation(
                template_name=test_type,
                prompt=f"Auto-generated by type: {test_type}",
                response=generated_script,
                file_path=file_path,
            )
        except Exception as e:
            print(f"⚠️ Logging by-type generation to SQLite failed: {e}")

        return TestScriptResponse(
            success=True,
            generated_script=generated_script,
            file_path=file_path,
            message=f"{test_type.title()} test script generated successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating {test_type} test: {str(e)}")


# Save Test Script Response endpoint
@router.post("/api/save-test-script")
async def save_test_script_response(request: TestScriptSaveRequest):
    """Save a generated test script response to the Resources folder."""
    try:
        # Create TestScriptGenerator folder if it doesn't exist
        output_dir = BACKEND_DIR / "resources" / "TestScriptGenerator"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file extension based on language
        file_extension = ".py"  # default
        if request.language == "C (Coming Soon)":
            file_extension = ".c"
        elif request.language == "C++ (Coming Soon)":
            file_extension = ".cpp"
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{request.template_type}_{timestamp}{file_extension}"
        file_path = output_dir / filename
        
        # Save the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(request.content)
        
        return {
            "success": True,
            "file_path": str(file_path),
            "filename": filename,
            "message": f"Test script saved successfully to {file_path}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving test script: {str(e)}")

@router.post("/api/test-script/save-template")
async def save_template(request: TemplateSaveRequest):
    """Save or update a template prompt in the backend."""
    try:
        print("=" * 80)
        print("💾 SAVE TEMPLATE ENDPOINT CALLED")
        print("=" * 80)
        print(f"💾 Template name: '{request.template_name}'")
        print(f"💾 Template content length: {len(request.template_content)} chars")
        print(f"💾 Template preview (first 100 chars): {request.template_content[:100]}...")
        
        success, message = test_script_generator.save_prompt_to_file(
            request.template_name,
            request.template_content
        )
        
        print(f"✅ Template save result: success={success}, message={message}")
        print("=" * 80)
        
        return {
            "success": success,
            "message": message,
            "template_name": request.template_name
        }
        
    except Exception as e:
        print("=" * 80)
        print("❌ ERROR IN SAVE TEMPLATE ENDPOINT")
        print("=" * 80)
        print(f"❌ Exception type: {type(e).__name__}")
        print(f"❌ Exception message: {str(e)}")
        import traceback
        print(f"❌ Full traceback:")
        traceback.print_exc()
        print("=" * 80)
        raise HTTPException(status_code=500, detail=f"Error saving template: {str(e)}")

@router.delete("/api/test-script/delete-template")
async def delete_template(request: TemplateDeleteRequest):
    """Delete a custom template from the backend."""
    try:
        print(f"🗑️ Deleting template: '{request.template_name}'")
        
        success, message = test_script_generator.delete_custom_template(request.template_name)
        
        print(f"✅ Template delete result: success={success}, message={message}")
        
        return {
            "success": success,
            "message": message,
            "template_name": request.template_name
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting template: {str(e)}")

@router.get("/api/test-script/custom-templates")
async def get_custom_templates():
    """Get list of custom template names."""
    try:
        custom_names = test_script_generator.get_custom_template_names()
        
        return {
            "success": True,
            "custom_templates": custom_names,
            "message": f"Found {len(custom_names)} custom templates"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting custom templates: {str(e)}")


# Test Deployment Endpoints

# Global storage for deployment job status
deployment_job_status = {}

class DeploymentConfig(BaseModel):
    source_directory: str
    ubuntu_host: str
    ubuntu_user: str
    ubuntu_password: str
    destination_directory: str

class DeploymentRequest(BaseModel):
    config_name: Optional[str] = "default"
    custom_config: Optional[DeploymentConfig] = None

class DeploymentResponse(BaseModel):
    success: bool
    job_id: Optional[str] = None
    message: str
    file_transferred: Optional[str] = None

async def execute_deployment_process(job_id: str, config: DeploymentConfig):
    """Background task for deployment execution (runs test_deployment.py as subprocess, matching PyQt behavior)."""
    try:
        deployment_job_status[job_id] = {
            "status": "processing",
            "progress": 0,
            "message": "Starting deployment...",
            "error": None,
            "file_transferred": None
        }
        
        # Get the path to test_deployment.py script (matching PyQt approach)
        # The script is located at Backend/app/services/test_deployment.py
        current_dir = Path(__file__).parent.parent
        script_path = current_dir / "services" / "test_deployment.py"
        
        if not script_path.exists():
            deployment_job_status[job_id]["status"] = "failed"
            deployment_job_status[job_id]["error"] = f"Deployment script not found: {script_path}"
            deployment_job_status[job_id]["message"] = f"Deployment script not found: {script_path}"
            return
        
        deployment_job_status[job_id]["progress"] = 25
        deployment_job_status[job_id]["message"] = "Running deployment script..."
        
        # Update the script with the configuration before running (if needed)
        # Or pass config as environment variables or arguments
        # For now, the script uses hardcoded values, so we'll just run it
        # The script will handle the connection itself
        
        import subprocess
        import sys
        
        # Run test_deployment.py as subprocess (matching PyQt: lines 4269-4275)
        # Use the source directory from config (absolute path)
        config_source_dir = config.source_directory if config and config.source_directory else None
        
        if not config_source_dir:
            # Fall back to default path
            config_source_dir = str(Path("resources/TestScriptGenerator/test_suite/test_script").absolute())
        
        # Ensure the path is absolute
        if not os.path.isabs(config_source_dir):
            config_source_dir = os.path.abspath(config_source_dir)
        
        # Verify the directory exists before running
        if not os.path.exists(config_source_dir):
            deployment_job_status[job_id]["status"] = "failed"
            deployment_job_status[job_id]["error"] = f"Source directory does not exist: {config_source_dir}"
            deployment_job_status[job_id]["message"] = f"Source directory does not exist: {config_source_dir}"
            return
        
        deployment_job_status[job_id]["progress"] = 50
        deployment_job_status[job_id]["message"] = f"Executing deployment script: {script_path.name}\nSource directory: {config_source_dir}"
        
        # Prepare configuration as JSON to pass to the script
        config_dict = {
            "source_directory": config_source_dir,
            "ubuntu_host": config.ubuntu_host if config else "10.138.77.131",
            "ubuntu_user": config.ubuntu_user if config else "tcs",
            "ubuntu_password": config.ubuntu_password if config else "tcs@12345",
            "destination_directory": config.destination_directory if config else "/home/tcs/chandu/Genai/"
        }
        config_json = json.dumps(config_dict)
        
        # Run the script with source directory and config JSON as arguments
        # The script will parse the config and use it for deployment
        process = subprocess.Popen(
            [sys.executable, str(script_path), config_source_dir, config_json],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,  # Don't use shell on Windows
            text=True,
            cwd=str(script_path.parent)  # Run from the script's directory
        )
        
        deployment_job_status[job_id]["progress"] = 75
        deployment_job_status[job_id]["message"] = "Deployment in progress..."
        
        # Wait for the process to complete
        stdout, stderr = process.communicate()
        
        # Check if deployment was successful (matching PyQt: lines 4279-4285)
        if process.returncode == 0 and "Error" not in stdout and "Error" not in stderr:
            deployment_job_status[job_id]["status"] = "completed"
            deployment_job_status[job_id]["progress"] = 100
            deployment_job_status[job_id]["message"] = "Deployment completed successfully"
            deployment_job_status[job_id]["output"] = stdout
            # Extract file name from output if available
            if stdout:
                # Look for transferred file name in output
                for line in stdout.split('\n'):
                    if "Transferred" in line or "transferred" in line:
                        # Try to extract file name
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if "transferred" in part.lower() and i + 1 < len(parts):
                                deployment_job_status[job_id]["file_transferred"] = parts[i + 1]
                                break
        else:
            # Deployment failed
            error_message = stderr if stderr else stdout
            if not error_message:
                error_message = f"Deployment script returned exit code {process.returncode}"
            
            deployment_job_status[job_id]["status"] = "failed"
            deployment_job_status[job_id]["error"] = error_message
            deployment_job_status[job_id]["message"] = f"Deployment failed: {error_message}"
            deployment_job_status[job_id]["output"] = stdout
            deployment_job_status[job_id]["stderr"] = stderr
        
    except FileNotFoundError as e:
        deployment_job_status[job_id]["status"] = "failed"
        deployment_job_status[job_id]["error"] = f"Deployment script not found: {str(e)}"
        deployment_job_status[job_id]["message"] = f"Deployment script not found: {str(e)}"
    except Exception as e:
        deployment_job_status[job_id]["status"] = "failed"
        deployment_job_status[job_id]["error"] = str(e)
        deployment_job_status[job_id]["message"] = f"Deployment failed: {str(e)}"
        deployment_job_status[job_id]["progress"] = 0

@router.post("/api/deployment/deploy")
async def deploy_test_scripts(request: DeploymentRequest, background_tasks: BackgroundTasks):
    """Deploy test scripts to target environment."""
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Use default configuration if no custom config provided
        if request.custom_config:
            config = request.custom_config
        else:
            # Default configuration pointing to our test script output directory
            # Point to the test_script subdirectory where scripts are actually saved
            config = DeploymentConfig(
                source_directory=str(Path("resources/TestScriptGenerator/test_suite/test_script").absolute()),
                ubuntu_host="10.138.77.131",
                ubuntu_user="tcs",
                ubuntu_password="tcs@12345",
                destination_directory="/home/tcs/chandu/Genai/"
            )
        
        # Start background deployment task
        background_tasks.add_task(execute_deployment_process, job_id, config)
        
        return DeploymentResponse(
            success=True,
            job_id=job_id,
            message="Deployment started successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting deployment: {str(e)}")

@router.get("/api/deployment/status/{job_id}")
async def get_deployment_status(job_id: str):
    """Get deployment status."""
    if job_id not in deployment_job_status:
        raise HTTPException(status_code=404, detail="Deployment job not found")
    
    return deployment_job_status[job_id]

@router.get("/api/deployment/configs")
async def get_deployment_configs():
    """Get available deployment configurations."""
        configs = {
        "default": {
            "name": "Default Configuration",
            "source_directory": str(Path("resources/TestScriptGenerator").absolute()),
            "ubuntu_host": "10.138.77.131",
            "ubuntu_user": "tcs",
            "destination_directory": "/home/tcs/chandu/Genai/",
            "description": "Deploy latest test scripts to default Ubuntu server"
        }
    }
    
    return {
        "success": True,
        "configs": configs,
        "message": "Deployment configurations retrieved successfully"
    }

@router.get("/api/deployment/test-connection")
async def test_deployment_connection():
    """Test connection to deployment server."""
    try:
        import paramiko
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Test with default configuration
        ssh.connect("10.138.77.131", username="tcs", password="tcs@12345", timeout=10)
        ssh.close()
        
        return {
            "success": True,
            "message": "Connection test successful",
            "server": "10.138.77.131",
            "user": "tcs"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "server": "10.138.77.131",
            "user": "tcs"
        }
@router.post("/api/deployment/upload-config")
async def upload_deployment_config(file: UploadFile = File(...)):
    """Upload deployment configuration file."""
    try:
        # Validate file extension - accept common config file types
        allowed_extensions = ['.cfg', '.conf', '.ini', '.yaml', '.yml', '.json']
        if not file.filename or not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            raise HTTPException(status_code=400, detail="Only config files (.cfg, .conf, .ini, .yaml, .json) are allowed")
        
        # Create upload directory
        upload_dir = Path("resources/deployment_configs")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename to avoid conflicts
        file_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "message": "Deployment configuration uploaded successfully",
            "file_id": unique_filename,
            "filename": file.filename,
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload deployment config: {str(e)}")

@router.get("/api/deployment/config-files")
async def get_deployment_config_files():
    """Get list of uploaded deployment configuration files."""
    try:
        config_dir = Path("resources/deployment_configs")
        
        if not config_dir.exists():
            return {"files": []}
        
        # Accept common config file extensions
        allowed_extensions = ['.cfg', '.conf', '.ini', '.yaml', '.yml', '.json']
        
        files = []
        for file_path in config_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in allowed_extensions:
                files.append({
                    "file_id": file_path.name,
                    "filename": file_path.stem + file_path.suffix,
                    "upload_date": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "file_size": file_path.stat().st_size
                })
        
        # Sort by upload date (newest first)
        files.sort(key=lambda x: x["upload_date"], reverse=True)
        
        return {"files": files}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list config files: {str(e)}")
# Test Execution Endpoints

# Global storage for test execution job status
test_execution_job_status = {}

class TestExecutionConfig(BaseModel):
    jenkins_server_url: str
    jenkins_username: str
    jenkins_password: str
    job_name: str

class TestExecutionRequest(BaseModel):
    config_name: Optional[str] = "default"
    custom_config: Optional[TestExecutionConfig] = None

class TestExecutionResponse(BaseModel):
    success: bool
    job_id: Optional[str] = None
    message: str
    build_result: Optional[str] = None

async def execute_test_execution_process(job_id: str, config: TestExecutionConfig):
    """Background task for test execution (runs jenkins_build_trigger_with_results.py as subprocess)."""
    try:
        test_execution_job_status[job_id] = {
            "status": "processing",
            "progress": 0,
            "message": "Starting test execution...",
            "error": None,
            "build_result": None,
            "build_number": None,
            "output": ""
        }
        
        # Get the path to Jenkins trigger script
        current_dir = Path(__file__).parent.parent
        script_path = current_dir / "services" / "jenkins_build_trigger_with_rtesults.py"
        
        if not script_path.exists():
            test_execution_job_status[job_id]["status"] = "failed"
            test_execution_job_status[job_id]["error"] = f"Test execution script not found: {script_path}"
            test_execution_job_status[job_id]["message"] = f"Test execution script not found: {script_path}"
            return
        
        test_execution_job_status[job_id]["progress"] = 25
        test_execution_job_status[job_id]["message"] = "Connecting to Jenkins server..."
        
        import subprocess
        import sys
        import re
        
        # Prepare configuration as JSON to pass to the script
        config_dict = {
            "jenkins_server_url": config.jenkins_server_url if config else "http://10.138.77.71:8080/",
            "jenkins_username": config.jenkins_username if config else "chandu",
            "jenkins_password": config.jenkins_password if config else "tcs@12345",
            "job_name": config.job_name if config else "GenAI_Phase1_Demo_Script"
        }
        config_json = json.dumps(config_dict)
        
        test_execution_job_status[job_id]["progress"] = 50
        test_execution_job_status[job_id]["message"] = f"Triggering Jenkins job: {config_dict['job_name']}"
        
        # Run the script with config JSON as argument
        process = subprocess.Popen(
            [sys.executable, str(script_path), config_json],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            text=True,
            bufsize=1,
            cwd=str(script_path.parent)  # Run from the script's directory
        )
        
        test_execution_job_status[job_id]["progress"] = 70
        test_execution_job_status[job_id]["message"] = "Monitoring Jenkins job execution..."

        # Stream script output live and parse progress/status markers.
        stdout_lines = []
        while True:
            line = process.stdout.readline() if process.stdout else ''
            if line:
                clean_line = line.rstrip('\n')
                stdout_lines.append(clean_line)

                progress_match = re.match(r"^PROGRESS:(\d{1,3})$", clean_line.strip())
                status_match = re.match(r"^STATUS:(.+)$", clean_line.strip())
                if progress_match:
                    pct = max(0, min(100, int(progress_match.group(1))))
                    test_execution_job_status[job_id]["progress"] = pct
                elif status_match:
                    test_execution_job_status[job_id]["message"] = status_match.group(1).strip()

            if process.poll() is not None:
                if process.stdout:
                    remainder = process.stdout.read()
                    if remainder:
                        stdout_lines.extend(remainder.splitlines())
                break

        stderr = process.stderr.read() if process.stderr else ""
        stdout = "\n".join(stdout_lines)
        
        # Extract console output from stdout (between markers)
        console_output = ""
        if stdout:
            # Look for console output between markers
            start_marker = "=== JENKINS CONSOLE OUTPUT START ==="
            end_marker = "=== JENKINS CONSOLE OUTPUT END ==="
            
            start_idx = stdout.find(start_marker)
            end_idx = stdout.find(end_marker)
            
            if start_idx != -1 and end_idx != -1:
                # Extract console output between markers
                console_output = stdout[start_idx + len(start_marker):end_idx].strip()
            else:
                # If markers not found, use entire stdout as fallback
                console_output = stdout
        
        # Extract build result and build number from output
        build_result = None
        build_number = None
        if stdout:
            for line in stdout.split('\n'):
                if "Job completed with result:" in line:
                    build_result = line.split("Job completed with result:")[-1].strip()
                elif "Job started with build number:" in line:
                    build_number = line.split("Job started with build number:")[-1].strip()
                elif "Build number:" in line:
                    build_number = line.split("Build number:")[-1].strip()
        
        # Set progress to 100% regardless of success/failure (execution completed)
        test_execution_job_status[job_id]["progress"] = 100
        test_execution_job_status[job_id]["build_result"] = build_result
        test_execution_job_status[job_id]["build_number"] = build_number
        test_execution_job_status[job_id]["output"] = console_output  # Only console output, no other messages
        
        # Check if execution was successful
        if process.returncode == 0:
            test_execution_job_status[job_id]["status"] = "completed"
            test_execution_job_status[job_id]["message"] = f"Test execution completed (Result: {build_result or 'SUCCESS'})"
        else:
            # Execution failed but completed - still show 100% progress
            error_message = stderr if stderr else "Job execution failed"
            test_execution_job_status[job_id]["status"] = "failed"
            test_execution_job_status[job_id]["error"] = error_message
            test_execution_job_status[job_id]["message"] = f"Test execution completed (Result: {build_result or 'FAILED'})"
        
    except FileNotFoundError as e:
        test_execution_job_status[job_id]["status"] = "failed"
        test_execution_job_status[job_id]["error"] = f"Test execution script not found: {str(e)}"
        test_execution_job_status[job_id]["message"] = f"Test execution script not found: {str(e)}"
    except Exception as e:
        test_execution_job_status[job_id]["status"] = "failed"
        test_execution_job_status[job_id]["error"] = str(e)
        test_execution_job_status[job_id]["message"] = f"Test execution failed: {str(e)}"
        test_execution_job_status[job_id]["progress"] = 0

@router.post("/api/test-execution/execute")
async def execute_test_scripts(request: TestExecutionRequest, background_tasks: BackgroundTasks):
    """Execute test scripts via Jenkins."""
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Use default configuration if no custom config provided
        if request.custom_config:
            config = request.custom_config
        else:
            # Default configuration
            config = TestExecutionConfig(
                jenkins_server_url="http://10.138.77.71:8080/",
                jenkins_username="chandu",
                jenkins_password="tcs@12345",
                job_name="GenAI_Phase1_Demo_Script"
            )
        
        # Start background test execution task
        background_tasks.add_task(execute_test_execution_process, job_id, config)
        
        return TestExecutionResponse(
            success=True,
            job_id=job_id,
            message="Test execution started successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting test execution: {str(e)}")

@router.get("/api/test-execution/status/{job_id}")
async def get_test_execution_status(job_id: str):
    """Get test execution status."""
    if job_id not in test_execution_job_status:
        raise HTTPException(status_code=404, detail="Test execution job not found")
    
    return test_execution_job_status[job_id]

@router.get("/api/test-execution/configs")
async def get_test_execution_configs():
    """Get available test execution configurations."""
    configs = {
        "default": {
            "name": "Default Configuration",
            "jenkins_server_url": "http://10.138.77.71:8080/",
            "jenkins_username": "chandu",
            "job_name": "GenAI_Phase1_Demo_Script",
            "description": "Execute tests using default Jenkins server and job"
        }
    }
    
    return {
        "success": True,
        "configs": configs,
        "message": "Test execution configurations retrieved successfully"
    }



@router.get("/api/dataset/extract-folder-path")
async def get_extract_folder_path():
    """Get the path to the extract folder where dataset files are stored."""
    try:
        extract_path = Path("resources/extract").absolute()
        
        return {
            "success": True,
            "extract_path": str(extract_path),
            "message": f"Extract folder path: {extract_path}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get extract folder path: {str(e)}")

@router.post("/api/dataset/open-folder")
async def open_folder_in_explorer(request: OpenFolderRequest):
    """Open a folder in Windows Explorer."""
    try:
        import subprocess
        import platform
        
        folder_path = request.folder_path
        
        # Ensure the folder path exists
        folder_path_obj = Path(folder_path)
        if not folder_path_obj.exists():
            return {
                "success": False,
                "message": f"Folder does not exist: {folder_path}"
            }
        
        # Open folder based on operating system
        system = platform.system().lower()
        
        if system == "windows":
            # Use Windows Explorer
            subprocess.run(["explorer", str(folder_path_obj)], check=True)
        elif system == "darwin":  # macOS
            # Use Finder
            subprocess.run(["open", str(folder_path_obj)], check=True)
        elif system == "linux":
            # Use file manager (try common ones)
            file_managers = ["xdg-open", "nautilus", "dolphin", "thunar"]
            for fm in file_managers:
                try:
                    subprocess.run([fm, str(folder_path_obj)], check=True)
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            else:
                raise Exception("No suitable file manager found")
        else:
            raise Exception(f"Unsupported operating system: {system}")
        
        return {
            "success": True,
            "message": f"Opened folder: {folder_path}"
        }
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to open folder: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error opening folder: {str(e)}")

@router.delete("/api/deployment/config-files/{file_id}")
async def delete_deployment_config_file(file_id: str):
    """Delete a deployment configuration file."""
    try:
        config_dir = Path("resources/deployment_configs")
        file_path = config_dir / file_id
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Configuration file not found")
        
        file_path.unlink()
        
        return {
            "success": True,
            "message": "Configuration file deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete config file: {str(e)}")


# Bug Discovery / RCA Analysis Endpoints

class RCARequest(BaseModel):
    """Request model for RCA analysis"""
    log_file_name: str
    analysis_type: str = "error"  # error, function, impact, kt, ai - default to error

@router.post("/api/rca/upload-logs")
async def upload_rca_logs(files: List[UploadFile] = File(...)):
    """Upload log files for RCA analysis"""
    try:
        # Create upload directory
        upload_dir = BACKEND_DIR / "resources" / "rca_logs"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Create metadata file to track original names
        metadata_file = upload_dir / "file_metadata.json"
        
        # Load existing metadata
        file_metadata = {}
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                file_metadata = json.load(f)
        
        uploaded_files = []
        
        for file in files:
            # Save file with original name to preserve it
            file_id = str(uuid.uuid4())
            # Use original filename with UUID prefix to avoid conflicts
            safe_filename = f"{file_id}_{file.filename}"
            file_path = upload_dir / safe_filename
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Store metadata mapping
            file_metadata[file.filename] = {
                "file_id": file_id,
                "saved_name": safe_filename,
                "file_path": str(file_path),
                "upload_date": datetime.now().isoformat()
            }
            
            uploaded_files.append({
                "file_id": file_id,
                "original_name": file.filename,
                "saved_name": safe_filename,
                "file_path": str(file_path),
                "size": file_path.stat().st_size
            })
        
        # Save metadata
        with open(metadata_file, 'w') as f:
            json.dump(file_metadata, f, indent=2)
        
        return {
            "success": True,
            "files": uploaded_files,
            "message": f"Successfully uploaded {len(uploaded_files)} log file(s)"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload log files: {str(e)}")

@router.post("/api/rca/analyze")
async def start_rca_analysis(background_tasks: BackgroundTasks, request: RCARequest):
    """Start RCA analysis on uploaded log file"""
    try:
        import subprocess
        
        # Find the log file using metadata
        upload_dir = BACKEND_DIR / "resources" / "rca_logs"
        metadata_file = upload_dir / "file_metadata.json"
        
        if not metadata_file.exists():
            raise HTTPException(status_code=404, detail="No log files have been uploaded yet")
        
        # Load metadata
        with open(metadata_file, 'r') as f:
            file_metadata = json.load(f)
        
        # Find file by original name
        if request.log_file_name not in file_metadata:
            print(f"🔍 Looking for: {request.log_file_name}")
            print(f"🔍 Available files: {list(file_metadata.keys())}")
            raise HTTPException(status_code=404, detail=f"Log file not found: {request.log_file_name}")
        
        file_info = file_metadata[request.log_file_name]
        log_file_path = Path(file_info["file_path"])
        
        if not log_file_path.exists():
            raise HTTPException(status_code=404, detail=f"Log file path does not exist: {log_file_path}")
        
        # Path to RCA code
        rca_dir = BACKEND_DIR / "app" / "services" / "RCA-Code-Updated" / "RCA-Code-Updated"
        
        print(f"🔍 RCA Directory: {rca_dir}")
        print(f"🔍 RCA Directory exists: {rca_dir.exists()}")
        print(f"🔍 Log file path: {log_file_path}")
        print(f"🔍 Log file exists: {log_file_path.exists()}")
        
        if not rca_dir.exists():
            raise HTTPException(status_code=500, detail=f"RCA code directory not found: {rca_dir}")
        
        # Output file - save next to the log file with .rca.json extension
        # This makes it easier to find and read
        output_file = log_file_path.parent / f"{log_file_path.name}.rca.json"
        
        print(f"📁 Output file will be saved as: {output_file}")
        
        # Use the system Python (same as the backend)
        python_exe = sys.executable
        print(f"✓ Using system Python: {python_exe}")
        
        # Build command - use wrapper script to ensure imports work
        wrapper_script = rca_dir / "run_rca_wrapper.py"
        wrapper_exists = wrapper_script.exists()
        print(f"🔍 Checking wrapper script: {wrapper_script}")
        print(f"🔍 Wrapper exists: {wrapper_exists}")
        
        if not wrapper_exists:
            # Fallback to direct script if wrapper doesn't exist
            script_to_run = "advanced_rca.py"
            print(f"⚠️ Wrapper not found, using advanced_rca.py directly")
        else:
            script_to_run = "run_rca_wrapper.py"
            print(f"✅ Using wrapper script for proper imports")
        
        cmd = [
            python_exe,
            "-u",  # Unbuffered output
            script_to_run,
            "--log-file", str(log_file_path.absolute()),
            "--output", str(output_file.absolute()),
            "--offline"  # Run in offline mode (no OpenAI API calls)
        ]
        
        # Add function map if exists (use relative path since we're in RCA dir)
        function_map_file = "function_calls.json"
        if (rca_dir / function_map_file).exists():
            cmd.extend(["--function-map", function_map_file])
            print(f"✓ Using function map: {function_map_file}")
        
        # Add error patterns if exists (use relative path since we're in RCA dir)
        error_patterns_file = "error_patterns_enhanced.json"
        if (rca_dir / error_patterns_file).exists():
            cmd.extend(["--error-patterns", error_patterns_file])
            print(f"✓ Using error patterns: {error_patterns_file}")
        
        # Add OAI repo if exists (use relative path from RCA directory)
        oai_repo_name = "openairinterface5g"
        if (rca_dir / oai_repo_name).exists():
            cmd.extend(["--oai-repo", oai_repo_name])
            print(f"✓ Using OAI repo: {oai_repo_name}")
        
        # Run RCA analysis
        rca_dir_abs = str(rca_dir.absolute())
        print(f"🚀 Running RCA analysis...")
        print(f"   Command: {' '.join(cmd)}")
        print(f"   Working directory: {rca_dir_abs}")
        print(f"   Python interpreter: {python_exe}")
        
        # Run with default environment (wrapper handles sys.path)
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=rca_dir_abs)
        
        print(f"📊 RCA Return code: {result.returncode}")
        if result.stdout:
            print(f"📊 RCA Stdout:")
            print(result.stdout)
        else:
            print(f"📊 RCA Stdout: None")
        
        if result.stderr:
            print(f"📊 RCA Stderr:")
            print(result.stderr)
        else:
            print(f"📊 RCA Stderr: None")
        
        if result.returncode != 0:
            print(f"❌ RCA analysis failed with return code: {result.returncode}")
            print(f"❌ RCA stderr: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"RCA analysis failed: {result.stderr}")
        
        # Wait a moment for file to be written
        import time
        time.sleep(0.5)
        
        # Check if output file was created (should be next to the log file)
        print(f"🔍 Checking for output file: {output_file}")
        print(f"🔍 Output file exists: {output_file.exists()}")
        
        if not output_file.exists():
            print(f"❌ RCA output file not found at expected location: {output_file}")
            print(f"🔍 Listing files in log directory:")
            for f in log_file_path.parent.iterdir():
                print(f"   - {f.name}")
            raise HTTPException(status_code=500, detail=f"RCA output file not generated at: {output_file}")
        
        print(f"✅ Found RCA output file: {output_file}")
        print(f"📊 File size: {output_file.stat().st_size} bytes")
        
        # Read the output file
        try:
            with open(output_file, 'r') as f:
                rca_results = json.load(f)
            
            print(f"📊 RCA results loaded successfully from: {output_file}")
            print(f"📊 Available analysis sections: {list(rca_results.keys())}")
            
            # Log what data is available for each section
            for section in ['error_analysis', 'function_analysis', 'impact_analysis', 'kb_analysis', 'ai_analysis']:
                section_data = rca_results.get(section)
                if section_data:
                    print(f"   ✓ {section}: {len(str(section_data))} chars")
                else:
                    print(f"   ✗ {section}: Not present or empty")
            
            # Extract the specific analysis type results
            analysis_data = {}
            if request.analysis_type == "error":
                analysis_data = rca_results.get("error_analysis", {})
            elif request.analysis_type == "function":
                analysis_data = rca_results.get("function_analysis", {})
            elif request.analysis_type == "impact":
                analysis_data = rca_results.get("impact_analysis", {})
            elif request.analysis_type == "kt":
                analysis_data = rca_results.get("kb_analysis", {})
            elif request.analysis_type == "ai":
                analysis_data = rca_results.get("ai_analysis", {})
            
            print(f"📊 Extracted {request.analysis_type} analysis data: {len(str(analysis_data))} chars")
            
            return {
                "success": True,
                "log_file": request.log_file_name,
                "analysis_type": request.analysis_type,
                "results": analysis_data,
                "full_results": rca_results,
                "output_file": str(output_file)
            }
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse RCA output file: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to parse RCA output: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"RCA Analysis Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"RCA analysis failed: {str(e)}")

class SaveAnalysisRequest(BaseModel):
    """Request model for saving analysis"""
    error_message: str
    log_file: str
    log_path: Optional[str] = ""
    code_dir: Optional[str] = ""
    results: Optional[Dict[str, Any]] = {}
    fix_suggestions: Optional[Dict[str, Any]] = {}

def _extract_code_from_git_diff(git_diff_data: str, file_path: str, function_name: str = None):
    """Extract original_code, patched_code, and full file path from git diff output (matching PyQt)."""
    import re
    
    if not git_diff_data:
        return "", "", None
    
    try:
        # Normalize the file path for matching
        file_basename = os.path.basename(file_path)
        
        # Find the diff section for this file
        file_pattern = rf'diff --git a/[^\s]+ b/([^\s]+)'
        diff_sections = re.split(file_pattern, git_diff_data)
        
        target_diff = None
        full_file_path = None
        for i in range(1, len(diff_sections), 2):
            if i + 1 < len(diff_sections):
                current_file = diff_sections[i]
                if file_basename in current_file:
                    target_diff = diff_sections[i + 1]
                    full_file_path = current_file
                    break
        
        if not target_diff:
            return "", "", None
        
        # Extract code with context
        original_code, patched_code = _extract_code_with_more_context(target_diff)
        return original_code, patched_code, full_file_path
        
    except Exception as e:
        print(f"Error extracting code from git diff: {e}")
        return "", "", None

def _extract_code_with_more_context(diff_section: str):
    """Extract code changes with more surrounding context (matching PyQt)."""
    lines = diff_section.split('\n')
    
    original_lines = []
    patched_lines = []
    
    for line in lines:
        if line.startswith('@@') or line.startswith('---') or line.startswith('+++'):
            continue
        elif line.startswith('-') and not line.startswith('---'):
            original_lines.append(line[1:])
        elif line.startswith('+') and not line.startswith('+++'):
            patched_lines.append(line[1:])
        elif line.startswith(' '):
            context_line = line[1:]
            original_lines.append(context_line)
            patched_lines.append(context_line)
    
    original_code = '\n'.join(original_lines)
    patched_code = '\n'.join(patched_lines)
    return original_code, patched_code

def _extract_config_from_git_diff(git_diff_data: str, param_name: str):
    """Extract old and new config values from git diff output (matching PyQt)."""
    import re
    
    if not git_diff_data:
        return "N/A", "N/A"
    
    try:
        lines = git_diff_data.split('\n')
        old_value = None
        new_value = None
        
        i = 0
        while i < len(lines):
            line = lines[i]
            if param_name in line:
                if line.startswith('-') and not line.startswith('---'):
                    old_line = line[1:].strip()
                    old_value = _extract_value_from_config_line(old_line)
                    
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j]
                        if next_line.strip() == '':
                            j += 1
                            continue
                        if param_name in next_line and next_line.startswith('+') and not next_line.startswith('+++'):
                            new_line = next_line[1:].strip()
                            new_value = _extract_value_from_config_line(new_line)
                            i = j
                            break
                        else:
                            break
                        j += 1
                elif line.startswith('+') and not line.startswith('+++'):
                    if new_value is None:
                        new_line = line[1:].strip()
                        new_value = _extract_value_from_config_line(new_line)
            i += 1
        
        return old_value or "N/A", new_value or "N/A"
        
    except Exception as e:
        print(f"Error extracting config from git diff: {e}")
        return "N/A", "N/A"

def _extract_value_from_config_line(line: str):
    """Extract the value from a configuration line (matching PyQt)."""
    import re
    
    # Format 1: param = "value";
    match = re.search(r'=\s*"([^"]+)"', line)
    if match:
        return match.group(1)
    
    # Format 2: param = value;
    match = re.search(r'=\s*([^;]+);', line)
    if match:
        return match.group(1).strip()
    
    # Format 3: ipv4 = "value"
    match = re.search(r'ipv4\s*=\s*"([^"]+)"', line)
    if match:
        return match.group(1)
    
    return line.strip()

@router.post("/api/rca/save-analysis")
async def save_rca_analysis(request: SaveAnalysisRequest):
    """Save RCA analysis results to bug history (matching PyQt save_bug_analysis_to_history)"""
    try:
        # Use the same path resolution as Code Assistant
        history_dir = Path("resources/bug_history")
        if not history_dir.exists():
            project_root_dir = Path(__file__).parent.parent.parent
            alt_history_dir = project_root_dir / "backend" / "resources" / "bug_history"
            if alt_history_dir.exists():
                history_dir = alt_history_dir
            else:
                history_dir.mkdir(parents=True, exist_ok=True)
        
        # Create unique filename with timestamp (matching PyQt)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_file = history_dir / f"bug_analysis_{timestamp}.json"
        
        # CRITICAL: If this is a Git fix, check for existing RCA analysis with the same log_file
        # Match by log_file (not code_dir) - code_dir can change but log_file is the base identifier
        existing_rca_results = {}
        if request.fix_suggestions and request.fix_suggestions.get('from_git_history', False):
            try:
                # Find all JSON files in history directory
                json_files = list(history_dir.glob("bug_analysis_*.json"))
                
                # Load and check each file for matching log_file
                matching_analyses = []
                for json_file in json_files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            existing_data = json.load(f)
                            
                            # Match by log_file (case-insensitive)
                            existing_log_file = existing_data.get('log_file', '')
                            if existing_log_file.lower() == request.log_file.lower():
                                # Only consider RCA analyses (not other git fixes)
                                # Check if it's NOT from git history
                                is_git_fix = existing_data.get('from_git_history', False) or existing_data.get('source') == 'existing_fix'
                                if not is_git_fix:
                                    # This is an RCA analysis - store it
                                    file_timestamp = existing_data.get('timestamp', '')
                                    matching_analyses.append({
                                        'file': json_file,
                                        'timestamp': file_timestamp,
                                        'data': existing_data
                                    })
                    except (json.JSONDecodeError, KeyError, Exception) as e:
                        # Skip corrupted or invalid files
                        continue
                
                # Sort by timestamp (most recent first) and get the latest RCA analysis
                if matching_analyses:
                    matching_analyses.sort(key=lambda x: x['timestamp'], reverse=True)
                    latest_rca = matching_analyses[0]['data']
                    existing_rca_results = latest_rca.get('results', {})
                    
                    print(f"✅ Found existing RCA analysis for log_file '{request.log_file}'")
                    print(f"   Source file: {matching_analyses[0]['file'].name}")
                    print(f"   Preserving: phase2_analysis={bool(existing_rca_results.get('phase2_analysis'))}, "
                          f"phase4_commands={bool(existing_rca_results.get('phase4_commands'))}, "
                          f"deployment_context={bool(existing_rca_results.get('deployment_context'))}, "
                          f"summary={bool(existing_rca_results.get('summary'))}")
            except Exception as e:
                print(f"⚠️ Error while searching for existing RCA analysis: {e}")
                import traceback
                traceback.print_exc()
        
        # Merge fix_suggestions into results structure (matching PyQt format)
        # Start with existing RCA results if found, otherwise use request results
        if existing_rca_results:
            # Deep copy existing RCA results to preserve all data
            import copy
            results = copy.deepcopy(existing_rca_results)
            print(f"✅ Starting with existing RCA results (preserving all phases)")
        else:
            results = request.results.copy() if request.results else {}
        
        # Check if this is from git history (existing fix) - need to extract values from git diff
        from_git_history = False
        git_metadata = {}
        git_diff = None
        
        if request.fix_suggestions:
            from_git_history = request.fix_suggestions.get('from_git_history', False)
            git_diff = request.fix_suggestions.get('git_diff')
            
            # CRITICAL: If this is a Git fix and we have a different code_dir, update deployment_context paths
            # This matches PyQt behavior - update paths to use the codebase from Git search (e.g., openairinterface5g-test)
            # while preserving all other RCA data
            if from_git_history and request.code_dir:
                # Get the codebase name from the Git search code_dir
                git_codebase_name = os.path.basename(request.code_dir.rstrip(os.sep)) if request.code_dir else "openairinterface5g-develop"
                
                # Helper function to update deployment_context paths recursively
                def update_deployment_context_paths(deployment_context_dict):
                    """Recursively update paths in deployment_context.active_configs"""
                    if not isinstance(deployment_context_dict, dict):
                        return
                    
                    if 'active_configs' in deployment_context_dict and isinstance(deployment_context_dict['active_configs'], list):
                        for config_entry in deployment_context_dict['active_configs']:
                            if isinstance(config_entry, dict) and 'used' in config_entry:
                                # Update path from openairinterface5g-develop to git codebase (e.g., openairinterface5g-test)
                                old_path = config_entry.get('used', '')
                                if 'openairinterface5g-develop' in old_path:
                                    new_path = old_path.replace('openairinterface5g-develop', git_codebase_name)
                                    config_entry['used'] = new_path
                                    print(f"   Updated deployment_context path: {old_path} -> {new_path}")
                
                # Update top-level deployment_context
                if 'deployment_context' in results and isinstance(results.get('deployment_context'), dict):
                    update_deployment_context_paths(results['deployment_context'])
                    print(f"✅ Updated top-level deployment_context.active_configs to use codebase: {git_codebase_name}")
                
                # Update deployment_context in phase2_analysis (nested)
                if 'phase2_analysis' in results and isinstance(results.get('phase2_analysis'), dict):
                    phase2_analysis = results['phase2_analysis']
                    if 'deployment_context' in phase2_analysis and isinstance(phase2_analysis.get('deployment_context'), dict):
                        update_deployment_context_paths(phase2_analysis['deployment_context'])
                        print(f"✅ Updated phase2_analysis.deployment_context.active_configs to use codebase: {git_codebase_name}")
            
            # Extract all git-related metadata from fix_suggestions
            if from_git_history:
                git_metadata = {
                    'git_diff': git_diff,
                    'current_branch': request.fix_suggestions.get('current_branch'),
                    'files_changed_summary': request.fix_suggestions.get('files_changed_summary'),
                    'selection_result': request.fix_suggestions.get('selection_result'),
                    'confidence': request.fix_suggestions.get('confidence'),
                    'score': request.fix_suggestions.get('score'),
                    'reasoning': request.fix_suggestions.get('reasoning'),
                    'full_commit': request.fix_suggestions.get('full_commit')
                }
                # Remove None values to keep JSON clean
                git_metadata = {k: v for k, v in git_metadata.items() if v is not None}
        
        # If fix_suggestions are provided, merge them into results.phase3_fixes
        if request.fix_suggestions:
            # Ensure phase3_fixes exists
            if 'phase3_fixes' not in results:
                results['phase3_fixes'] = {}
            
            # Get fix_suggestion from fix_suggestions (it's directly at the root level)
            fix_suggestion = request.fix_suggestions.get('fix_suggestion', {})
            if fix_suggestion:
                # CRITICAL: If this is from git history and we have git_diff, extract actual values
                # This matches PyQt behavior - enrich patches with actual code/config from git diff
                if from_git_history and git_diff:
                    # Extract code patches with actual code from git diff
                    code_patches = fix_suggestion.get('code_patches', [])
                    if code_patches:
                        for patch in code_patches:
                            file_path_from_patch = patch.get('file_path', '')
                            function_name = patch.get('function_name', '')
                            
                            # Extract actual code from git diff (matching PyQt)
                            original_code, patched_code, full_file_path = _extract_code_from_git_diff(
                                git_diff, file_path_from_patch, function_name
                            )
                            
                            # Update patch with extracted values
                            if original_code:
                                patch['original_code'] = original_code
                            if patched_code:
                                patch['patched_code'] = patched_code
                                patch['suggested_code'] = patched_code  # Alias for compatibility
                            
                            # Update file path with full path from git diff if available
                            if full_file_path and request.code_dir:
                                openair_codebase_file_name = os.path.basename(request.code_dir.rstrip(os.sep)) if request.code_dir else "openairinterface5g-develop"
                                patch['file_path'] = f"Error_fixing_pipelin/{openair_codebase_file_name}/{full_file_path}"
                    
                    # Extract config patches with actual values from git diff (matching PyQt)
                    config_patches = fix_suggestion.get('config_patches', [])
                    if config_patches:
                        for patch in config_patches:
                            param_name = patch.get('parameter_name') or patch.get('config_name', '')
                            
                            # Extract actual config values from git diff (matching PyQt)
                            current_value, new_value = _extract_config_from_git_diff(git_diff, param_name)
                            
                            # Update patch with extracted values
                            if current_value != "N/A":
                                patch['current_value'] = current_value
                            if new_value != "N/A":
                                patch['new_value'] = new_value
                                patch['suggested_value'] = new_value  # Alias for compatibility
                            
                            # Construct proper file path (matching PyQt)
                            file_path_from_patch = patch.get('file_path', '')
                            if file_path_from_patch and request.code_dir:
                                openair_codebase_file_name = os.path.basename(request.code_dir.rstrip(os.sep)) if request.code_dir else "openairinterface5g-develop"
                                file_basename = os.path.basename(file_path_from_patch)
                                
                                if file_basename.endswith('.conf') or file_basename.endswith('.cfg'):
                                    if 'gnb' in file_basename.lower():
                                        patch['file_path'] = f"Error_fixing_pipelin/{openair_codebase_file_name}/targets/PROJECTS/GENERIC-NR-5GC/CONF/{file_basename}"
                                    elif 'ue' in file_basename.lower():
                                        patch['file_path'] = f"Error_fixing_pipelin/{openair_codebase_file_name}/openair3/NAS/TOOLS/{file_basename}"
                                    else:
                                        patch['file_path'] = f"Error_fixing_pipelin/{openair_codebase_file_name}/{file_path_from_patch}"
                                else:
                                    patch['file_path'] = f"Error_fixing_pipelin/{openair_codebase_file_name}/{file_path_from_patch}"
                
                # Merge fix_suggestion into results.phase3_fixes
                # Preserve existing fix_suggestion fields (root_cause_analysis, investigation_steps, specification_context, etc.)
                # and only update/add git fix specific fields
                existing_fix_suggestion = results['phase3_fixes'].get('fix_suggestion', {})
                
                # Merge: Keep existing fields, update with git fix data
                merged_fix_suggestion = {
                    **existing_fix_suggestion,  # Preserve existing RCA fix data
                    **fix_suggestion  # Override with git fix data (code_patches, config_patches, commit_info, etc.)
                }
                
                # Preserve important RCA fields that shouldn't be overwritten by git fix
                if 'root_cause_analysis' in existing_fix_suggestion and 'root_cause_analysis' not in fix_suggestion:
                    merged_fix_suggestion['root_cause_analysis'] = existing_fix_suggestion['root_cause_analysis']
                if 'investigation_steps' in existing_fix_suggestion and 'investigation_steps' not in fix_suggestion:
                    merged_fix_suggestion['investigation_steps'] = existing_fix_suggestion['investigation_steps']
                if 'specification_context' in existing_fix_suggestion and 'specification_context' not in fix_suggestion:
                    merged_fix_suggestion['specification_context'] = existing_fix_suggestion['specification_context']
                
                results['phase3_fixes']['fix_suggestion'] = merged_fix_suggestion
            
            # Also merge phase4_commands (terminal commands) if available
            # Check both root level and in a phase4_commands object
            terminal_commands = request.fix_suggestions.get('terminal_commands', [])
            if not terminal_commands and 'phase4_commands' in request.fix_suggestions:
                terminal_commands = request.fix_suggestions['phase4_commands'].get('terminal_commands', [])
            
            if terminal_commands:
                if 'phase4_commands' not in results:
                    results['phase4_commands'] = {}
                results['phase4_commands']['terminal_commands'] = terminal_commands
        
        # Prepare data to save (matching PyQt format)
        history_data = {
            'error_message': request.error_message,
            'log_file': request.log_file,
            'log_path': request.log_path,
            'code_dir': request.code_dir,
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'history_file': str(history_file),
            'source': 'existing_fix' if from_git_history else 'rca_analysis',  # Mark source
            'from_git_history': from_git_history,  # Also store flag for easy checking
            'git_metadata': git_metadata if git_metadata else None  # Store all git-related data
        }
        
        # Save to file
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2)
        
        try:
            bug_history_record = {
                "log_file": request.log_file,
                "output": request.fix_suggestions or results,
                "metadata": {
                    "history_file": str(history_file),
                    "log_path": request.log_path,
                    "code_dir": request.code_dir,
                },
            }
            append_history_record("bug_discovery_history.json", bug_history_record)
        except Exception as log_error:
            print(f"⚠️ Failed to append bug discovery history record: {log_error}")
        
        print(f"✅ Saved bug analysis to history: {history_file}")
        print(f"   Error message: {request.error_message[:100]}...")
        print(f"   Log file: {request.log_file}")
        print(f"   Code dir: {request.code_dir}")
        
        # Debug: Show patch counts
        phase3_fixes = results.get('phase3_fixes', {})
        fix_suggestion = phase3_fixes.get('fix_suggestion', {})
        code_count = len(fix_suggestion.get('code_patches', []))
        config_count = len(fix_suggestion.get('config_patches', []))
        print(f"   Code patches: {code_count}, Config patches: {config_count}")
        
        return {
            "success": True,
            "message": "Analysis saved to history",
            "history_file": str(history_file),
            "filename": history_file.name
        }
        
    except Exception as e:
        print(f"Error saving bug analysis: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save bug analysis: {str(e)}")


# Error Fixing Pipeline Endpoints

class ErrorAnalysisRequest(BaseModel):
    error_message: Optional[str] = None
    log_file_path: Optional[str] = None
    openair_codebase_name: str = "openairinterface5g-develop"
    custom_deployment_context: Optional[Dict[str, Any]] = None
    crash_analysis: bool = False  # Flag for crash analysis mode

class EmbeddingUpdateRequest(BaseModel):
    commit_hash: str
    selected_code_patches: List[Dict[str, Any]]
    selected_config_patches: List[Dict[str, Any]]

@router.post("/api/error-fixing/analyze")
async def analyze_error(request: ErrorAnalysisRequest):
    """
    Analyze an error and provide fix suggestions using the complete error fixing pipeline
    
    Args:
        request: ErrorAnalysisRequest containing error message and optional log file path
        
    Returns:
        Complete analysis results including error analysis and fix suggestions
    """
    if not ERROR_FIXING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Error fixing pipeline not available")
    
    try:
        # Change to the error fixing pipeline directory for proper execution
        original_cwd = os.getcwd()
        # The pipeline directory is app/services/Error_fixing_pipelin (no nested subdirectory)
        pipeline_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "services", "Error_fixing_pipelin")
        pipeline_dir = os.path.abspath(pipeline_dir)  # Get absolute path
        
        # Verify the directory exists
        if not os.path.exists(pipeline_dir):
            raise HTTPException(
                status_code=500, 
                detail=f"Error fixing pipeline directory not found: {pipeline_dir}"
            )
        
        print(f"📁 Changing to pipeline directory: {pipeline_dir}")
        os.chdir(pipeline_dir)
        
        try:
            # Initialize the pipeline
            pipeline = CompleteErrorFixingPipeline(openair_codebase_file_name=request.openair_codebase_name)
            
            # Extract error message from log file if not provided (matching UI_v3.py)
            error_message = request.error_message
            log_file_path = request.log_file_path
            
            if not error_message and log_file_path:
                # Extract error message from log file (like UI_v3.py extract_error_from_log)
                try:
                    from app.services.Error_fixing_pipelin.parse_log_context import LogContextParser
                    log_parser = LogContextParser(openair_codebase_file_name=request.openair_codebase_name)
                    error_message = log_parser.extract_error_message(log_file_path)
                except Exception as e:
                    print(f"Could not extract error from log file, trying simple extraction: {e}")
                    # Fallback: simple error extraction
                    try:
                        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Look for common error patterns
                            error_keywords = ['error', 'ERROR', 'fail', 'FAIL', 'exception', 'EXCEPTION', 'fatal', 'FATAL']
                            lines = content.split('\n')
                            for line in lines:
                                if any(keyword in line for keyword in error_keywords):
                                    error_message = line.strip()
                                    if error_message:
                                        break
                    except Exception as e2:
                        print(f"Simple error extraction also failed: {e2}")
            
            # Convert log file path to relative path (matching UI_v3.py)
            relative_log_path = log_file_path
            if log_file_path and os.path.isabs(log_file_path):
                relative_log_path = os.path.relpath(log_file_path, pipeline_dir)
            
            # Check if crash analysis is enabled
            crash_analysis_enabled = request.crash_analysis
            
            if crash_analysis_enabled:
                # Use crash analysis flow for segmentation faults - Run complete flow (Phase 1, 2, 2.5, 3)
                print("🔬 Crash Analysis Mode Enabled")
                print("Running complete crash analysis pipeline...")
                print("Phase 1: Extracting error and backtrace from segmentation fault log...")
                
                # Run complete crash analysis (Phase 1, 2, 2.5, 3)
                result = pipeline.process_crash_analysis(relative_log_path, phase="full")
                
                # Extract error message for display
                error_message = result.get('error_message', 'Segmentation Fault Detected')
                
                print("\n✅ Crash Analysis Complete!")
                
                # Load crash-specific results if available
                crash_output_file = os.path.join(pipeline_dir, "output/crash_phase3_fixes.json")
                if os.path.exists(crash_output_file):
                    try:
                        with open(crash_output_file, 'r', encoding='utf-8') as f:
                            crash_detailed = json.load(f)
                            result['crash_detailed_fixes'] = crash_detailed
                    except Exception as e:
                        print(f"Could not load detailed crash fixes: {e}")
                
                # Format result to match regular analysis structure for UI compatibility
                if 'crash_detailed_fixes' in result:
                    crash_fixes = result['crash_detailed_fixes']
                    # Convert crash fixes to match regular fix_suggestion structure
                    result['phase3_fixes'] = {
                        'fix_suggestion': crash_fixes.get('fix_suggestion', {})
                    }
                    result['fix_suggestions'] = {
                        'fix_suggestion': crash_fixes.get('fix_suggestion', {}),
                        'error_text': error_message
                    }
                
                # Ensure crash_info, backtrace, and scenario_flow are included in result for crash analysis
                # (These are already in result from process_crash_analysis, but ensure they're at top level)
                if crash_analysis_enabled:
                    # crash_info is already in result from process_crash_analysis
                    # Ensure it's accessible for frontend
                    if 'crash_info' not in result:
                        result['crash_info'] = result.get('extraction_summary', {})
                    if 'backtrace' not in result and 'crash_info' in result:
                        result['backtrace'] = result['crash_info'].get('backtrace', [])
                    if 'scenario_flow' not in result and 'crash_info' in result:
                        result['scenario_flow'] = result['crash_info'].get('scenario_flow', [])
            else:
                # Process the error through the complete pipeline (same as PyQt)
                # Use custom deployment context if provided, otherwise use None (will use JSON defaults)
                custom_context = request.custom_deployment_context if request.custom_deployment_context and len(request.custom_deployment_context) > 0 else None
                if custom_context:
                    print(f"📝 Using custom deployment context with {len(custom_context)} values")
                    for key, value in custom_context.items():
                        print(f"   - {key}: {value}")
                else:
                    print("📝 Using default deployment context from JSON file")
                
                result = pipeline.process_error_with_context(error_message, relative_log_path, custom_deployment_context=custom_context)
            
            # Debug: Print the result structure to understand what data is available
            print(f"🔍 DEBUG: Pipeline result keys: {list(result.keys())}")
            if 'phase3_fixes' in result:
                print(f"🔍 DEBUG: Phase3 fixes keys: {list(result['phase3_fixes'].keys())}")
                if 'fix_suggestion' in result['phase3_fixes']:
                    fix_suggestion = result['phase3_fixes']['fix_suggestion']
                    print(f"🔍 DEBUG: Fix suggestion keys: {list(fix_suggestion.keys())}")
                    print(f"🔍 DEBUG: Suspected functions: {fix_suggestion.get('suspected_functions', [])}")
                    print(f"🔍 DEBUG: Suspected configs: {fix_suggestion.get('suspected_configs', [])}")
                    print(f"🔍 DEBUG: Code patches count: {len(fix_suggestion.get('code_patches', []))}")
                    print(f"🔍 DEBUG: Config patches count: {len(fix_suggestion.get('config_patches', []))}")
                    print(f"🔍 DEBUG: Investigation steps count: {len(fix_suggestion.get('investigation_steps', []))}")
            
            # Extract the results from the pipeline
            phase3_fixes = result.get('phase3_fixes', {})
            fix_suggestion = phase3_fixes.get('fix_suggestion', {})
            
            # Phase 4: Generate investigation commands (matching PyQt behavior)
            try:
                # Import the function using the same approach as the main pipeline
                from app.services.Error_fixing_pipelin.complete_error_fixing_pipeline import generate_terminal_commands
                from app.services.Error_fixing_pipelin.fix_suggestion_pipeline import FixSuggestionPipeline
                
                # Extract data for command generation
                phase3_fixes = result.get('phase3_fixes', {})
                fix_suggestion = phase3_fixes.get('fix_suggestion', {})
                investigation_steps = fix_suggestion.get('investigation_steps', [])
                deployment_context = result.get('deployment_context')
                
                # Get troubleshooting hints from error patterns (matching UI_v3.py logic)
                troubleshooting_hints = []
                try:
                    patterns_file = os.path.join(pipeline_dir, 'database', 'error_patterns_structured.json')
                    with open(patterns_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        patterns = data.get('patterns', {})
                        error_lower = error_message.lower()
                        
                        # Find matching pattern
                        pattern_found = False
                        for pattern_name, pattern_data in patterns.items():
                            keywords = pattern_data.get('keywords', [])
                            if any(keyword in error_lower for keyword in keywords):
                                suggested_fixes = pattern_data.get('suggested_fixes', [])
                                troubleshooting_hints.extend(suggested_fixes)
                                pattern_found = True
                                break
                        
                        # If no pattern matches, generate dynamic pattern (like UI_v3.py)
                        if not pattern_found:
                            print(f"🔄 No pattern found for Phase 4, generating dynamic pattern for: {error_message}")
                            fix_pipeline = FixSuggestionPipeline(openair_codebase_file_name=request.openair_codebase_name)
                            dynamic_pattern = fix_pipeline._generate_dynamic_error_pattern(error_message)
                            fix_pipeline._add_pattern_to_json(error_message, dynamic_pattern)
                            
                            # Use the generated pattern
                            suggested_fixes = dynamic_pattern.get('suggested_fixes', [])
                            troubleshooting_hints.extend(suggested_fixes)
                            
                except Exception as e:
                    print(f"Could not load troubleshooting hints: {e}")
                    # Fallback to default hints (matching UI_v3.py)
                    troubleshooting_hints = [
                        "Validate network configuration and parameters in config files",
                        "Check network reachability between endpoints",
                        "Verify protocol-specific configuration settings",
                        "Review error logs for additional context"
                    ]
                
                # Generate terminal commands using the pipeline function
                terminal_commands = generate_terminal_commands(
                    error_message=error_message,
                    investigation_steps=investigation_steps,
                    deployment_context=deployment_context,
                    troubleshooting_hints=troubleshooting_hints,
                    openair_codebase_file_name=request.openair_codebase_name
                )
                
                # Add commands to results
                result['phase4_commands'] = {
                    "terminal_commands": terminal_commands,
                    "command_count": len(terminal_commands)
                }
                
                # Save fix suggestions separately (including terminal commands) - matching UI_v3.py
                fix_suggestions_file = os.path.join(pipeline_dir, "output", "fix_suggestions.json")
                fix_suggestions_data = result.get('phase3_fixes', {}).copy()
                fix_suggestions_data['terminal_commands'] = result.get('phase4_commands', {})
                
                os.makedirs(os.path.dirname(fix_suggestions_file), exist_ok=True)
                with open(fix_suggestions_file, 'w', encoding='utf-8') as f:
                    json.dump(fix_suggestions_data, f, indent=2, ensure_ascii=False)
                
                print(f"🔧 Fix suggestions saved to: {fix_suggestions_file}")
                
                # Save complete results to output directory (matching UI_v3.py)
                output_file = os.path.join(pipeline_dir, "output", "complete_error_analysis.json")
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                print(f"💾 Complete results saved to: {output_file}")
                
                # Save deployment context if available (matching UI_v3.py)
                if result.get('deployment_context'):
                    context_file = os.path.join(pipeline_dir, "output", "deployment_context.json")
                    os.makedirs(os.path.dirname(context_file), exist_ok=True)
                    with open(context_file, 'w', encoding='utf-8') as f:
                        json.dump(result['deployment_context'], f, indent=2, ensure_ascii=False)
                    print(f"🌐 Deployment context saved to: {context_file}")
                
                # Save summary report (matching UI_v3.py)
                summary_file = os.path.join(pipeline_dir, "output", "error_fix_summary.txt")
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(f"Error Fix Summary Report\n")
                    f.write(f"=" * 60 + "\n\n")
                    f.write(f"Error: {error_message}\n")
                    f.write(f"Log File: {log_file_path or 'None'}\n")
                    f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    
                    # Deployment context
                    if result.get('deployment_context'):
                        ctx = result['deployment_context']
                        f.write(f"Deployment Context:\n")
                        f.write(f"- Role: {ctx.get('role', 'Unknown')}\n")
                        f.write(f"- Active Configs: {len(ctx.get('active_configs', []))}\n")
                        network_params = ctx.get('network_params', {})
                        f.write(f"- Network: gNB={network_params.get('gnb_ipv4', 'Unknown')}, AMF={network_params.get('amf_ipv4', 'Unknown')}\n\n")
                    
                    # Phase 2
                    phase2 = result.get('phase2_analysis', {})
                    f.write(f"Phase 2 Results:\n")
                    f.write(f"- Retrieval Method: {phase2.get('retrieval_method', 'standard')}\n")
                    f.write(f"- Functions: {len(phase2.get('suspected_functions', []))}\n")
                    f.write(f"- Configs: {len(phase2.get('suspected_configs', []))}\n\n")
                    
                    # Phase 3
                    phase3 = result.get('phase3_fixes', {})
                    fix_suggestion = phase3.get('fix_suggestion', {})
                    f.write(f"Phase 3 Results:\n")
                    f.write(f"- Root Cause: {fix_suggestion.get('reason', 'Not provided')[:200]}...\n")
                    f.write(f"- Fix Available: {'Yes' if fix_suggestion.get('config_fix') or fix_suggestion.get('code_patch') else 'No'}\n")
                
                print(f"📄 Summary report saved to: {summary_file}")
                
                # Add investigation commands to fix_suggestion for frontend
                if 'fix_suggestion' not in phase3_fixes:
                    phase3_fixes['fix_suggestion'] = {}
                
                phase3_fixes['fix_suggestion']['investigation_commands'] = [
                    {
                        "command": cmd.get('command', ''),
                        "hint": cmd.get('explanation', '')
                    }
                    for cmd in terminal_commands
                ]
                
                # Add analysis summary data
                result['summary'] = {
                    "total_functions_analyzed": len(phase3_fixes.get('fix_suggestion', {}).get('suspected_functions', [])),
                    "total_configs_analyzed": len(phase3_fixes.get('fix_suggestion', {}).get('suspected_configs', [])),
                    "call_graph_entries": len(result.get('call_graph_context', [])),
                    "pattern_matched": True,
                    "analysis_completed": True
                }
                
                # datetime is already imported at module level
                result['timestamp'] = datetime.now().isoformat()
                result['log_file'] = request.log_file_path
                
            except Exception as e:
                print(f"Could not generate investigation commands: {e}")
                import traceback
                traceback.print_exc()
                # Continue without investigation commands
            
            # Try to read the formatted output from the latest LLM prompts file
            formatted_output = ""
            try:
                # Look for the most recent LLM prompts file
                output_dir = os.path.join(pipeline_dir, "output")
                llm_files = [f for f in os.listdir(output_dir) if f.startswith("llm_prompts_") and f.endswith(".txt")]
                if llm_files:
                    latest_file = max(llm_files, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
                    with open(os.path.join(output_dir, latest_file), 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Extract the formatted output section
                        if "RCA ANALYSIS RESULTS" in content:
                            start_idx = content.find("RCA ANALYSIS RESULTS")
                            formatted_output = content[start_idx:]
                        elif "SUSPECTED FUNCTIONS" in content:
                            start_idx = content.find("SUSPECTED FUNCTIONS")
                            formatted_output = content[start_idx:]
            except Exception as e:
                print(f"Could not read formatted output: {e}")
                formatted_output = ""
            
        finally:
            # Always restore the original working directory
            os.chdir(original_cwd)
        
        # Read fix_suggestions.json file to include in response
        fix_suggestions_data = None
        try:
            fix_suggestions_file = os.path.join(pipeline_dir, "output", "fix_suggestions.json")
            if os.path.exists(fix_suggestions_file):
                with open(fix_suggestions_file, 'r', encoding='utf-8') as f:
                    fix_suggestions_data = json.load(f)
        except Exception as e:
            print(f"Could not read fix_suggestions.json: {e}")
        
        # Load deployment context (network parameters and deployment commands) from error_patterns_structured.json
        # This matches what PyQt UI does - loading from database/error_patterns_structured.json
        deployment_context_extended = {}
        try:
            patterns_file = os.path.join(pipeline_dir, 'database', 'error_patterns_structured.json')
            if os.path.exists(patterns_file):
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    patterns_data = json.load(f)
                    deployment_context_extended = patterns_data.get('deployment_context', {})
                    print(f"✅ Loaded deployment context from error_patterns_structured.json")
            else:
                print(f"⚠️ error_patterns_structured.json not found at: {patterns_file}")
        except Exception as e:
            print(f"⚠️ Could not load deployment context from error_patterns_structured.json: {e}")
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "formatted_output": formatted_output,
            "fix_suggestions": fix_suggestions_data,  # Include the JSON file content
            "deployment_context_extended": deployment_context_extended  # Include network params and deployment commands
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analysis failed: {str(e)}")

@router.post("/api/error-fixing/update-embeddings")
async def update_embeddings(request: EmbeddingUpdateRequest):
    """
    Update embeddings after applying patches
    
    Args:
        request: EmbeddingUpdateRequest containing commit hash and patch information
        
    Returns:
        Update results
    """
    if not ERROR_FIXING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Error fixing pipeline not available")
    
    try:
        # Update embeddings using the UI integration function
        success, message = update_embeddings_from_ui(
            commit_hash=request.commit_hash,
            selected_code_patches=request.selected_code_patches,
            selected_config_patches=request.selected_config_patches,
            openair_codebase_file_name=request.openair_codebase_name
        )
        
        return {
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding update failed: {str(e)}")

@router.get("/api/error-fixing/status")
async def get_error_fixing_status():
    """
    Get the current status of the error fixing pipeline
    
    Returns:
        Pipeline status information
    """
    return {
        "pipeline_available": ERROR_FIXING_AVAILABLE,
        "embedding_update_available": update_embeddings_from_ui is not None,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/api/error-fixing/log-files")
async def get_available_log_files(log_directory: Optional[str] = None):
    """
    Get list of available log files for error analysis
    
    Args:
        log_directory: Optional directory to search for log files
        
    Returns:
        List of available log files
    """
    try:
        if not log_directory:
            # Default to the log files directory in the error fixing pipeline
            log_directory = str(current_dir / "services" / "Error_fixing_pipelin" / "log_files")
        
        log_files = []
        log_path = Path(log_directory)
        
        if log_path.exists():
            for log_file in log_path.glob("*.log"):
                log_files.append({
                    "filename": log_file.name,
                    "path": str(log_file),
                    "size": log_file.stat().st_size,
                    "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                })
        
        return {
            "success": True,
            "log_files": log_files,
            "count": len(log_files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get log files: {str(e)}")

@router.post("/api/error-fixing/upload-log")
async def upload_log_file(file: UploadFile = File(...)):
    """
    Upload a log file for error analysis
    
    Args:
        file: Log file to upload
        
    Returns:
        Upload confirmation with file path
    """
    try:
        # Create the log files directory if it doesn't exist
        # Save to the pipeline's expected location: Error_fixing_pipelin/log_files/
        pipeline_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "services", "Error_fixing_pipelin")
        log_dir = Path(pipeline_dir) / "log_files"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a unique filename to avoid conflicts
        file_extension = Path(file.filename).suffix if file.filename else ".log"
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = log_dir / unique_filename
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Return path relative to pipeline directory
        relative_path = f"log_files/{unique_filename}"
        
        return {
            "success": True,
            "file_id": unique_filename,
            "filename": file.filename,
            "file_path": relative_path,
            "file_size": file_path.stat().st_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Log file upload failed: {str(e)}")

@router.get("/api/error-fixing/deployment-context-defaults")
async def get_deployment_context_defaults():
    """
    Get default deployment context values from error_patterns_structured.json
    
    Returns:
        Default deployment context values
    """
    try:
        # Get pipeline directory
        pipeline_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "services", "Error_fixing_pipelin")
        pipeline_dir = os.path.abspath(pipeline_dir)
        
        # Load deployment context from error_patterns_structured.json
        patterns_file = os.path.join(pipeline_dir, 'database', 'error_patterns_structured.json')
        if not os.path.exists(patterns_file):
            raise HTTPException(status_code=404, detail=f"Error patterns file not found: {patterns_file}")
        
        with open(patterns_file, 'r', encoding='utf-8') as f:
            patterns_data = json.load(f)
        
        deployment_context = patterns_data.get('deployment_context', {})
        
        return {
            "success": True,
            "deployment_context": deployment_context
        }
        
    except Exception as e:
        print(f"Error getting deployment context defaults: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get deployment context defaults: {str(e)}")

@router.post("/api/error-fixing/check-existing-fix")
async def check_existing_fix(
    log_file_path: str = Form(...), 
    openair_codebase_name: str = Form("openairinterface5g-develop"),
    source_code_directory: Optional[str] = Form(None)  # New parameter - user's selected source code directory
):
    """
    Check if an existing fix exists in Git commits for the given log file.
    
    Args:
        log_file_path: Path to the log file
        openair_codebase_name: Name of the OpenAirInterface codebase folder
        source_code_directory: Optional path to the user's selected source code directory
        
    Returns:
        Result with existing fix information if found, or None
    """
    if not ERROR_FIXING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Error fixing pipeline not available")
    
    try:
        # Get pipeline directory
        pipeline_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "services", "Error_fixing_pipelin")
        pipeline_dir = os.path.abspath(pipeline_dir)
        
        # Convert to absolute path if relative
        if not os.path.isabs(log_file_path):
            log_file_path = os.path.join(pipeline_dir, log_file_path)
        
        if not os.path.exists(log_file_path):
            raise HTTPException(status_code=404, detail=f"Log file not found: {log_file_path}")
        
        print(f"\n🔍 Checking for existing fixes for: {log_file_path}")
        
        # Step 1: Extract error from log file
        print("   Extracting error message from log file...")
        from app.services.Error_fixing_pipelin.parse_log_context import LogContextParser
        
        log_parser = LogContextParser(openair_codebase_file_name=openair_codebase_name)
        error_message = log_parser.extract_error_message(log_file_path)
        
        if not error_message:
            print("   No clear error extracted from log")
            return {
                "success": False,
                "found": False,
                "message": "No clear error message could be extracted from the log file."
            }
        
        print(f"   Error extracted: {error_message[:100]}...")
        
        # Step 2: Search embeddings
        print("   Searching 30,000+ commits for similar fixes...")
        from app.services.Error_fixing_pipelin.smart_commit_selector import CommitSearcher, SmartSelector
        
        embeddings_dir = os.path.join(pipeline_dir, 'resources', 'embeddings')
        if not os.path.exists(embeddings_dir):
            return {
                "success": False,
                "found": False,
                "message": "Embeddings directory not found. Please ensure embeddings are generated."
            }
        
        searcher = CommitSearcher(
            embeddings_dir=embeddings_dir,
            validate_commits=False,
            openair_codebase_file_name=openair_codebase_name
        )
        search_results = searcher.search(error_message, top_k=10)
        
        if not search_results:
            print("   No similar commits found")
            return {
                "success": True,
                "found": False,
                "message": "No similar fixes found in Git history."
            }
        
        # Step 3: Intelligent selection
        print("   Analyzing matches with smart selector...")
        selector = SmartSelector(use_llm=False)
        selection_result = selector.select_best_fix(error_message, search_results)
        
        # Add error message to selection_result for frontend
        selection_result['error_message'] = error_message
        
        # Step 4: Check results
        print("   Finalizing results...")
        
        # Check if a good fix was found
        if selection_result['status'] in ['auto_selected', 'suggested', 'llm_verified']:
            if selection_result['commit'] and selection_result['commit'].get('is_rca_commit'):
                # RCA fix found!
                confidence = selection_result['confidence']
                score = selection_result['commit'].get('boosted_score', 
                                                       selection_result['commit'].get('similarity', 0))
                
                print(f"   ✅ Found existing RCA fix! Confidence: {confidence}, Score: {score:.2%}")
                
                # Get git diff and branch information if available
                # Try both full and short commit hash (matching PyQt behavior)
                commit_hash = selection_result['commit'].get('commit_hash') or selection_result['commit'].get('commit_hash_short', '')
                commit_hash_short = selection_result['commit'].get('commit_hash_short', '')
                
                # If we have a full hash (40 chars), also try short version (7-8 chars)
                commit_hash_variants = []
                if commit_hash:
                    commit_hash_variants.append(commit_hash)
                    # If it's a full hash (40 chars), try short version
                    if len(commit_hash) == 40:
                        commit_hash_variants.append(commit_hash[:8])
                        commit_hash_variants.append(commit_hash[:7])
                    # Also try the short hash if different
                    if commit_hash_short and commit_hash_short != commit_hash:
                        commit_hash_variants.append(commit_hash_short)
                
                git_diff = None
                current_branch = 'develop'  # Default
                files_changed_summary = None
                
                if commit_hash:
                    try:
                        import subprocess
                        # Find git repository (matching PyQt behavior - prioritize user's selected directory)
                        possible_paths = []
                        
                        # First priority: User's selected source code directory (if provided)
                        # This matches PyQt line 6540: os.path.join(os.getcwd(), openair_codebase_file_name)
                        if source_code_directory and os.path.exists(source_code_directory):
                            possible_paths.append(source_code_directory)
                            print(f"   🔍 Checking user's selected directory: {source_code_directory}")
                        
                        # Second priority: Current working directory + codebase name (like PyQt)
                        current_cwd = os.getcwd()
                        possible_paths.extend([
                            os.path.join(current_cwd, openair_codebase_name),
                            os.path.join(current_cwd, 'Error_fixing_pipelin', openair_codebase_name),
                            os.path.join(current_cwd, 'Error_fixing_pipelin', 'openairinterface5g-develop'),
                            os.path.join(current_cwd, 'Error_fixing_pipelin', 'openairinterface5g-test'),
                        ])
                        
                        # Third priority: Pipeline directory paths (fallback)
                        possible_paths.extend([
                            os.path.join(pipeline_dir, openair_codebase_name),
                            os.path.join(pipeline_dir, 'openairinterface5g-develop'),
                            os.path.join(pipeline_dir, 'openairinterface5g-test'),
                        ])
                        
                        print(f"   🔍 Searching for Git repository in {len(possible_paths)} possible paths...")
                        git_dir = None
                        found_commit_hash = None
                        
                        for path in possible_paths:
                            if os.path.exists(path) and os.path.exists(os.path.join(path, '.git')):
                                print(f"   🔍 Checking Git repo at: {path}")
                                
                                # Try each commit hash variant to see if commit exists (matching PyQt behavior)
                                # PyQt only sets git_dir if commit exists (lines 6547-6558)
                                for hash_variant in commit_hash_variants:
                                    try:
                                        check_result = subprocess.run(
                                            ['git', 'cat-file', '-e', hash_variant],
                                            cwd=path,
                                            capture_output=True,
                                            timeout=2
                                        )
                                        if check_result.returncode == 0:
                                            # Commit exists! Set git_dir and found_commit_hash (matching PyQt line 6557)
                                            git_dir = path
                                            found_commit_hash = hash_variant
                                            print(f"   ✅ Found Git repository at: {git_dir} with commit {hash_variant}")
                                            break
                                    except Exception as e:
                                        continue
                                
                                # If we found a commit, we're done (matching PyQt line 6558)
                                if git_dir and found_commit_hash:
                                    break
                        
                        if not git_dir:
                            print(f"   ❌ Git repository not found in any of the {len(possible_paths)} paths")
                            print(f"   ⚠️ Tried commit hash variants: {commit_hash_variants}")
                        elif not found_commit_hash:
                            print(f"   ⚠️ Git repository found but commit {commit_hash} not found (tried variants: {commit_hash_variants})")
                            print(f"   🔍 Will try git show anyway with original hash: {commit_hash} (matching PyQt fallback behavior)")
                        
                        # Try git show if we have a git_dir (matching PyQt behavior)
                        # PyQt runs git show even if the commit hash check failed, so we do the same
                        if git_dir:
                            # Use found_commit_hash if available, otherwise use original commit_hash
                            hash_to_use = found_commit_hash if found_commit_hash else commit_hash
                            print(f"   🔍 Running git show for commit: {hash_to_use}")
                            git_show_result = subprocess.run(
                                ['git', 'show', '--stat', '--format=fuller', '--unified=3', hash_to_use],
                                cwd=git_dir,
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            
                            if git_show_result.returncode == 0:
                                git_diff = git_show_result.stdout
                                print(f"   ✅ Git diff retrieved successfully! Length: {len(git_diff)} characters")
                                
                                # Parse git show output to extract commit info
                                lines = git_show_result.stdout.split('\n')
                                commit_info = {}
                                message_lines = []
                                in_message = False
                                
                                for line in lines:
                                    if line.startswith('commit '):
                                        commit_info['full_hash'] = line.split()[1]
                                    elif line.startswith('Author:'):
                                        commit_info['author'] = line.replace('Author:', '').strip()
                                    elif line.startswith('AuthorDate:'):
                                        commit_info['date'] = line.replace('AuthorDate:', '').strip()
                                    elif line.startswith('Commit:'):
                                        commit_info['committer'] = line.replace('Commit:', '').strip()
                                    elif line.startswith('CommitDate:'):
                                        commit_info['commit_date'] = line.replace('CommitDate:', '').strip()
                                    elif line.startswith('    ') and not in_message:
                                        in_message = True
                                        message_lines.append(line.strip())
                                    elif in_message and line.startswith('    '):
                                        message_lines.append(line.strip())
                                    elif in_message and not line.startswith('    '):
                                        break
                                
                                # Update commit with parsed info
                                if commit_info.get('full_hash'):
                                    selection_result['commit']['commit_hash'] = commit_info['full_hash']
                                if commit_info.get('author'):
                                    selection_result['commit']['author'] = commit_info['author']
                                    selection_result['commit']['author_name'] = commit_info['author'].split('<')[0].strip()
                                if commit_info.get('date'):
                                    selection_result['commit']['date'] = commit_info['date']
                                    selection_result['commit']['date_iso'] = commit_info['date']
                                if commit_info.get('committer'):
                                    selection_result['commit']['committer'] = commit_info['committer']
                                if commit_info.get('commit_date'):
                                    selection_result['commit']['commit_date'] = commit_info['commit_date']
                                
                                # Update commit body with full message
                                if message_lines:
                                    selection_result['commit']['body'] = '\n'.join(message_lines)
                                    # Extract subject (first line)
                                    if len(message_lines) > 0:
                                        selection_result['commit']['subject'] = message_lines[0]
                                
                                # Extract files changed summary from git show output
                                for line in git_show_result.stdout.split('\n'):
                                    if 'files changed' in line.lower():
                                        files_changed_summary = line.strip()
                                        break
                            else:
                                print(f"   ⚠️ Git show failed with return code: {git_show_result.returncode}")
                                print(f"   Error: {git_show_result.stderr[:200]}")
                                # git_diff will remain None and we'll still return other details (matching PyQt fallback behavior)
                            
                            # Get current branch (matching PyQt behavior)
                            if git_dir:
                                branch_result = subprocess.run(
                                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                    cwd=git_dir,
                                    capture_output=True,
                                    text=True,
                                    timeout=2
                                )
                                if branch_result.returncode == 0:
                                    current_branch = branch_result.stdout.strip() or 'develop'
                        else:
                            print(f"   ❌ Git repository not found - cannot retrieve git diff")
                            print(f"   ⚠️ Git repository not found - cannot get branch info")
                    except Exception as e:
                        print(f"⚠️ Could not get git diff/branch info: {e}")
                        import traceback
                        traceback.print_exc()
                
                # error_message is already extracted at the beginning of the function
                # It's already added to selection_result above
                
                # Return the result
                return {
                    "success": True,
                    "found": True,
                    "confidence": confidence,
                    "score": score,
                    "commit": selection_result['commit'],
                    "reasoning": selection_result.get('reasoning', ''),
                    "selection_result": selection_result,
                    "git_diff": git_diff,
                    "current_branch": current_branch,
                    "files_changed_summary": files_changed_summary
                }
            else:
                print("   Found similar commits but no RCA fixes")
                return {
                    "success": True,
                    "found": False,
                    "message": "Similar commits found but no RCA fixes."
                }
        else:
            print("   No suitable fix found")
            return {
                "success": True,
                "found": False,
                "message": "No suitable fix found in Git history."
            }
            
    except Exception as e:
        print(f"⚠️ Error checking for existing fix: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error checking for existing fix: {str(e)}")

@router.post("/api/error-fixing/impact-analysis")
async def analyze_impact(log_file_path: str = Form(...)):
    """
    Analyze log file for impact analysis using error_patterns_enhanced.json
    This matches PyQt's LogLayerSeverityAnalyzer functionality
    
    Args:
        log_file_path: Path to the log file to analyze
        
    Returns:
        Impact analysis results with error counts, identified errors, and layer counts
    """
    try:
        import re
        
        # Get pipeline directory
        pipeline_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "services", "Error_fixing_pipelin")
        pipeline_dir = os.path.abspath(pipeline_dir)
        
        # Load error patterns from error_patterns_enhanced.json
        patterns_file = os.path.join(pipeline_dir, 'database', 'error_patterns_enhanced.json')
        if not os.path.exists(patterns_file):
            raise HTTPException(status_code=404, detail=f"Error patterns file not found: {patterns_file}")
        
        with open(patterns_file, 'r', encoding='utf-8') as f:
            patterns_data = json.load(f)
        
        patterns = patterns_data.get('patterns', {})
        
        # Resolve log file path (handle both absolute and relative paths)
        if os.path.isabs(log_file_path):
            log_file = log_file_path
        else:
            log_file = os.path.join(pipeline_dir, log_file_path)
        
        if not os.path.exists(log_file):
            raise HTTPException(status_code=404, detail=f"Log file not found: {log_file}")
        
        # Read log file
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            log_lines = f.readlines()
        
        # Calculate cascading layers (matching PyQt's LogLayerSeverityAnalyzer)
        # Protocol layer hierarchy: RRC → PDCP → RLC → MAC → PHY (downward cascade)
        def calculate_cascading_layers(primary_layer, impact):
            """Calculate cascading layer effects (matching PyQt functionality with proper layer hierarchy)"""
            cascade_chain = []
            
            # Primary layer (stage 1 - PRIMARY)
            cascade_chain.append({
                'layer': primary_layer,
                'impact': impact,
                'stage': 1
            })
            
            # Define layer hierarchy for proper cascading (matching PyQt PROTOCOL_DEPENDENCIES)
            # Protocol stack order (top to bottom): RRC → PDCP → RLC → MAC → PHY
            # Return full cascade chain with all levels (matching PyQt LogLayerSeverityAnalyzer behavior)
            layer_hierarchy = {
                'RRC': ['PDCP', 'RLC', 'MAC', 'PHY'],    # RRC → PDCP (1st) → RLC (2nd) → MAC (3rd) → PHY (4th)
                'PDCP': ['RLC', 'MAC', 'PHY'],            # PDCP → RLC (1st) → MAC (2nd) → PHY (3rd)
                'RLC': ['MAC', 'PHY'],                    # RLC → MAC (1st) → PHY (2nd)
                'MAC': ['PHY'],                           # MAC → PHY (1st)
                'PHY': []                                 # Bottom layer, no cascading
            }
            
            # Control plane layers (different hierarchy)
            # SCTP is NOT included as it's unnecessary per user feedback
            # Control plane layers cascade to RRC, and RRC cascades down through the full stack
            control_plane_hierarchy = {
                'NAS': ['RRC', 'PDCP', 'RLC', 'MAC', 'PHY'],    # NAS → RRC → PDCP → RLC → MAC → PHY
                'NGAP': ['RRC', 'PDCP', 'RLC', 'MAC', 'PHY']    # NGAP → RRC → PDCP → RLC → MAC → PHY
            }
            
            # Get cascading layers based on primary layer
            cascade_layers = []
            if primary_layer in layer_hierarchy:
                cascade_layers = layer_hierarchy[primary_layer]
            elif primary_layer in control_plane_hierarchy:
                cascade_layers = control_plane_hierarchy[primary_layer]
            
            # Add all cascade levels (matching PyQt format - shows PRIMARY, 1ST LEVEL, 2ND LEVEL, etc.)
            # This ensures all layers in the cascade chain are displayed
            for stage_idx, cascade_layer in enumerate(cascade_layers, start=2):  # Start at stage 2 (1ST LEVEL)
                # Determine appropriate impact description for each stage
                # Stage 2 (1ST LEVEL)
                if stage_idx == 2:
                    impact_descriptions_stage2 = {
                        'RRC': 'RRC failures may cause PDCP data integrity issues and connection problems',
                        'PDCP': 'PDCP failures may cause RLC layer data transmission issues',
                        'RLC': 'RLC failures may cause MAC layer scheduling and resource allocation issues',
                        'MAC': 'MAC failures may cause PHY layer signal transmission issues',
                        'NAS': 'NAS failures may cause RRC connection establishment issues',
                        'NGAP': 'NGAP failures may cause RRC connection establishment and core network connectivity issues'
                    }
                    cascade_impact = impact_descriptions_stage2.get(primary_layer, f'{primary_layer} failures may cause {cascade_layer} layer issues')
                # Stage 3 (2ND LEVEL) - shows PDCP → RLC, RLC → MAC, etc.
                elif stage_idx == 3:
                    if primary_layer == 'RRC':
                        cascade_impact = 'PDCP issues may cascade to RLC layer causing data transmission failures'
                    elif primary_layer == 'PDCP':
                        cascade_impact = 'RLC failures may cause MAC layer scheduling and resource allocation issues'
                    elif primary_layer == 'RLC':
                        cascade_impact = 'MAC failures may cause PHY layer signal transmission issues'
                    elif primary_layer == 'NAS':
                        cascade_impact = 'RRC issues may cascade to PDCP layer causing data integrity and connection problems'
                    elif primary_layer == 'NGAP':
                        cascade_impact = 'RRC issues may cascade to PDCP layer causing data integrity and connection problems'
                    else:
                        cascade_impact = f'{cascade_layers[stage_idx-3] if stage_idx-3 < len(cascade_layers) else "Previous layer"} issues may cascade to {cascade_layer} layer'
                # Stage 4 (3RD LEVEL) - shows RLC → MAC, MAC → PHY for RRC cascade
                elif stage_idx == 4:
                    if primary_layer == 'RRC':
                        cascade_impact = 'RLC issues may cascade to MAC layer causing scheduling problems'
                    elif primary_layer == 'PDCP':
                        cascade_impact = 'MAC failures may cause PHY layer signal transmission issues'
                    elif primary_layer == 'NAS':
                        cascade_impact = 'PDCP issues may cascade to RLC layer causing data transmission failures'
                    elif primary_layer == 'NGAP':
                        cascade_impact = 'PDCP issues may cascade to RLC layer causing data transmission failures'
                    else:
                        cascade_impact = f'{cascade_layers[stage_idx-3] if stage_idx-3 < len(cascade_layers) else "Previous layer"} issues may cascade to {cascade_layer} layer'
                # Stage 5 (4TH LEVEL) - shows MAC → PHY for RRC cascade
                elif stage_idx == 5:
                    if primary_layer == 'RRC':
                        cascade_impact = 'MAC issues may cascade to PHY layer causing signal transmission problems'
                    elif primary_layer == 'PDCP':
                        cascade_impact = 'MAC issues may cascade to PHY layer causing signal transmission problems'
                    elif primary_layer == 'NAS':
                        cascade_impact = 'RLC issues may cascade to MAC layer causing scheduling problems'
                    elif primary_layer == 'NGAP':
                        cascade_impact = 'RLC issues may cascade to MAC layer causing scheduling problems'
                    else:
                        cascade_impact = f'{cascade_layer} layer may be affected by upstream failures'
                # Stage 6 (5TH LEVEL) - shows MAC → PHY for NAS/NGAP cascade
                elif stage_idx == 6:
                    if primary_layer == 'NAS':
                        cascade_impact = 'MAC issues may cascade to PHY layer causing signal transmission problems'
                    elif primary_layer == 'NGAP':
                        cascade_impact = 'MAC issues may cascade to PHY layer causing signal transmission problems'
                    else:
                        cascade_impact = f'{cascade_layer} layer may be affected by upstream cascade effects'
                else:
                    cascade_impact = f'{cascade_layer} layer may be affected by upstream cascade effects'
                
                cascade_chain.append({
                    'layer': cascade_layer,
                    'impact': cascade_impact,
                    'stage': stage_idx  # 2 = 1ST LEVEL, 3 = 2ND LEVEL, etc.
                })
            
            return cascade_chain
        
        # Analyze log file using patterns
        identified_errors = {}
        error_counts = {}
        layer_counts = {}
        
        for error_type, error_config in patterns.items():
            pattern_list = error_config.get('patterns', [])
            severity = error_config.get('severity', 'medium')
            layer = error_config.get('layer', 'Unknown')
            impact = error_config.get('impact', 'Unknown impact')
            
            occurrences = []
            for line_num, line in enumerate(log_lines, 1):
                for pattern in pattern_list:
                    try:
                        if re.search(pattern, line, re.IGNORECASE):
                            occurrences.append({
                                'line_number': line_num,
                                'line': line.strip(),
                                'pattern': pattern,
                                'severity': severity,
                                'layer': layer,
                                'impact': impact,
                                'confidence': error_config.get('confidence_threshold', 0.7)
                            })
                            break  # Only match once per line
                    except re.error:
                        # Skip invalid regex patterns
                        continue
            
            if occurrences:
                # Calculate cascade chain for this error type (matching PyQt: line 6627)
                cascade_chain = calculate_cascading_layers(layer, impact)
                
                # Add cascade chain to each occurrence
                for occ in occurrences:
                    occ['cascade_chain'] = cascade_chain
                
                identified_errors[error_type] = occurrences
                error_counts[error_type] = len(occurrences)
                
                # Count layers
                if layer not in layer_counts:
                    layer_counts[layer] = 0
                layer_counts[layer] += len(occurrences)
        
        # Calculate impact scores (simplified version)
        def calculate_impact_score(error_type, severity):
            """Calculate impact scores for different layers"""
            severity_scores = {'critical': 0.9, 'high': 0.7, 'medium': 0.5, 'low': 0.3}
            base_score = severity_scores.get(severity.lower(), 0.5)
            return {
                'primary': base_score,
                'secondary': base_score * 0.7,
                'tertiary': base_score * 0.5
            }
        
        # Prepare results in PyQt format
        results = {
            'identified_errors': identified_errors,
            'error_counts': error_counts,
            'layer_counts': layer_counts,
            'total_errors': sum(error_counts.values()),
            'unique_error_types': len(identified_errors),
            'layers_affected': len(layer_counts)
        }
        
        return {
            "success": True,
            "results": results
        }
        
    except Exception as e:
        print(f"Impact analysis error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Impact analysis failed: {str(e)}")


# Code Assistant Endpoints

class ApplyPatchesRequest(BaseModel):
    """Request model for applying patches"""
    analysis_filename: str
    selected_code_patches: List[str] = []
    selected_config_patches: List[str] = []
    code_dir: Optional[str] = None

class RunInvestigationRequest(BaseModel):
    """Request model for running investigation commands"""
    analysis_filename: str

class CodeEvaluationRequest(BaseModel):
    """Request model for running code evaluation tests"""
    analysis_filename: str
    selected_code_patches: List[int] = []  # Indices of selected code patches
    selected_config_patches: List[int] = []  # Indices of selected config patches
    selected_layers: List[str] = []  # List of layer keys: ["layer1", "layer2", "layer3", "layer4"]
    code_dir: Optional[str] = None

@router.get("/api/code-assistant/bug-history")
async def get_bug_history():
    """Get list of bug analysis history files"""
    try:
        # Use the same path as PyQt: "backend/resources/bug_history" relative to project root
        # But since backend runs from Backend directory, we need "resources/bug_history"
        # However, PyQt saves to "backend/resources/bug_history" which is relative to project root
        # So we need to check both locations
        
        # First try: Backend/resources/bug_history (relative to Backend directory)
        history_dir = Path("resources/bug_history")
        
        # Check if first path exists
        if not history_dir.exists():
            # Try parent directory (project root) - check both lowercase and capital B
            project_root_dir = Path(__file__).parent.parent.parent
            alt_history_dir = project_root_dir / "backend" / "resources" / "bug_history"
            alt_history_dir2 = project_root_dir / "Backend" / "resources" / "bug_history"
            
            if alt_history_dir.exists():
                history_dir = alt_history_dir
            elif alt_history_dir2.exists():
                history_dir = alt_history_dir2
            else:
                # None found, create default and return empty
                history_dir.mkdir(parents=True, exist_ok=True)
                print(f"📂 No history directory found, created: {history_dir.absolute()}")
                return {
                    "success": True,
                    "history": [],
                    "message": "No history files found"
                }
        
        print(f"📂 Using history directory: {history_dir.absolute()}")
        print(f"📂 Directory exists: {history_dir.exists()}")
        
        # Get all history files and sort by timestamp (newest first)
        try:
            history_files = [f for f in history_dir.iterdir() if f.is_file() and f.suffix == '.json']
            history_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            print(f"📂 Found {len(history_files)} history files")
        except Exception as e:
            print(f"❌ Error reading history directory: {e}")
            return {
                "success": False,
                "history": [],
                "message": f"Error reading history directory: {str(e)}"
            }
        
        history_list = []
        for file_path in history_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                error_message = data.get('error_message', 'Unknown error') or 'Unknown error'
                timestamp = data.get('timestamp', '')
                
                # Format display text
                display_text = error_message[:100] + "..." if len(error_message) > 100 else error_message
                
                # Add timestamp to display
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%Y-%m-%d %H:%M")
                        display_text = f"[{time_str}] {display_text}"
                    except:
                        pass
                
                # Get patch counts
                results = data.get('results', {})
                phase3_fixes = results.get('phase3_fixes', {})
                fix_suggestion = phase3_fixes.get('fix_suggestion', {})
                code_count = len(fix_suggestion.get('code_patches', []))
                config_count = len(fix_suggestion.get('config_patches', []))
                display_text += f" [Code:{code_count}, Config:{config_count}]"
                
                history_list.append({
                    "filename": file_path.name,
                    "display_text": display_text,
                    "error_message": error_message,
                    "timestamp": timestamp,
                    "code_patches_count": code_count,
                    "config_patches_count": config_count
                })
                print(f"✅ Loaded history file: {file_path.name}")
            except Exception as e:
                print(f"❌ Error loading history file {file_path.name}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"📊 Total history items loaded: {len(history_list)}")
        
        return {
            "success": True,
            "history": history_list,
            "count": len(history_list)
        }
        
    except Exception as e:
        print(f"Error getting bug history: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get bug history: {str(e)}")

@router.get("/api/code-assistant/load-analysis/{filename}")
async def load_bug_analysis(filename: str):
    """Load a specific bug analysis file"""
    try:
        # Use the same path resolution as get_bug_history
        history_dir = Path("resources/bug_history")
        if not history_dir.exists():
            project_root_dir = Path(__file__).parent.parent.parent
            alt_history_dir = project_root_dir / "backend" / "resources" / "bug_history"
            if alt_history_dir.exists():
                history_dir = alt_history_dir
            else:
                # Also try Backend/resources/bug_history (capital B)
                alt_history_dir2 = project_root_dir / "Backend" / "resources" / "bug_history"
                if alt_history_dir2.exists():
                    history_dir = alt_history_dir2
        
        file_path = history_dir / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Analysis file not found: {filename}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract patch information
        results = data.get('results', {})
        phase3_fixes = results.get('phase3_fixes', {})
        fix_suggestion = phase3_fixes.get('fix_suggestion', {})
        
        code_patches = fix_suggestion.get('code_patches', [])
        config_patches = fix_suggestion.get('config_patches', [])
        
        # Format patches for display
        formatted_code_patches = []
        for patch in code_patches:
            function_name = patch.get('function_name', 'Unknown')
            file_path_str = patch.get('file_path', 'Unknown')
            file_name = os.path.basename(file_path_str)
            formatted_code_patches.append({
                "function_name": function_name,
                "file_path": file_path_str,
                "file_name": file_name,
                "display_text": f"{function_name} ({file_name})",
                "description": patch.get('description', 'No description'),
                "patch_type": patch.get('patch_type', 'modification'),
                "line_number": patch.get('line_number') or patch.get('line_numbers', ''),
                "original_code": patch.get('original_code', ''),
                "suggested_code": patch.get('suggested_code') or patch.get('patched_code') or patch.get('new_code', ''),
                "patch_data": patch
            })
        
        formatted_config_patches = []
        for patch in config_patches:
            param_name = patch.get('config_name', patch.get('parameter_name', 'Unknown'))
            file_path_str = patch.get('file_path', 'Unknown')
            file_name = os.path.basename(file_path_str)
            formatted_config_patches.append({
                "config_name": param_name,
                "file_path": file_path_str,
                "file_name": file_name,
                "display_text": f"{param_name} ({file_name})",
                "description": patch.get('description', 'No description'),
                "current_value": patch.get('current_value', ''),
                "suggested_value": patch.get('suggested_value') or patch.get('new_value', ''),
                "patch_data": patch
            })
        
        # Get error details
        error_message = data.get('error_message', 'Unknown error') or 'Unknown error'
        log_file = data.get('log_file', 'N/A')
        log_path = data.get('log_path', '')  # Include log_path for Electron UI
        timestamp = data.get('timestamp', 'N/A')
        code_dir = data.get('code_dir', '')
        results_data = data.get('results', {})  # Include full results
        
        # Get terminal commands from phase4_commands
        terminal_commands = []
        phase4_commands = results.get('phase4_commands', {})
        if phase4_commands:
            terminal_commands_data = phase4_commands.get('terminal_commands', [])
            if terminal_commands_data:
                for cmd in terminal_commands_data:
                    if isinstance(cmd, dict):
                        terminal_commands.append(cmd)
                    else:
                        terminal_commands.append({'command': str(cmd), 'explanation': 'Investigation command'})
        
        # Get git_metadata if this is from git history (for existing fixes)
        git_metadata = data.get('git_metadata', {})
        from_git_history = data.get('from_git_history', False)
        
        return {
            "success": True,
            "analysis": {
                "error_message": error_message,
                "log_file": log_file,
                "log_path": log_path,  # Include log_path (matching PyQt load_previous_bug_analysis)
                "timestamp": timestamp,
                "code_dir": code_dir,
                "results": results_data,  # Include full results (matching PyQt)
                "error_display": f"Error Message:\n{error_message}\n\nLog File: {log_file}\nTimestamp: {timestamp}\n",
                "code_patches": formatted_code_patches,
                "config_patches": formatted_config_patches,
                "terminal_commands": terminal_commands,
                "raw_data": data,
                # Include git metadata for existing fixes
                "git_metadata": git_metadata if git_metadata else None,
                "from_git_history": from_git_history
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error loading bug analysis: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to load bug analysis: {str(e)}")

@router.post("/api/code-assistant/apply-patches")
async def apply_patches(request: ApplyPatchesRequest):
    """Apply selected patches using unified patch applicator"""
    try:
        # Use the same path resolution as get_bug_history
        history_dir = Path("resources/bug_history")
        if not history_dir.exists():
            project_root_dir = Path(__file__).parent.parent.parent
            alt_history_dir = project_root_dir / "backend" / "resources" / "bug_history"
            if alt_history_dir.exists():
                history_dir = alt_history_dir
            else:
                # Also try Backend/resources/bug_history (capital B)
                alt_history_dir2 = project_root_dir / "Backend" / "resources" / "bug_history"
                if alt_history_dir2.exists():
                    history_dir = alt_history_dir2
        
        file_path = history_dir / request.analysis_filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Analysis file not found: {request.analysis_filename}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # Get code directory
        code_dir = request.code_dir or analysis_data.get('code_dir', '')
        if not code_dir:
            raise HTTPException(status_code=400, detail="Code directory is required. Please ensure the analysis includes a code directory.")
        
        openair_codebase_file_name = os.path.basename(code_dir.rstrip(os.sep))
        
        # Check if we have selected patches
        if not request.selected_code_patches and not request.selected_config_patches:
            raise HTTPException(status_code=400, detail="No patches selected for application")
        
        # Create a temporary fix_suggestions.json file
        # Use Error_fixing_pipelin/resources directory (where UnifiedPatchApplicator expects it)
        current_dir = Path(__file__).parent.parent
        error_pipeline_path = current_dir / "services" / "Error_fixing_pipelin"
        resources_dir = error_pipeline_path / "resources"
        resources_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fix_suggestions_file = resources_dir / f"fix_suggestions_{timestamp}.json"
        
        # Extract fix_suggestion from analysis
        results = analysis_data.get('results', {})
        phase3_fixes = results.get('phase3_fixes', {})
        fix_suggestion = phase3_fixes.get('fix_suggestion', {})
        
        # Filter patches to only include selected ones
        code_patches = fix_suggestion.get('code_patches', [])
        config_patches = fix_suggestion.get('config_patches', [])
        
        print(f"🔧 DEBUG: Received {len(request.selected_code_patches)} code patches and {len(request.selected_config_patches)} config patches")
        print(f"🔧 DEBUG: Available in analysis: {len(code_patches)} code patches, {len(config_patches)} config patches")
        
        # Filter code patches
        selected_code_patch_data = []
        for idx, patch in enumerate(code_patches):
            function_name = patch.get('function_name', 'Unknown')
            file_path_str = patch.get('file_path', 'Unknown')
            file_name = os.path.basename(file_path_str)
            display_text = f"{function_name} ({file_name})"
            
            if display_text in request.selected_code_patches:
                selected_code_patch_data.append(patch)
                print(f"🔧 DEBUG: ✅ Matched code patch {idx}: {display_text}")
            else:
                print(f"🔧 DEBUG: ❌ No match for code patch {idx}: '{display_text}' not in {request.selected_code_patches}")
        
        # Filter config patches
        selected_config_patch_data = []
        for idx, patch in enumerate(config_patches):
            param_name = patch.get('config_name', patch.get('parameter_name', 'Unknown'))
            file_path_str = patch.get('file_path', 'Unknown')
            file_name = os.path.basename(file_path_str)
            display_text = f"{param_name} ({file_name})"
            
            if display_text in request.selected_config_patches:
                selected_config_patch_data.append(patch)
                print(f"🔧 DEBUG: ✅ Matched config patch {idx}: {display_text}")
            else:
                print(f"🔧 DEBUG: ❌ No match for config patch {idx}: '{display_text}' not in {request.selected_config_patches}")
        
        print(f"🔧 DEBUG: Final filtered: {len(selected_code_patch_data)} code patches, {len(selected_config_patch_data)} config patches")
        
        # Create filtered fix_suggestion
        # UnifiedPatchApplicator expects structure: { "fix_suggestion": { "code_patches": [], "config_patches": [] } }
        # But it also needs code_dir, so we put it at the root level
        filtered_fix_suggestion = {
            "code_dir": code_dir,
            "fix_suggestion": {
                "code_dir": code_dir,
                "code_patches": selected_code_patch_data,
                "config_patches": selected_config_patch_data
            }
        }
        
        # Save to file
        with open(fix_suggestions_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_fix_suggestion, f, indent=2)
        
        # Get absolute path BEFORE changing directories (important!)
        absolute_file_path = str(fix_suggestions_file.absolute())
        print(f"🔧 Saved fix_suggestions file to: {fix_suggestions_file}")
        print(f"🔧 Absolute path: {absolute_file_path}")
        print(f"🔧 File exists: {fix_suggestions_file.exists()}")
        
        # Verify file was created correctly
        if not fix_suggestions_file.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create fix_suggestions file at {absolute_file_path}"
            )
        
        # Import and use unified patch applicator
        try:
            # Add the Error_fixing_pipelin directory to sys.path
            current_dir = Path(__file__).parent.parent
            error_pipeline_path = current_dir / "services" / "Error_fixing_pipelin"
            if str(error_pipeline_path) not in sys.path:
                sys.path.append(str(error_pipeline_path))
            
            from app.services.Error_fixing_pipelin.unified_patch_applicator import UnifiedPatchApplicator
            
            # Change to pipeline directory for proper execution
            original_cwd = os.getcwd()
            try:
                os.chdir(error_pipeline_path)
                
                # Verify file still exists after directory change (using absolute path)
                import os as os_module
                if not os_module.path.exists(absolute_file_path):
                    raise HTTPException(
                        status_code=500,
                        detail=f"Fix suggestions file not found after directory change: {absolute_file_path}"
                    )
                
                print(f"🔧 Creating UnifiedPatchApplicator with file: {absolute_file_path}")
                print(f"🔧 Current working directory: {os.getcwd()}")
                applicator = UnifiedPatchApplicator(absolute_file_path)
                
                # Apply patches with backup
                result = applicator.apply_all_patches(dry_run=False, backup=True)
                
                # Change back to original directory
                os.chdir(original_cwd)
                
                return {
                    "success": result.get("success", False),
                    "total_applied": result.get("total_applied", 0),
                    "total_failed": result.get("total_failed", 0),
                    "applied_code_patches": result.get("applied_code_patches", []),
                    "applied_config_patches": result.get("applied_config_patches", []),
                    "failed_patches": result.get("failed_patches", []),
                    "backup_location": result.get("backup_location", ""),
                    "message": f"Applied {result.get('total_applied', 0)} patches successfully"
                }
                
            finally:
                os.chdir(original_cwd)
                
        except ImportError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Could not import unified patch applicator: {str(e)}\nPlease ensure the Error_fixing_pipelin module is available."
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while applying patches: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error applying patches: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to apply patches: {str(e)}")

class GitCommitPushRequest(BaseModel):
    """Request model for Git commit and push operations"""
    commit_message: str
    should_push: bool = False
    code_dir: Optional[str] = None
    selected_code_patches: Optional[List[str]] = []  # List of patch names/display_text
    selected_config_patches: Optional[List[str]] = []  # List of patch names/display_text
    analysis_filename: Optional[str] = None  # To check if this is from git history (already in embeddings)

@router.post("/api/code-assistant/git-commit-push")
async def git_commit_and_push(request: GitCommitPushRequest):
    """Perform Git commit and optionally push to remote (matching PyQt perform_git_commit_and_push)"""
    try:
        import subprocess
        
        result = {
            "success": False,
            "committed": False,
            "pushed": False,
            "commit_hash": None,
            "error": None
        }
        
        # Get code directory
        code_dir = request.code_dir
        if not code_dir:
            # Try to get from the most recent fix_suggestions.json file
            try:
                current_dir = Path(__file__).parent.parent
                error_pipeline_path = current_dir / "services" / "Error_fixing_pipelin"
                resources_dir = error_pipeline_path / "resources"
                
                if resources_dir.exists():
                    json_files = [f for f in os.listdir(resources_dir) if f.startswith('fix_suggestions_') and f.endswith('.json')]
                    if json_files:
                        json_files.sort(reverse=True)
                        fix_suggestions_file = resources_dir / json_files[0]
                        with open(fix_suggestions_file, 'r', encoding='utf-8') as f:
                            suggestions_data = json.load(f)
                        code_dir = suggestions_data.get('code_dir', None)
            except Exception as e:
                print(f"Error reading code directory from fix_suggestions: {e}")
        
        if code_dir:
            openair_codebase_file_name = os.path.basename(code_dir.rstrip(os.sep))
        else:
            openair_codebase_file_name = "openairinterface5g-develop"  # Default fallback
        
        # Get the OpenAirInterface5G directory path (matching PyQt line 14866)
        # Try multiple possible paths with priority matching PyQt
        current_dir = Path(__file__).parent.parent
        error_pipeline_path = current_dir / "services" / "Error_fixing_pipelin"
        
        possible_paths = []
        
        # First priority: User's code_dir (if provided and exists)
        if code_dir and os.path.exists(code_dir):
            possible_paths.append(code_dir)
            print(f"   🔍 Checking user's code_dir: {code_dir}")
        
        # Second priority: PyQt-style relative path (matching PyQt line 14866)
        pyqt_style_path = os.path.join('Error_fixing_pipelin', openair_codebase_file_name)
        if os.path.exists(pyqt_style_path):
            possible_paths.append(pyqt_style_path)
            print(f"   🔍 Checking PyQt-style path: {pyqt_style_path}")
        
        # Third priority: Current working directory paths (like PyQt fallback)
        current_cwd = os.getcwd()
        possible_paths.extend([
            os.path.join(current_cwd, openair_codebase_file_name),
            os.path.join(current_cwd, 'Error_fixing_pipelin', openair_codebase_file_name),
        ])
        
        # Fourth priority: Pipeline directory paths (fallback)
        possible_paths.extend([
            str(error_pipeline_path / openair_codebase_file_name),
            str(error_pipeline_path / 'openairinterface5g-develop'),
            str(error_pipeline_path / 'openairinterface5g-test'),
        ])
        
        print(f"   🔍 Searching for Git repository in {len(possible_paths)} possible paths...")
        
        oai_dir = None
        for path in possible_paths:
            # Ensure path is absolute
            abs_path = os.path.abspath(os.path.normpath(path))
            if os.path.exists(abs_path) and os.path.isdir(abs_path) and os.path.exists(os.path.join(abs_path, '.git')):
                # Verify it's a valid git repo
                print(f"   🔍 Checking Git repo at: {abs_path}")
                try:
                    check_result = subprocess.run(
                        ['git', 'status'],
                        cwd=abs_path,
                        capture_output=True,
                        timeout=2
                    )
                    if check_result.returncode == 0:
                        oai_dir = abs_path  # Always use absolute path
                        print(f"   ✅ Found valid Git repository at: {oai_dir}")
                        print(f"   🔍 DEBUG [endpoints.py:3504] oai_dir type: {type(oai_dir)}")
                        print(f"   🔍 DEBUG [endpoints.py:3504] oai_dir value: {repr(oai_dir)}")
                        print(f"   🔍 DEBUG [endpoints.py:3504] oai_dir str: {str(oai_dir)}")
                        if hasattr(oai_dir, '__class__'):
                            print(f"   🔍 DEBUG [endpoints.py:3504] oai_dir class: {oai_dir.__class__.__name__}")
                        break
                    else:
                        print(f"   ⚠️ Git status check failed for: {abs_path}")
                except Exception as e:
                    print(f"   ⚠️ Error checking Git repo at {abs_path}: {e}")
                    continue
        
        if not oai_dir:
            print(f"   ❌ Git repository not found in any of the {len(possible_paths)} paths")
            result["error"] = f"Git repository not found. Please ensure the source code directory is a valid Git repository.\n\nTried paths:\n" + "\n".join([f"  - {p}" for p in possible_paths])
            return result
        
        print(f"🔍 DEBUG [Git Operations]:")
        print(f"  Code directory: {code_dir}")
        print(f"  Codebase folder name: {openair_codebase_file_name}")
        print(f"  Git repository path: {oai_dir}")
        print(f"  Current working directory: {os.getcwd()}")
        
        # Check if we're in a Git repository
        git_check = subprocess.run(
            ["git", "status"],
            capture_output=True,
            text=True,
            cwd=oai_dir,
            timeout=10
        )
        
        if git_check.returncode != 0:
            result["error"] = "Not a Git repository or Git not available"
            return result
        
        # Add all changes
        add_result = subprocess.run(
            ["git", "add", "."],
            capture_output=True,
            text=True,
            cwd=oai_dir,
            timeout=10
        )
        
        if add_result.returncode != 0:
            result["error"] = f"Failed to add changes: {add_result.stderr}"
            return result
        
        # Check if there are changes to commit
        diff_check = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
            text=True,
            cwd=oai_dir,
            timeout=10
        )
        
        if diff_check.returncode == 0:
            result["error"] = "No changes to commit - patches may have been applied outside the Git repository or files are unchanged"
            return result
        
        # Commit changes
        commit_result = subprocess.run(
            ["git", "commit", "-m", request.commit_message],
            capture_output=True,
            text=True,
            cwd=oai_dir,
            timeout=10
        )
        
        if commit_result.returncode != 0:
            result["error"] = f"Failed to commit: {commit_result.stderr}"
            return result
        
        result["committed"] = True
        
        # Get commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=oai_dir,
            timeout=5
        )
        
        full_hash = None
        if hash_result.returncode == 0:
            full_hash = hash_result.stdout.strip()
            result["commit_hash"] = full_hash[:8]  # Short for display
            result["full_commit_hash"] = full_hash  # Full for embedding update
        
        # Get commit details for logging
        commit_output = commit_result.stdout.strip() if commit_result.stdout else ""
        commit_error = commit_result.stderr.strip() if commit_result.stderr else ""
        
        # Get commit details (files changed, stats, etc.)
        commit_details = ""
        if full_hash:
            try:
                # Get detailed commit information
                show_result = subprocess.run(
                    ["git", "show", "--stat", "--oneline", full_hash],
                    capture_output=True,
                    text=True,
                    cwd=oai_dir,
                    timeout=5
                )
                if show_result.returncode == 0:
                    commit_details = show_result.stdout.strip()
            except Exception as e:
                print(f"⚠️ Error getting commit details: {e}")
        
        # Store commit information in code assistant history
        try:
            commit_record = {
                "activity_type": "git-commit",
                "activity_label": "Git Commit",
                "title": request.analysis_filename or "Git Commit",
                "timestamp": datetime.utcnow().isoformat(),
                "record": {
                    "commit_hash": result.get("commit_hash"),
                    "full_commit_hash": full_hash,
                    "commit_message": request.commit_message,
                    "commit_output": commit_output,
                    "commit_error": commit_error if commit_error else None,
                    "commit_details": commit_details if commit_details else None,
                    "code_dir": code_dir or str(oai_dir) if oai_dir else None,
                    "should_push": request.should_push,
                    "pushed": False,  # Will be updated below if push succeeds
                    "analysis_filename": request.analysis_filename,
                    "selected_code_patches": request.selected_code_patches or [],
                    "selected_config_patches": request.selected_config_patches or []
                }
            }
            
            # Append to code assistant history
            append_history_record("code_assistant_history.json", commit_record)
            print(f"✅ Commit details stored in code assistant history: {result.get('commit_hash')}")
        except Exception as e:
            print(f"⚠️ Error storing commit details in history: {e}")
            # Don't fail the commit if history storage fails
        
        # Push to remote if requested
        if request.should_push and result["committed"]:
            push_result = subprocess.run(
                ["git", "push"],
                capture_output=True,
                text=True,
                cwd=oai_dir,
                timeout=30
            )
            
            if push_result.returncode == 0:
                result["pushed"] = True
                # Update the history record with push status
                try:
                    # Load the history and update the last entry
                    from app.services.history_logger import load_history_entries
                    import json
                    
                    # Get history directory path (matching history_logger.py)
                    history_dir = Path(__file__).parent.parent / "resources" / "history"
                    if not history_dir.exists():
                        history_dir = Path(__file__).parent.parent.parent / "Backend" / "resources" / "history"
                    
                    history_file = history_dir / "code_assistant_history.json"
                    
                    if history_file.exists():
                        entries = load_history_entries("code_assistant_history.json")
                        if entries and entries[-1].get("record", {}).get("full_commit_hash") == full_hash:
                            entries[-1]["record"]["pushed"] = True
                            entries[-1]["record"]["push_output"] = push_result.stdout.strip() if push_result.stdout else ""
                            # Write updated entries back to file
                            history_file.parent.mkdir(parents=True, exist_ok=True)
                            with history_file.open("w", encoding="utf-8") as fp:
                                json.dump(entries, fp, ensure_ascii=False, indent=2)
                            print(f"✅ Updated commit history with push status")
                except Exception as e:
                    print(f"⚠️ Error updating push status in history: {e}")
            else:
                result["error"] = f"Commit successful but push failed: {push_result.stderr}"
                result["success"] = True  # Commit succeeded, so partial success
                return result
        
        # Git-commit embeddings refresh on Start RCA Analysis (commit-gated), not after each commit.
        if result.get("committed"):
            result["embedding_updated"] = False
        # ========================================
        
        result["success"] = True
        return result
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "committed": False,
            "pushed": False,
            "commit_hash": None,
            "error": "Git operation timed out. Please try again."
        }
    except Exception as e:
        print(f"Error performing Git operations: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "committed": False,
            "pushed": False,
            "commit_hash": None,
            "error": str(e)
        }

@router.post("/api/code-assistant/run-investigation")
async def run_investigation_commands(request: RunInvestigationRequest):
    """Run investigation commands from the analysis"""
    try:
        # Use the same path resolution as get_bug_history
        history_dir = Path("resources/bug_history")
        if not history_dir.exists():
            project_root_dir = Path(__file__).parent.parent.parent
            alt_history_dir = project_root_dir / "backend" / "resources" / "bug_history"
            if alt_history_dir.exists():
                history_dir = alt_history_dir
        
        file_path = history_dir / request.analysis_filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Analysis file not found: {request.analysis_filename}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # Get terminal commands from phase4_commands
        results = analysis_data.get('results', {})
        terminal_commands = []
        phase4_commands = results.get('phase4_commands', {})
        if phase4_commands:
            terminal_commands_data = phase4_commands.get('terminal_commands', [])
            
            # Handle nested structure: if terminal_commands_data is a dict, extract the actual array
            if isinstance(terminal_commands_data, dict):
                terminal_commands_data = terminal_commands_data.get('terminal_commands', [])
            
            if terminal_commands_data:
                for cmd in terminal_commands_data:
                    if isinstance(cmd, dict):
                        terminal_commands.append(cmd)
                    else:
                        terminal_commands.append({'command': str(cmd), 'explanation': 'Investigation command'})
        
        if not terminal_commands:
            return {
                "success": False,
                "message": "No investigation commands available for this analysis.",
                "commands": [],
                "results": []
            }
        
        # Execute commands one by one
        import subprocess
        command_results = []
        
        for i, cmd_info in enumerate(terminal_commands, 1):
            command = cmd_info['command']
            explanation = cmd_info.get('explanation', 'No explanation provided')
            
            result_entry = {
                "command_number": i,
                "total_commands": len(terminal_commands),
                "command": command,
                "explanation": explanation,
                "status": "pending",
                "output": "",
                "stderr": "",
                "return_code": None,
                "error": None
            }
            
            try:
                # Execute the command
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                result_entry["return_code"] = result.returncode
                result_entry["output"] = result.stdout
                result_entry["stderr"] = result.stderr
                
                if result.returncode == 0:
                    result_entry["status"] = "success"
                else:
                    result_entry["status"] = "failed"
                    
            except subprocess.TimeoutExpired:
                result_entry["status"] = "timeout"
                result_entry["error"] = "Command timed out after 30 seconds"
            except Exception as e:
                result_entry["status"] = "error"
                result_entry["error"] = str(e)
            
            command_results.append(result_entry)
        
        return {
            "success": True,
            "message": f"Executed {len(terminal_commands)} commands",
            "commands": terminal_commands,
            "results": command_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error running investigation commands: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to run investigation commands: {str(e)}")


def _parse_history_timestamp(timestamp_value: Optional[str]) -> Optional[datetime]:
    if not timestamp_value:
        return None
    try:
        return datetime.fromisoformat(timestamp_value)
    except ValueError:
        try:
            return datetime.strptime(timestamp_value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def _append_test_generation_history(filename: str, request: TestGenerationHistoryRequest) -> Dict[str, Any]:
    metadata = dict(request.metadata) if request.metadata else {}
    parsed_timestamp = _parse_history_timestamp(request.timestamp)
    if request.timestamp and parsed_timestamp is None:
        metadata.setdefault("provided_timestamp", request.timestamp)

    record = {
        "template_name": request.template_name,
        "prompt": request.prompt,
        "output": request.output,
        "metadata": metadata,
    }

    file_path = append_history_record(filename, record, timestamp=parsed_timestamp)
    return {
        "success": True,
        "message": f"History stored in {filename}",
        "file_path": str(file_path),
    }


@router.post("/api/history/test-script")
async def log_test_script_history(request: TestGenerationHistoryRequest):
    try:
        return _append_test_generation_history("test_script_history.json", request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log test script history: {str(e)}")


@router.post("/api/history/test-case")
async def log_test_case_history(request: TestGenerationHistoryRequest):
    try:
        return _append_test_generation_history("test_case_history.json", request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log test case history: {str(e)}")


@router.post("/api/history/bug-discovery")
async def log_bug_discovery_history(request: BugDiscoveryHistoryRequest):
    try:
        metadata = dict(request.metadata) if request.metadata else {}
        if request.analysis_type:
            metadata.setdefault("analysis_type", request.analysis_type)

        parsed_timestamp = _parse_history_timestamp(request.timestamp)
        if request.timestamp and parsed_timestamp is None:
            metadata.setdefault("provided_timestamp", request.timestamp)

        record = {
            "log_file": request.log_file,
            "output": request.output,
            "metadata": metadata,
        }

        file_path = append_history_record(
            "bug_discovery_history.json",
            record,
            timestamp=parsed_timestamp,
        )
        return {
            "success": True,
            "message": "Bug discovery history stored successfully",
            "file_path": str(file_path),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log bug discovery history: {str(e)}")

# ===== CODE EVALUATION ENDPOINTS =====

@router.get("/api/code-evaluation/bug-history")
async def get_code_evaluation_bug_history():
    """Get list of bug analysis history files for Code Evaluation (reuses code-assistant endpoint logic)"""
    # Reuse the same endpoint as code-assistant since they use the same bug history
    return await get_bug_history()

@router.get("/api/code-evaluation/load-analysis/{filename}")
async def load_code_evaluation_analysis(filename: str):
    """Load a specific bug analysis file for Code Evaluation (reuses code-assistant endpoint logic)"""
    # Reuse the same endpoint as code-assistant since they use the same analysis format
    return await load_bug_analysis(filename)

@router.post("/api/code-evaluation/run-tests")
async def run_code_evaluation_tests(request: CodeEvaluationRequest):
    """Run code evaluation tests using the selected layers"""
    try:
        # Initialize evaluators (singleton pattern - create once, reuse)
        if not hasattr(run_code_evaluation_tests, '_code_testing_engine'):
            run_code_evaluation_tests._code_testing_engine = CodeTestingEngine()
            run_code_evaluation_tests._spec_reference_evaluator = SpecReferenceEvaluator()
            run_code_evaluation_tests._llm_judge_evaluator = LLMJudgeEvaluator()
        
        code_testing_engine = run_code_evaluation_tests._code_testing_engine
        spec_reference_evaluator = run_code_evaluation_tests._spec_reference_evaluator
        llm_judge_evaluator = run_code_evaluation_tests._llm_judge_evaluator
        
        # Load analysis file
        history_dir = Path("resources/bug_history")
        if not history_dir.exists():
            project_root_dir = Path(__file__).parent.parent.parent
            alt_history_dir = project_root_dir / "backend" / "resources" / "bug_history"
            if alt_history_dir.exists():
                history_dir = alt_history_dir
            else:
                alt_history_dir2 = project_root_dir / "Backend" / "resources" / "bug_history"
                if alt_history_dir2.exists():
                    history_dir = alt_history_dir2
        
        file_path = history_dir / request.analysis_filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Analysis file not found: {request.analysis_filename}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # Get code directory
        code_dir = request.code_dir or analysis_data.get('code_dir', '')
        if not code_dir:
            raise HTTPException(status_code=400, detail="Code directory is required. Please ensure the analysis includes a code directory.")
        
        # Extract patches from analysis
        results = analysis_data.get('results', {})
        phase3_fixes = results.get('phase3_fixes', {})
        fix_suggestion = phase3_fixes.get('fix_suggestion', {})
        
        all_code_patches = fix_suggestion.get('code_patches', [])
        all_config_patches = fix_suggestion.get('config_patches', [])
        
        # Filter selected patches based on indices
        selected_code_patches = [all_code_patches[i] for i in request.selected_code_patches if i < len(all_code_patches)]
        selected_config_patches = [all_config_patches[i] for i in request.selected_config_patches if i < len(all_config_patches)]
        
        if not selected_code_patches and not selected_config_patches:
            raise HTTPException(status_code=400, detail="No patches selected for evaluation")
        
        if not request.selected_layers:
            raise HTTPException(status_code=400, detail="No validation layers selected")
        
        selected_layer_keys = set(request.selected_layers)
        layer_results = []
        all_output_lines = []
        
        # Layer 1: Syntax & Structural Validation
        if 'layer1' in selected_layer_keys:
            try:
                layer1_lines = code_testing_engine.run_layer1_syntax_validation(
                    selected_code_patches,
                    code_dir,
                    config_patches=selected_config_patches,
                )
                all_output_lines.extend(layer1_lines)
                all_output_lines.append("")
                layer_results.append({
                    "layer": "layer1",
                    "label": "Layer 1: Syntax & Structural Validation",
                    "status": "completed",
                    "output": "\n".join(layer1_lines),
                    "output_lines": layer1_lines
                })
            except Exception as e:
                error_msg = f"Layer 1 failed: {str(e)}"
                all_output_lines.append(error_msg)
                layer_results.append({
                    "layer": "layer1",
                    "label": "Layer 1: Syntax & Structural Validation",
                    "status": "error",
                    "output": error_msg,
                    "error": str(e)
                })
        else:
            layer_results.append({
                "layer": "layer1",
                "label": "Layer 1: Syntax & Structural Validation",
                "status": "skipped",
                "output": "Layer 1: Syntax & Structural Validation not selected."
            })
        
        # Layer 2: 3GPP Spec Reference Analysis
        if 'layer2' in selected_layer_keys:
            try:
                # Extract spec context from analysis (matching PyQt logic)
                phase3 = results.get('phase3_fixes', {})
                fix_suggestion = phase3.get('fix_suggestion', {})
                
                spec_context = (
                    fix_suggestion.get('specification_context') or
                    phase3.get('specification_context') or
                    results.get('specification_context') or
                    results.get('phase2_spec_reference', {}).get('spec_context', '') or
                    results.get('spec_reference', {}).get('spec_context', '')
                )
                
                error_summary = analysis_data.get('error_message', 'Unknown error') or 'Unknown error'
                
                # Build change entries for spec evaluation (matching PyQt format)
                code_changes = []
                for patch in selected_code_patches:
                    original = patch.get('original_code', '') or patch.get('existing_code', '') or ""
                    patched = patch.get('suggested_code', '') or patch.get('patched_code', '') or patch.get('new_code', '') or ""
                    code_changes.append({
                        "change_type": "code",
                        "file_path": patch.get('file_path', ''),
                        "function_name": patch.get('function_name', ''),
                        "description": patch.get('description', ''),
                        "original_code": original,
                        "patched_code": patched,
                        "suggested_code": patched,  # Alias for compatibility
                    })
                
                config_changes = []
                for patch in selected_config_patches:
                    param_name = patch.get('config_name', '') or patch.get('parameter_name', '') or patch.get('setting', '')
                    current_value = patch.get('current_value', '')
                    new_value = patch.get('suggested_value', '') or patch.get('new_value', '') or patch.get('patched_value', '')
                    config_changes.append({
                        "change_type": "config",
                        "file_path": patch.get('file_path', ''),
                        "config_name": param_name,
                        "parameter_name": param_name,  # Alias for compatibility
                        "description": patch.get('description', ''),
                        "current_value": current_value,
                        "proposed_value": new_value,  # CRITICAL: LLM Judge looks for this field
                        "suggested_value": new_value,
                        "new_value": new_value,  # Alias for compatibility
                    })
                
                combined_changes = code_changes + config_changes
                
                if not combined_changes:
                    output_lines = ["Layer 2: 3GPP Spec Reference Analysis", "  ⚠️ No code or config patches selected – skipping spec reference analysis."]
                    all_output_lines.extend(output_lines)
                    all_output_lines.append("")
                    layer_results.append({
                        "layer": "layer2",
                        "label": "Layer 2: 3GPP Spec Reference Analysis",
                        "status": "skipped",
                        "output": "\n".join(output_lines),
                        "output_lines": output_lines
                    })
                elif spec_context:
                    # Extract additional notes
                    additional_notes_parts = []
                    root_cause = fix_suggestion.get('root_cause_analysis')
                    if root_cause:
                        additional_notes_parts.append(f"Root Cause Analysis: {root_cause}")
                    
                    investigation_steps = fix_suggestion.get('investigation_steps')
                    if investigation_steps:
                        formatted_steps = "\n".join(f"- {step}" for step in investigation_steps if step)
                        if formatted_steps:
                            additional_notes_parts.append("Investigation Steps:\n" + formatted_steps)
                    
                    additional_notes = "\n\n".join(additional_notes_parts) if additional_notes_parts else None
                    
                    result = spec_reference_evaluator.evaluate(
                        error_summary=error_summary,
                        code_changes=combined_changes,
                        spec_context=spec_context,
                        additional_notes=additional_notes,
                    )
                    
                    # Format output (matching PyQt format)
                    output_lines = [f"Layer 2: 3GPP Spec Reference Analysis"]
                    if result.status == "success":
                        verdict = (result.verdict or "UNKNOWN").upper()
                        verdict_icon = {
                            "APPROVE": "✅",
                            "APPROVE_WITH_WARNINGS": "⚠️",
                            "REJECT": "❌",
                        }.get(verdict, "ℹ️")
                        verdict_line = f"  {verdict_icon} Verdict: {verdict.replace('_', ' ').title()}"
                        if result.confidence is not None:
                            verdict_line += f" (Confidence: {result.confidence:.2f})"
                        output_lines.append(verdict_line)
                        
                        if result.will_fix_issue is not None:
                            fix_text = "Yes" if result.will_fix_issue else "No"
                            output_lines.append(f"  Fix Effectiveness: {fix_text}")
                        
                        if result.summary:
                            output_lines.append("  Summary")
                            # Wrap summary text
                            summary_lines = result.summary.split('\n')
                            for line in summary_lines:
                                output_lines.append(f"    {line}")
                        
                        if result.issues:
                            output_lines.append("  Spec Findings")
                            for issue in result.issues:
                                severity = issue.get('severity', 'UNKNOWN')
                                reference = issue.get('spec_reference', 'Unknown reference')
                                description = issue.get('description', '')
                                output_lines.append(f"    [{severity}] {reference}")
                                if description:
                                    # Wrap description if it's multi-line
                                    desc_lines = description.split('\n')
                                    for desc_line in desc_lines:
                                        output_lines.append(f"    {desc_line}")
                                action = issue.get('suggested_action')
                                if action:
                                    output_lines.append(f"    Suggested action: {action}")
                        
                        if result.reasoning:
                            output_lines.append("  Reasoning")
                            reasoning_lines = result.reasoning.split('\n')
                            for line in reasoning_lines:
                                output_lines.append(f"    {line}")
                        
                        if result.recommendations:
                            output_lines.append("  Recommendations")
                            for idx, rec in enumerate(result.recommendations, start=1):
                                output_lines.append(f"    {idx}. {rec}")
                    else:
                        for message in result.messages:
                            output_lines.append(f"  {message}")
                    
                    all_output_lines.extend(output_lines)
                    all_output_lines.append("")
                    layer_results.append({
                        "layer": "layer2",
                        "label": "Layer 2: 3GPP Spec Reference Analysis",
                        "status": "completed",
                        "output": "\n".join(output_lines),
                        "output_lines": output_lines,
                        "verdict": result.verdict if result.status == "success" else None,
                        "confidence": result.confidence if result.status == "success" else None
                    })
                else:
                    output_lines = ["Layer 2: 3GPP Spec Reference Analysis", "  ⚠️ No specification context found in the analysis data."]
                    all_output_lines.extend(output_lines)
                    all_output_lines.append("")
                    layer_results.append({
                        "layer": "layer2",
                        "label": "Layer 2: 3GPP Spec Reference Analysis",
                        "status": "skipped",
                        "output": "\n".join(output_lines),
                        "output_lines": output_lines
                    })
            except Exception as e:
                error_msg = f"Layer 2 failed: {str(e)}"
                all_output_lines.append(error_msg)
                layer_results.append({
                    "layer": "layer2",
                    "label": "Layer 2: 3GPP Spec Reference Analysis",
                    "status": "error",
                    "output": error_msg,
                    "error": str(e)
                })
        else:
            layer_results.append({
                "layer": "layer2",
                "label": "Layer 2: 3GPP Spec Reference Analysis",
                "status": "skipped",
                "output": "Layer 2: 3GPP Spec Reference Analysis not selected."
            })
        
        # Layer 3: LLM as Judge
        if 'layer3' in selected_layer_keys:
            try:
                error_summary = analysis_data.get('error_message', 'Unknown error') or 'Unknown error'
                
                # Build change entries (matching PyQt format)
                code_changes = []
                for patch in selected_code_patches:
                    original = patch.get('original_code', '') or patch.get('existing_code', '') or ""
                    patched = patch.get('suggested_code', '') or patch.get('patched_code', '') or patch.get('new_code', '') or ""
                    code_changes.append({
                        "change_type": "code",
                        "file_path": patch.get('file_path', ''),
                        "function_name": patch.get('function_name', ''),
                        "description": patch.get('description', ''),
                        "original_code": original,
                        "patched_code": patched,
                        "suggested_code": patched,  # Alias for compatibility
                    })
                
                config_changes = []
                for patch in selected_config_patches:
                    param_name = patch.get('config_name', '') or patch.get('parameter_name', '') or patch.get('setting', '')
                    current_value = patch.get('current_value', '')
                    new_value = patch.get('suggested_value', '') or patch.get('new_value', '') or patch.get('patched_value', '')
                    config_changes.append({
                        "change_type": "config",
                        "file_path": patch.get('file_path', ''),
                        "config_name": param_name,
                        "parameter_name": param_name,  # Alias for compatibility
                        "description": patch.get('description', ''),
                        "current_value": current_value,
                        "proposed_value": new_value,  # CRITICAL: LLM Judge looks for this field
                        "suggested_value": new_value,
                        "new_value": new_value,  # Alias for compatibility
                    })
                
                result = llm_judge_evaluator.evaluate(
                    error_summary=error_summary,
                    code_changes=code_changes,
                    config_changes=config_changes,
                )
                
                # Format output (matching PyQt format)
                output_lines = [f"Layer 3: LLM as Judge"]
                if result.status == "success":
                    verdict = (result.verdict or "UNKNOWN").upper()
                    # Map verdicts to PyQt format
                    verdict_mapping = {
                        "APPROVE": "PASS",
                        "APPROVE_WITH_WARNINGS": "APPROVE_WITH_WARNINGS",
                        "REJECT": "FAIL",
                    }
                    mapped_verdict = verdict_mapping.get(verdict, verdict)
                    icon = {
                        "PASS": "✅",
                        "FAIL": "❌",
                        "NEEDS_REVIEW": "⚠️",
                        "APPROVE_WITH_WARNINGS": "⚠️",
                    }.get(mapped_verdict, "ℹ️")
                    verdict_line = f"  {icon} Verdict: {mapped_verdict.replace('_', ' ').title()}"
                    if result.confidence is not None:
                        verdict_line += f" (Confidence: {result.confidence:.2f})"
                    output_lines.append(verdict_line)
                    
                    if result.summary:
                        output_lines.append("  Summary")
                        summary_lines = result.summary.split('\n')
                        for line in summary_lines:
                            output_lines.append(f"    {line}")
                    
                    if result.reasoning:
                        output_lines.append("  Reasoning")
                        reasoning_lines = result.reasoning.split('\n')
                        for line in reasoning_lines:
                            output_lines.append(f"    {line}")
                    
                    if result.criteria:
                        output_lines.append("  Criteria Evaluation")
                        # First pass: find the longest criterion name for alignment
                        criterion_items = []
                        max_name_length = 0
                        for key, value in result.criteria.items():
                            criterion_name = key.replace('_', ' ').title()
                            criterion_items.append((criterion_name, value))
                            max_name_length = max(max_name_length, len(criterion_name))
                        
                        # Second pass: format with proper alignment (fixed width for criterion name)
                        # Use 50 characters as the fixed width for criterion name column
                        fixed_width = 50
                        for criterion_name, value in criterion_items:
                            result_text = str(value).upper() if isinstance(value, str) else str(value)
                            # Pad criterion name to fixed width, then add result
                            padded_name = criterion_name.ljust(fixed_width)
                            output_lines.append(f"    {padded_name}{result_text}")
                    
                    if result.recommendations:
                        output_lines.append("  Recommendations")
                        for idx, rec in enumerate(result.recommendations, start=1):
                            output_lines.append(f"    {idx}. {rec}")
                else:
                    for message in result.messages:
                        output_lines.append(f"  {message}")
                
                all_output_lines.extend(output_lines)
                all_output_lines.append("")
                layer_results.append({
                    "layer": "layer3",
                    "label": "Layer 3: LLM as Judge",
                    "status": "completed",
                    "output": "\n".join(output_lines),
                    "output_lines": output_lines,
                    "verdict": result.verdict if result.status == "success" else None,
                    "confidence": result.confidence if result.status == "success" else None
                })
            except Exception as e:
                error_msg = f"Layer 3 failed: {str(e)}"
                all_output_lines.append(error_msg)
                layer_results.append({
                    "layer": "layer3",
                    "label": "Layer 3: LLM as Judge",
                    "status": "error",
                    "output": error_msg,
                    "error": str(e)
                })
        else:
            layer_results.append({
                "layer": "layer3",
                "label": "Layer 3: LLM as Judge",
                "status": "skipped",
                "output": "Layer 3: LLM as Judge not selected."
            })
        
        # Layer 4: Variable Impact Analysis
        if 'layer4' in selected_layer_keys:
            try:
                error_summary = analysis_data.get('error_message', 'Unknown error') or 'Unknown error'
                layer4_lines, layer4_results = code_testing_engine.run_variable_impact_analysis(
                    selected_code_patches,
                    code_dir,
                    error_summary=error_summary,
                )
                
                # Format Layer 4 output with structured results (matching PyQt format)
                formatted_layer4_lines = []
                formatted_layer4_lines.append("Layer 4: Variable Impact Analysis")
                
                for result in layer4_results:
                    patch_label = result.get("patch_label") or result.get("function_name") or "Unknown"
                    formatted_layer4_lines.append(f"{patch_label}")
                    
                    verdict = result.get("verdict") or "UNKNOWN"
                    confidence = result.get("confidence")
                    if verdict and verdict != "UNKNOWN":
                        verdict_icon = {"PASS": "✅", "NEEDS_REVIEW": "⚠️", "FAIL": "❌"}.get(verdict.upper(), "ℹ️")
                        verdict_line = f"Verdict: {verdict.replace('_', ' ').title()}"
                        if confidence is not None:
                            verdict_line += f" (confidence {confidence:.2f})"
                        formatted_layer4_lines.append(f"{verdict_icon} {verdict_line}")
                    
                    summary = result.get("summary")
                    if summary:
                        formatted_layer4_lines.append(f"Summary: {summary}")
                    
                    per_variable = result.get("per_variable") or result.get("analysis_variables") or []
                    if per_variable:
                        formatted_layer4_lines.append("Variables:")
                        for variable in per_variable:
                            name = variable.get("name") or variable.get("variable") or "<unknown>"
                            assessment = variable.get("assessment") or variable.get("change_summary") or variable.get("description", "")
                            notes = variable.get("notes") or variable.get("rationale") or ""
                            risk = variable.get("risk_level") or variable.get("scope") or "N/A"
                            formatted_layer4_lines.append(f"  {name} ({risk})")
                            if assessment:
                                # Wrap assessment if multi-line
                                for line in assessment.split('\n'):
                                    formatted_layer4_lines.append(f"    {line}")
                            if notes:
                                for line in notes.split('\n'):
                                    formatted_layer4_lines.append(f"    {line}")
                    
                    issues = result.get("issues") or []
                    if issues:
                        formatted_layer4_lines.append("Issues:")
                        for issue in issues:
                            desc = issue.get("description") or issue.get("message") or ""
                            severity = issue.get("severity") or "UNKNOWN"
                            formatted_layer4_lines.append(f"  {severity}: {desc}")
                    
                    recommendations = result.get("recommendations") or []
                    if recommendations:
                        formatted_layer4_lines.append("Recommendations:")
                        for rec in recommendations:
                            formatted_layer4_lines.append(f"  {rec}")
                    
                    messages = result.get("messages") or []
                    if messages:
                        formatted_layer4_lines.append("Notes:")
                        for message in messages:
                            formatted_layer4_lines.append(f"  {message}")
                
                # If no structured results, use plain lines
                if not layer4_results:
                    formatted_layer4_lines = layer4_lines
                
                all_output_lines.extend(formatted_layer4_lines)
                all_output_lines.append("")
                layer_results.append({
                    "layer": "layer4",
                    "label": "Layer 4: Variable Impact Analysis",
                    "status": "completed",
                    "output": "\n".join(formatted_layer4_lines),
                    "output_lines": formatted_layer4_lines,
                    "results": layer4_results
                })
            except Exception as e:
                error_msg = f"Layer 4 failed: {str(e)}"
                all_output_lines.append(error_msg)
                layer_results.append({
                    "layer": "layer4",
                    "label": "Layer 4: Variable Impact Analysis",
                    "status": "error",
                    "output": error_msg,
                    "error": str(e)
                })
        else:
            layer_results.append({
                "layer": "layer4",
                "label": "Layer 4: Variable Impact Analysis",
                "status": "skipped",
                "output": "Layer 4: Variable Impact Analysis not selected."
            })
        
        # Combine all output
        full_output = "\n".join(all_output_lines)
        
        return {
            "success": True,
            "message": "Code evaluation tests completed",
            "output": full_output,
            "output_lines": all_output_lines,
            "layer_results": layer_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error running code evaluation tests: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to run code evaluation tests: {str(e)}")
