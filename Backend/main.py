import os
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Load environment variables from .env file at startup (before importing endpoints)
# This ensures .env is loaded before any modules that need it
backend_dir = Path(__file__).parent
env_path = backend_dir / ".env"

if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"✅ Loaded .env file from: {env_path}")
else:
    # Try loading from current directory (default dotenv behavior)
    load_dotenv()
    print(f"ℹ️  Attempted to load .env using default behavior")

from app.api.endpoints import router

try:
    from app.guardrails import get_spec_intel_guardrail
    _guardrail_status = get_spec_intel_guardrail().status()
    print(
        f"🛡️ Spec Intel guardrails: enabled={_guardrail_status.get('enabled')}, "
        f"backend={_guardrail_status.get('backend')}, "
        f"model_loaded={_guardrail_status.get('model_loaded')}"
    )
    if _guardrail_status.get("model_error"):
        print(f"🛡️ Guardrail note: {_guardrail_status.get('model_error')} (rules-only fallback may apply)")
except Exception as _guard_err:
    print(f"⚠️ Could not initialize guardrail status: {_guard_err}")

# Configuration
HOST = "localhost"
PORT = 8000

app = FastAPI(title="RCA Backend API", version="1.0.0")

# Allow CORS for all origins (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Print all registered routes at startup for debugging
def print_routes():
    """Print all registered API routes at startup"""
    try:
        print("\n" + "="*80)
        print("📋 REGISTERED API ENDPOINTS (STARTUP)")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        routes_by_prefix = {}
        route_count = 0
        
        for route in app.routes:
            # Handle different route types (APIRoute, Mount, etc.)
            if hasattr(route, 'path'):
                path = route.path
                
                # Get methods for this route
                methods = ['GET']  # Default
                if hasattr(route, 'methods') and route.methods:
                    methods = [m for m in route.methods if m != 'HEAD']  # Exclude HEAD
                elif hasattr(route, 'endpoint') and hasattr(route.endpoint, '__name__'):
                    # Try to infer from endpoint
                    methods = ['GET']
                
                methods_str = ', '.join(sorted(methods)) if methods else 'GET'
                
                # Group by prefix
                if path.startswith('/api/'):
                    parts = path.split('/')
                    if len(parts) > 2:
                        prefix = '/api/' + parts[2]  # e.g., /api/dataset, /api/rca
                    else:
                        prefix = '/api'
                elif path == '/':
                    prefix = 'ROOT'
                elif path == '/health':
                    prefix = 'ROOT'
                else:
                    prefix = path.split('/')[1] if len(path.split('/')) > 1 else '/'
                
                if prefix not in routes_by_prefix:
                    routes_by_prefix[prefix] = []
                routes_by_prefix[prefix].append((methods_str, path))
                route_count += 1
        
        # Print grouped routes
        for prefix in sorted(routes_by_prefix.keys()):
            print(f"\n🔹 {prefix.upper() if prefix != 'ROOT' else 'ROOT'}")
            print("-" * 80)
            for methods, path in sorted(routes_by_prefix[prefix]):
                print(f"  {methods:20s} {path}")
        
        print("\n" + "="*80)
        print(f"✅ Total routes registered: {route_count}")
        print("="*80 + "\n")
    except Exception as e:
        print(f"⚠️  Could not print routes: {e}")
        import traceback
        traceback.print_exc()

# Print routes after app is created (but before startup)
# Use @app.on_event("startup") for async printing
@app.on_event("startup")
async def startup_event():
    """Print all routes when server starts"""
    print_routes()

# Also print routes immediately (synchronous, happens during import)
# This ensures routes are printed even if startup event doesn't fire
print_routes()

# For running with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True) 