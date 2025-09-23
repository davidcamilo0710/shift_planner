#!/usr/bin/env python3
"""
FastAPI Web Configuration API for the shift scheduler
Modern web-based API that replaces Excel configuration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
from pathlib import Path
from datetime import datetime
import traceback
import uvicorn
import os

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.shift_generator import generate_shifts
from src.optimizer import ShiftOptimizer
from src.verifier import verify_solution
from src.api_models import *
from src.web_config_service import WebConfigService

app = FastAPI(
    title="SERVAGRO Shift Scheduler API", 
    version="2.0.0",
    description="Web-based shift optimization API with flexible configuration",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "SERVAGRO Shift Scheduler API v2.0", 
        "status": "running",
        "endpoints": {
            "health": "/health",
            "quick_config": "/config/quick",
            "validate_config": "/config/validate", 
            "optimize": "/optimize",
            "strategies": "/strategies",
            "example": "/config/example"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# === NEW WEB CONFIGURATION ENDPOINTS ===

@app.post("/config/quick", response_model=QuickConfigResponse)
async def generate_quick_config(request: QuickConfigRequest):
    """
    Generate a complete optimization configuration from simple parameters
    
    Example:
    {
        "posts_count": 5,
        "employees_per_post": 3,
        "comodines_count": 2,
        "base_salary": 1400000,
        "salary_variation": 0.1,
        "year": 2025,
        "month": 8,
        "holidays": ["2025-08-15", "2025-08-20"]
    }
    """
    try:
        config = WebConfigService.generate_quick_config(request)
        
        total_fijos = request.posts_count * request.employees_per_post
        total_employees = total_fijos + request.comodines_count
        
        summary = f"Generated config: {request.posts_count} posts, {total_fijos} FIJO employees, {request.comodines_count} COMODINES"
        
        return QuickConfigResponse(
            config=config,
            summary=summary,
            employee_count=total_employees,
            post_count=request.posts_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generating configuration: {str(e)}")

@app.post("/config/validate", response_model=ValidationResponse)  
async def validate_config(config: OptimizationConfig):
    """
    Validate optimization configuration without running optimization
    """
    try:
        is_valid, errors, warnings = WebConfigService.validate_web_config(config)
        
        # Calculate summary info
        total_fijos = sum(post.fixed_employees_count for post in config.posts_config)
        total_comodines = config.comodines_count
        
        # Estimate shifts (rough calculation)
        import calendar
        days_in_month = calendar.monthrange(config.global_config.year, config.global_config.month)[1]
        estimated_shifts = config.posts_count * 2 * days_in_month  # 2 shifts per day per post
        
        return ValidationResponse(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
            total_posts=config.posts_count,
            total_fijos=total_fijos,
            total_comodines=total_comodines,
            estimated_shifts=estimated_shifts
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")

@app.post("/optimize", response_model=OptimizationResponse)
async def optimize_with_web_config(request: OptimizationRequest):
    """
    Run shift optimization with web-based configuration
    
    Main endpoint for web interface optimization
    """
    try:
        start_time = datetime.now()
        
        # Validate configuration first
        is_valid, errors, warnings = WebConfigService.validate_web_config(request.config)
        if not is_valid:
            return OptimizationResponse(
                success=False,
                message=f"Configuration errors: {'; '.join(errors)}",
                solver_status="CONFIGURATION_ERROR"
            )
        
        # Convert web config to internal format
        internal_config = WebConfigService.convert_web_config_to_internal(request.config)
        
        # Generate shifts
        shifts = generate_shifts(internal_config)
        
        # Create optimizer and solve
        optimizer = ShiftOptimizer(internal_config, shifts)
        
        if request.strategy == OptimizationStrategy.LEXICOGRAPHIC:
            solution = optimizer.solve_lexicographic(
                sunday_strategy=request.sunday_strategy.value,
                random_seed=request.seed
            )
        else:
            solution = optimizer.solve_weighted(random_seed=request.seed)
        
        solve_time = (datetime.now() - start_time).total_seconds()
        
        if solution.solver_status not in ["OPTIMAL", "FEASIBLE"]:
            return OptimizationResponse(
                success=False,
                message=f"Optimization failed: {solution.solver_status}",
                solver_status=solution.solver_status,
                solve_time=solve_time,
                optimization_strategy=request.strategy.value,
                sunday_strategy=request.sunday_strategy.value,
                random_seed=request.seed
            )
        
        # Verify solution
        verification = verify_solution(solution, internal_config, shifts)
        
        # Convert solution to response format
        employee_metrics = {}
        for emp_id, metrics in solution.employee_metrics.items():
            employee_metrics[emp_id] = EmployeeMetrics(**metrics)
        
        post_metrics = {}
        for post_id, metrics in solution.post_metrics.items():
            post_metrics[post_id] = PostMetrics(**metrics)
        
        total_metrics = TotalMetrics(**solution.total_metrics)
        
        return OptimizationResponse(
            success=True,
            message=f"Optimization completed successfully. Verification: {'PASSED' if verification.is_valid else 'FAILED'}",
            solver_status=solution.solver_status,
            solve_time=solve_time,
            assignments=solution.assignments,
            active_employees=solution.active_employees,
            employee_metrics=employee_metrics,
            post_metrics=post_metrics,
            total_metrics=total_metrics,
            total_shifts=len(shifts),
            optimization_strategy=request.strategy.value,
            sunday_strategy=request.sunday_strategy.value,
            random_seed=request.seed
        )
        
    except Exception as e:
        error_msg = f"Optimization error: {str(e)}"
        print(f"ERROR: {error_msg}")
        traceback.print_exc()
        
        return OptimizationResponse(
            success=False,
            message=error_msg,
            solver_status="ERROR",
            solve_time=(datetime.now() - start_time).total_seconds() if 'start_time' in locals() else 0,
            optimization_strategy=request.strategy.value if 'request' in locals() else "unknown",
            sunday_strategy=request.sunday_strategy.value if 'request' in locals() else "unknown",
            random_seed=request.seed if 'request' in locals() else 42
        )

# === UTILITY ENDPOINTS ===

@app.get("/config/example")
async def get_example_config():
    """Get an example configuration for reference"""
    
    example_config = OptimizationConfig(
        global_config=GlobalConfig(),
        holidays=[
            HolidayConfig(date="2025-08-15", name="Assumption of Mary"),
            HolidayConfig(date="2025-08-07", name="Battle of Boyacá")
        ],
        posts_count=3,
        posts_config=[
            PostConfig(
                post_id="P001",
                fixed_employees_count=3,
                employee_salaries=[1400000.0, 1450000.0, 1380000.0]
            ),
            PostConfig(
                post_id="P002", 
                fixed_employees_count=3,
                employee_salaries=[1420000.0, 1470000.0, 1390000.0]
            ),
            PostConfig(
                post_id="P003",
                fixed_employees_count=3,
                employee_salaries=[1410000.0, 1460000.0, 1400000.0]
            )
        ],
        comodines_count=2,
        comodines_salaries=[1350000.0, 1370000.0]
    )
    
    return {"example_config": example_config}

@app.get("/strategies")
async def get_available_strategies():
    """Get available optimization and Sunday strategies"""
    
    return {
        "optimization_strategies": {
            "lexicographic": "Multi-level optimization (HE > RF > RN) - Recommended",
            "weighted": "Single weighted objective optimization"
        },
        "sunday_strategies": {
            "smart": "Intelligent Sunday distribution (Champion + Helper + Others + COMODIN relief)",
            "balanced": "Equal penalty for all employees having excess Sundays", 
            "cost_focused": "Direct minimization of Sunday costs"
        },
        "recommended": {
            "strategy": "lexicographic",
            "sunday_strategy": "smart"
        }
    }

if __name__ == "__main__":
    # Get port from environment (for deployment)
    port = int(os.environ.get("PORT", 8001))
    print(f"Starting SERVAGRO Shift Scheduler API v2.0 on port {port}")
    uvicorn.run(
        "api_web:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )