#!/usr/bin/env python3
"""
Server entry point for DigitalOcean App Platform
Following the official DO Python sample pattern
"""

import os
import sys
from pathlib import Path

# Ensure imports work
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / 'src'))

print("🚀 Starting Planificador de Turnos API")
print(f"📁 Working directory: {current_dir}")

# Import FastAPI app
from api_web import app

if __name__ == "__main__":
    import uvicorn
    
    # Use same pattern as DO sample: int(os.getenv('PORT', default))
    port = int(os.getenv('PORT', 8000))
    
    print(f"🌐 Listening on port {port}")
    
    # Start server exactly like DO example pattern
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )