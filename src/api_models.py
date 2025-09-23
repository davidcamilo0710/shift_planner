#!/usr/bin/env python3
"""
API Data Models for Web-based Shift Optimizer
"""

from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import date
from enum import Enum

class EmployeeType(str, Enum):
    FIJO = "FIJO"
    COMODIN = "COMODIN"

class OptimizationStrategy(str, Enum):
    LEXICOGRAPHIC = "lexicographic"
    WEIGHTED = "weighted"

class SundayStrategy(str, Enum):
    SMART = "smart"
    BALANCED = "balanced"
    COST_FOCUSED = "cost_focused"

# === CONFIGURATION MODELS ===

class GlobalConfig(BaseModel):
    """Global optimization configuration"""
    year: int = 2025
    month: int = 8
    hours_per_week: float = 48.0
    hours_base_month: float = 192.0
    shift_length_hours: int = 12
    sunday_threshold: int = 2
    min_fixed_per_post: int = 3
    max_posts_per_comodin: int = 5
    he_pct: float = 25.0  # Overtime percentage
    rf_pct: float = 75.0  # Holiday percentage  
    rn_pct: float = 35.0  # Night percentage
    w_he: float = 1000.0  # HE weight
    w_rf: float = 800.0   # RF weight
    w_rn: float = 600.0   # RN weight
    w_base: float = 1.0   # Base salary weight
    use_lexicographic: bool = True

class HolidayConfig(BaseModel):
    """Holiday configuration"""
    date: str  # YYYY-MM-DD format
    name: str = "Holiday"

class PostConfig(BaseModel):
    """Simplified post configuration"""
    post_id: str
    fixed_employees_count: int  # Number of FIJO employees for this post
    employee_salaries: List[float]  # Salaries for each FIJO employee

class EmployeeConfig(BaseModel):
    """Individual employee configuration"""
    emp_id: str
    tipo: EmployeeType
    asignado_post_id: Optional[str] = None  # None for COMODINES
    salario_contrato: float

class OptimizationConfig(BaseModel):
    """Complete optimization configuration"""
    global_config: GlobalConfig
    holidays: List[HolidayConfig] = []
    posts_count: int = 5
    posts_config: List[PostConfig] = []  # Detailed config per post
    comodines_count: int = 2
    comodines_salaries: List[float] = []  # Salaries for COMODINES
    
    # Alternative simplified configuration
    use_simple_config: bool = False
    simple_posts: Dict[str, int] = {}  # post_id -> employee_count

# === REQUEST/RESPONSE MODELS ===

class OptimizationRequest(BaseModel):
    """Request to run optimization"""
    config: OptimizationConfig
    strategy: OptimizationStrategy = OptimizationStrategy.LEXICOGRAPHIC
    sunday_strategy: SundayStrategy = SundayStrategy.SMART
    seed: int = 42

class EmployeeMetrics(BaseModel):
    """Metrics for individual employee"""
    emp_id: str
    empresa: str = "SERVAGRO"
    cargo: str = "VIGILANTE"
    cliente: str = "CLIENT"
    salario_contrato: float
    sueldo_hora: float
    hours_assigned: int
    hours_to_work: float
    hours_night: float
    hours_holiday: float
    hours_sunday: float
    num_sundays: int
    he_hours: float
    rf_hours_applied: float
    val_rn: float
    val_rf: float
    val_he: float
    salary_base: float
    total_employee: float

class PostMetrics(BaseModel):
    """Metrics for individual post"""
    post_id: str
    nombre: str
    total_shifts: int
    total_cost: float

class TotalMetrics(BaseModel):
    """Overall metrics"""
    total_empleados_activos: int
    fijos_activos: int
    comodines_activos: int
    total_he_hours: float
    total_rf_hours: float
    total_rn_hours: float
    total_val_he: float
    total_val_rf: float
    total_val_rn: float
    total_salary_base: float
    total_cost: float
    cost_per_post: float
    employees_with_excess_sundays: int

class OptimizationResponse(BaseModel):
    """Response from optimization"""
    success: bool
    message: str = ""
    solver_status: str = ""
    solve_time: float = 0.0
    
    # Results (if successful)
    assignments: Dict[str, str] = {}  # shift_id -> emp_id
    active_employees: List[str] = []
    employee_metrics: Dict[str, EmployeeMetrics] = {}
    post_metrics: Dict[str, PostMetrics] = {}
    total_metrics: Optional[TotalMetrics] = None
    
    # Additional info
    total_shifts: int = 0
    optimization_strategy: str = ""
    sunday_strategy: str = ""
    random_seed: int = 42

class ValidationResponse(BaseModel):
    """Response for configuration validation"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    
    # Summary info
    total_posts: int = 0
    total_fijos: int = 0
    total_comodines: int = 0
    estimated_shifts: int = 0

class QuickConfigRequest(BaseModel):
    """Quick configuration for simple setups"""
    posts_count: int = 5
    employees_per_post: int = 3  # FIJO employees per post
    comodines_count: int = 2
    base_salary: float = 1400000.0  # Base salary for all employees
    salary_variation: float = 0.1   # +/- percentage variation
    
    # Global settings
    year: int = 2025
    month: int = 8
    holidays: List[str] = []  # List of dates YYYY-MM-DD

class QuickConfigResponse(BaseModel):
    """Response with generated configuration"""
    config: OptimizationConfig
    summary: str
    employee_count: int
    post_count: int