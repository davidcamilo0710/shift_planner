#!/usr/bin/env python3
"""
Super explicit app entry point for DigitalOcean
This avoids any import path issues
"""

import os
import sys
from pathlib import Path

# Ensure we can import everything
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / 'src'))

print(f"🔧 Python path: {sys.path[:3]}...")
print(f"📁 Current directory: {current_dir}")

# Now import the FastAPI app
try:
    from main import app
    print("✅ Successfully imported FastAPI app")
except ImportError as e:
    print(f"❌ Import error: {e}")
    raise

# Export for gunicorn
application = app

def start_server():
    """Start the server explicitly"""
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting server on 0.0.0.0:{port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    start_server()