# RCA Electron Application - Setup and Installation Guide

This document provides step-by-step instructions to set up and run the complete RCA (Root Cause Analysis) Electron application, including both the Frontend (Electron) and Backend (FastAPI) components.

## Table of Contents
- [System Requirements](#system-requirements)
- [Prerequisites](#prerequisites)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [Running the Application](#running-the-application)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Operating System
- **Windows 10/11** (tested on Windows 10.0.26100)
- **macOS** (compatible)
- **Linux** (compatible)

### Hardware Requirements
- **RAM**: Minimum 8GB (16GB recommended for ML/AI features)
- **Storage**: At least 5GB free space
- **CPU**: Multi-core processor recommended

---

## Prerequisites

### 1. Python Installation
- **Python 3.8 or higher** (Python 3.9+ recommended)
- Download from: https://www.python.org/downloads/
- **Important**: During installation, check "Add Python to PATH"

**Verify Installation:**
```bash
python --version
# or
python3 --version
```

### 2. Node.js and npm Installation
- **Node.js 16.x or higher** (Node.js 18+ recommended)
- Download from: https://nodejs.org/
- npm comes bundled with Node.js

**Verify Installation:**
```bash
node --version
npm --version
```

### 3. Git (Optional)
- Required if cloning from repository
- Download from: https://git-scm.com/downloads

---

## Backend Setup

### Step 1: Navigate to Backend Directory
```bash
cd RCA_Electron-main/Backend
```

### Step 2: Create Python Virtual Environment
```bash
# Windows
python -m venv venv

# macOS/Linux
python3 -m venv venv
```

### Step 3: Activate Virtual Environment

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Note**: After activation, you should see `(venv)` prefix in your terminal prompt.

### Step 4: Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Backend Dependencies Include:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `python-multipart` - File upload support
- `python-docx` - Word document processing
- `networkx` - Graph analysis
- `openai` - OpenAI API client
- `python-dotenv` - Environment variable management
- `requests` - HTTP library
- `beautifulsoup4` - HTML/XML parsing
- `PyMuPDF` - PDF processing
- `paramiko` - SSH client
- `colorama` - Terminal colors
- `matplotlib` - Plotting library
- `graphviz` - Graph visualization
- `tqdm` - Progress bars
- `google-generativeai` - Google Gemini API
- `pydantic` - Data validation
- `numpy` - Numerical computing
- `pandas` - Data manipulation
- `scikit-learn` - Machine learning
- `faiss-cpu` - Vector similarity search
- `sentence-transformers` - Sentence embeddings
- `transformers` - Hugging Face transformers
- `torch` - PyTorch deep learning framework

**Note**: Installation may take 10-15 minutes due to ML/AI libraries (torch, transformers, etc.)

### Step 5: Configure Environment Variables

Create a `.env` file in the `Backend` directory:

```bash

# Windows (PowerShell)
New-Item -Path .env -ItemType File

# Windows (Command Prompt)
type nul > .env

# macOS/Linux
touch .env
```

Add the following content to `.env`:

```env
# Azure OpenAI Configuration (Required)
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint_here

# Alternative: If using AZURE_OPENAI_KEY (backward compatibility)
# AZURE_OPENAI_KEY=your_azure_openai_key_here

# Optional: Google Gemini API (if using Gemini features)
# GOOGLE_API_KEY=your_google_api_key_here
```

**Important**: Replace the placeholder values with your actual API keys.

### Step 6: Verify Backend Setup
```bash
python main.py
```

You should see:
- Server starting on `http://localhost:8000`
- Registered API endpoints listed
- Environment variables loaded successfully

**Stop the server** by pressing `Ctrl+C` in the terminal.

---

## Frontend Setup

### Step 1: Navigate to Frontend Directory
```bash
cd RCA_Electron-main/Frontend
```

### Step 2: Install Node.js Dependencies
```bash
npm install
```

**Frontend Dependencies Include:**
- `electron` (^38.2.0) - Electron framework
- `nodemon` (^3.1.11) - Development auto-reload

**Note**: This will create a `node_modules` directory with all dependencies.

### Step 3: Verify Frontend Setup
```bash
npm list electron
```

You should see Electron version 38.2.0 or similar listed.

---

## Running the Application

### Important: Run Backend First

The Frontend (Electron app) requires the Backend API to be running. Always start the Backend before the Frontend.

### Step 1: Start the Backend Server

**Terminal 1 - Backend:**

```bash
# Navigate to Backend directory
cd RCA_Electron-main/Backend

# Activate virtual environment (if not already activated)
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Windows (Command Prompt)
venv\Scripts\activate.bat
# macOS/Linux
source venv/bin/activate

# Start the server
python main.py
```

**Expected Output:**
```
✅ Loaded .env file from: [path]
✅ All required environment variables are set
📋 REGISTERED API ENDPOINTS (STARTUP)
...
INFO:     Uvicorn running on http://localhost:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

The backend server is now running on **http://localhost:8000**

### Step 2: Start the Frontend Application

**Terminal 2 - Frontend:**

```bash
# Navigate to Frontend directory
cd RCA_Electron-main/Frontend

# Start Electron app
npm start
```

**Alternative - Development Mode (with auto-reload):**
```bash
npm run dev
```

**Expected Output:**
- Electron application window should open
- Window size: 1400x900 pixels
- Application should connect to backend at `http://localhost:8000`

### Step 3: Verify Application is Running

1. **Backend**: Check terminal for "Uvicorn running on http://localhost:8000"
2. **Frontend**: Electron window should be open and functional
3. **API Connection**: Frontend should successfully communicate with backend

---

## Quick Start Summary

### Backend (Terminal 1)
```bash
cd RCA_Electron-main/Backend
.\venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt  # First time only
python main.py
```

### Frontend (Terminal 2)
```bash
cd RCA_Electron-main/Frontend
npm install  # First time only
npm start
```

---

## Troubleshooting

### Backend Issues

#### Issue: `ModuleNotFoundError` or Import Errors
**Solution:**
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Verify Python version: `python --version` (should be 3.8+)

#### Issue: `Port 8000 already in use`
**Solution:**
- Stop any other application using port 8000
- Or modify `HOST` and `PORT` in `Backend/main.py`

#### Issue: Environment Variables Not Loading
**Solution:**
- Ensure `.env` file exists in `Backend` directory
- Check file format (no spaces around `=`)
- Verify API keys are correct
- Check terminal output for environment variable loading messages

#### Issue: `torch` or ML libraries installation fails
**Solution:**
- Install PyTorch separately: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
- For GPU support, visit: https://pytorch.org/get-started/locally/

### Frontend Issues

#### Issue: `electron: command not found`
**Solution:**
- Run `npm install` in Frontend directory
- Verify Electron is installed: `npm list electron`

#### Issue: `Cannot connect to backend`
**Solution:**
- Ensure backend is running on `http://localhost:8000`
- Check backend terminal for errors
- Verify CORS settings in `Backend/main.py`
- Check firewall settings

#### Issue: `npm install` fails
**Solution:**
- Clear npm cache: `npm cache clean --force`
- Delete `node_modules` and `package-lock.json`, then reinstall
- Check Node.js version: `node --version` (should be 16+)

### General Issues

#### Issue: Application window doesn't open
**Solution:**
- Check both terminals for error messages
- Ensure backend is running before starting frontend
- Try running in development mode: `npm run dev`

#### Issue: API requests fail
**Solution:**
- Verify backend server is running
- Check API endpoint URLs in Frontend code
- Review browser DevTools console (if available)
- Check backend terminal for request logs

---

## Project Structure

```
RCA_Electron-main/
├── Backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── endpoints.py      # API route definitions
│   │   └── services/              # Business logic services
│   ├── resources/                 # Output files and resources
│   ├── main.py                    # FastAPI application entry point
│   ├── requirements.txt           # Python dependencies
│   └── .env                       # Environment variables (create this)
│
└── Frontend/
    ├── app.js                     # Main application logic
    ├── main.js                    # Electron main process
    ├── index.html                 # Application UI
    ├── api.js                     # API communication
    ├── package.json               # Node.js dependencies
    └── preload.js                 # Electron preload script
```

---

## Additional Notes

### Development Mode
- Backend: Runs with auto-reload enabled (`reload=True` in `main.py`)
- Frontend: Use `npm run dev` for auto-reload on file changes

### Production Deployment
- Backend: Consider using production ASGI server (e.g., Gunicorn with Uvicorn workers)
- Frontend: Build Electron app for distribution using Electron Builder

### API Documentation
- Once backend is running, visit: `http://localhost:8000/docs` for interactive API documentation (Swagger UI)
- Alternative: `http://localhost:8000/redoc` for ReDoc documentation

### Output Files
- All output/result files are saved in `Backend/resources/` directory
- Check this folder for generated results, logs, and analysis outputs

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review terminal error messages
3. Check application logs in `Backend/resources/log_files/`
4. Verify all prerequisites are installed correctly

---

**Last Updated**: Based on application version 1.0.0

