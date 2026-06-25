#!/usr/bin/env python3
"""
Test script to check error fixing pipeline imports and dependencies
"""

import sys
import os
from pathlib import Path

# Add the Error_fixing_pipelin directory to the Python path
current_dir = Path(__file__).parent
error_pipeline_path = current_dir / "app" / "services" / "Error_fixing_pipelin" / "Error_fixing_pipelin"
if str(error_pipeline_path) not in sys.path:
    sys.path.append(str(error_pipeline_path))

print("🧪 Testing Error Fixing Pipeline Imports")
print("=" * 50)

# Test basic imports
print("\n1. Testing basic Python modules...")
try:
    import json
    import logging
    import os
    from datetime import datetime
    print("✅ Basic modules imported successfully")
except ImportError as e:
    print(f"❌ Basic modules failed: {e}")

# Test third-party imports
print("\n2. Testing third-party modules...")

modules_to_test = [
    ("numpy", "np"),
    ("pandas", "pd"),
    ("sklearn", "sklearn"),
    ("faiss", "faiss"),
    ("sentence_transformers", "SentenceTransformer"),
    ("openai", "AzureOpenAI"),
    ("dotenv", "load_dotenv"),
    ("networkx", "nx"),
    ("fitz", "PyMuPDF"),
    ("docx", "Document"),
    ("bs4", "BeautifulSoup"),
    ("requests", "requests")
]

missing_modules = []

for module_name, import_name in modules_to_test:
    try:
        if module_name == "numpy":
            import numpy as np
        elif module_name == "pandas":
            import pandas as pd
        elif module_name == "sklearn":
            import sklearn
        elif module_name == "faiss":
            import faiss
        elif module_name == "sentence_transformers":
            from sentence_transformers import SentenceTransformer
        elif module_name == "openai":
            from openai import AzureOpenAI
        elif module_name == "dotenv":
            from dotenv import load_dotenv
        elif module_name == "networkx":
            import networkx as nx
        elif module_name == "fitz":
            import fitz
        elif module_name == "docx":
            from docx import Document
        elif module_name == "bs4":
            from bs4 import BeautifulSoup
        elif module_name == "requests":
            import requests
        
        print(f"✅ {module_name} imported successfully")
    except ImportError as e:
        print(f"❌ {module_name} failed: {e}")
        missing_modules.append(module_name)

# Test error fixing pipeline imports
print("\n3. Testing error fixing pipeline imports...")
try:
    from complete_error_fixing_pipeline import CompleteErrorFixingPipeline
    print("✅ CompleteErrorFixingPipeline imported successfully")
except ImportError as e:
    print(f"❌ CompleteErrorFixingPipeline failed: {e}")

try:
    from error_handling_pipeline import ErrorHandlingPipeline
    print("✅ ErrorHandlingPipeline imported successfully")
except ImportError as e:
    print(f"❌ ErrorHandlingPipeline failed: {e}")

try:
    from fix_suggestion_pipeline import FixSuggestionPipeline
    print("✅ FixSuggestionPipeline imported successfully")
except ImportError as e:
    print(f"❌ FixSuggestionPipeline failed: {e}")

try:
    from ui_integration import update_embeddings_from_ui
    print("✅ ui_integration imported successfully")
except ImportError as e:
    print(f"❌ ui_integration failed: {e}")

# Summary
print("\n" + "=" * 50)
print("📊 SUMMARY")
print("=" * 50)

if missing_modules:
    print(f"\n❌ Missing modules: {', '.join(missing_modules)}")
    print("\nTo install missing modules, run:")
    print("pip install " + " ".join(missing_modules))
else:
    print("\n✅ All required modules are available!")

print(f"\n📁 Error pipeline path: {error_pipeline_path}")
print(f"📁 Path exists: {error_pipeline_path.exists()}")

if error_pipeline_path.exists():
    print("📁 Pipeline files:")
    for file in error_pipeline_path.glob("*.py"):
        print(f"   - {file.name}")
else:
    print("❌ Error pipeline path does not exist!")
