#!/usr/bin/env python3
"""
Explicit startup script for DigitalOcean App Platform
"""
import os
import uvicorn

if __name__ == "__main__":
    # Import the app
    from main import app
    
    # Get port from environment
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🚀 Starting Planificador de Turnos API on port {port}")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🐍 Python executable: {os.sys.executable}")
    
    # Start the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )