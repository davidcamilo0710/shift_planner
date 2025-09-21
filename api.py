#!/usr/bin/env python3
"""
FastAPI REST API for 24/7 Shift Scheduler and Optimizer
"""

import os
import tempfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add src directory to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from processing.processor import ShiftProcessor

# Initialize FastAPI app
app = FastAPI(
    title="Planificador de Turnos API",
    description="API REST para optimización de turnos 24/7 en puestos de seguridad",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=2)

@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "message": "Planificador de Turnos API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for DigitalOcean App Platform."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "planificador-turnos"
    }

@app.post("/process")
async def process_schedule(
    config_file: UploadFile = File(..., description="Configuration Excel file"),
    strategy: str = Form(default="lexicographic", description="Optimization strategy: lexicographic or weighted"),
    log_level: str = Form(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR"),
    generate_validation: bool = Form(default=False, description="Generate detailed validation report")
):
    """
    Process shift scheduling optimization.
    
    - **config_file**: Excel configuration file (.xlsx)
    - **strategy**: Optimization strategy (lexicographic or weighted)
    - **log_level**: Logging level for debugging
    - **generate_validation**: Whether to generate validation report
    
    Returns the optimized schedule as an Excel file.
    """
    
    # Validate file type
    if not config_file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only Excel files (.xlsx, .xls) are allowed."
        )
    
    # Validate file size (50MB limit)
    if config_file.size > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 50MB."
        )
    
    # Validate strategy
    if strategy not in ["lexicographic", "weighted"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid strategy. Must be 'lexicographic' or 'weighted'."
        )
    
    # Validate log level
    if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid log level. Must be DEBUG, INFO, WARNING, or ERROR."
        )
    
    temp_config_file = None
    temp_output_file = None
    
    try:
        logger.info(f"Processing request - Strategy: {strategy}, Log Level: {log_level}, Validate: {generate_validation}")
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_config:
            temp_config_file = temp_config.name
            content = await config_file.read()
            temp_config.write(content)
        
        # Create output file
        temp_output_file = tempfile.mktemp(suffix='.xlsx')
        
        # Initialize processor
        processor = ShiftProcessor()
        
        # Run processing in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            processor.process_schedule,
            temp_config_file,
            temp_output_file,
            strategy,
            log_level,
            generate_validation
        )
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"Processing failed: {result.error_message}"
            )
        
        # Check if output file was created
        if not Path(temp_output_file).exists():
            raise HTTPException(
                status_code=500,
                detail="Output file was not created successfully."
            )
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"schedule_optimized_{timestamp}.xlsx"
        
        logger.info(f"Processing completed successfully. Returning file: {output_filename}")
        
        # Return the file
        return FileResponse(
            path=temp_output_file,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=output_filename,
            headers={
                "Content-Disposition": f"attachment; filename={output_filename}",
                "X-Processing-Time": str(result.processing_time),
                "X-Strategy-Used": result.strategy_used,
                "X-Total-Assignments": str(result.total_assignments) if result.total_assignments else "0"
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    finally:
        # Clean up temporary files
        try:
            if temp_config_file and Path(temp_config_file).exists():
                os.unlink(temp_config_file)
        except Exception as e:
            logger.warning(f"Failed to clean up temp config file: {e}")
        
        # Note: temp_output_file is cleaned up by FastAPI after sending the response

@app.get("/docs/usage")
async def api_usage_guide():
    """Get API usage instructions."""
    return {
        "title": "API Usage Guide",
        "endpoints": {
            "POST /process": {
                "description": "Main endpoint for schedule optimization",
                "parameters": {
                    "config_file": "Excel file with configuration (required)",
                    "strategy": "Optimization strategy: 'lexicographic' (default) or 'weighted'",
                    "log_level": "Logging level: DEBUG, INFO (default), WARNING, ERROR",
                    "generate_validation": "Generate validation report: true or false (default)"
                },
                "response": "Excel file with optimized schedule",
                "max_file_size": "50MB",
                "supported_formats": [".xlsx", ".xls"]
            },
            "GET /health": {
                "description": "Health check endpoint",
                "response": "Service health status"
            },
            "GET /docs": {
                "description": "Interactive API documentation"
            }
        },
        "example_curl": """
curl -X POST "http://localhost:8000/process" \\
     -F "config_file=@config/optimizer_config.xlsx" \\
     -F "strategy=lexicographic" \\
     -F "log_level=INFO" \\
     -F "generate_validation=false" \\
     -o optimized_schedule.xlsx
        """.strip()
    }

@app.exception_handler(413)
async def request_entity_too_large_handler(request, exc):
    """Handle file too large errors."""
    return JSONResponse(
        status_code=413,
        content={"detail": "File too large. Maximum size is 50MB."}
    )

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."}
    )

if __name__ == "__main__":
    # For local development
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )