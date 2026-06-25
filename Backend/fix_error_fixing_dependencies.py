#!/usr/bin/env python3
"""
Script to fix error fixing pipeline dependencies
"""

import subprocess
import sys

def run_command(command):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("🔧 Fixing Error Fixing Pipeline Dependencies")
    print("=" * 50)
    
    # Step 1: Downgrade NumPy to fix FAISS compatibility
    print("\n1. Fixing NumPy version for FAISS compatibility...")
    success, stdout, stderr = run_command("pip install 'numpy<2.0' --force-reinstall")
    if success:
        print("✅ NumPy downgraded successfully")
    else:
        print(f"❌ Failed to downgrade NumPy: {stderr}")
    
    # Step 2: Reinstall FAISS
    print("\n2. Reinstalling FAISS...")
    success, stdout, stderr = run_command("pip uninstall faiss-cpu -y")
    success, stdout, stderr = run_command("pip install faiss-cpu")
    if success:
        print("✅ FAISS reinstalled successfully")
    else:
        print(f"❌ Failed to reinstall FAISS: {stderr}")
    
    # Step 3: Install other missing dependencies
    print("\n3. Installing other dependencies...")
    dependencies = [
        "sentence-transformers",
        "transformers", 
        "torch",
        "openai",
        "python-dotenv",
        "networkx",
        "PyMuPDF",
        "python-docx",
        "beautifulsoup4",
        "requests"
    ]
    
    for dep in dependencies:
        print(f"   Installing {dep}...")
        success, stdout, stderr = run_command(f"pip install {dep}")
        if success:
            print(f"   ✅ {dep} installed")
        else:
            print(f"   ❌ {dep} failed: {stderr}")
    
    print("\n🎉 Dependency fixing completed!")
    print("\nTo test the error fixing pipeline, run:")
    print("python test_error_fixing_imports.py")

if __name__ == "__main__":
    main()
