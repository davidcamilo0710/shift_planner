#!/usr/bin/env python3
"""
Web Configuration Service
Converts web configuration to internal config format
"""

import random
from datetime import date, datetime, time, timedelta
from typing import List, Dict
from dataclasses import dataclass
import calendar

from .api_models import OptimizationConfig, QuickConfigRequest, EmployeeType
from .config_loader import Config, GlobalConfig, Employee, Post, Holiday

class WebConfigService:
    """Service to convert web configuration to internal format"""
    
    @staticmethod
    def convert_web_config_to_internal(web_config: OptimizationConfig) -> Config:
        """Convert web configuration to internal Config object"""
        
        # Parse shift start time for rotation calculations
        shift_start_str = web_config.global_config.shift_start_time
        shift_start_time = datetime.strptime(shift_start_str, '%H:%M').time()
        
        # Parse day/night start times for surcharge calculations (separate concept)
        day_start_str = web_config.global_config.day_start
        night_start_str = web_config.global_config.night_start
        day_start = datetime.strptime(day_start_str, '%H:%M').time()
        night_start = datetime.strptime(night_start_str, '%H:%M').time()
        
        # Convert global config
        global_config = GlobalConfig(
            year=web_config.global_config.year,
            month=web_config.global_config.month,
            hours_per_week=web_config.global_config.hours_per_week,
            hours_base_month=web_config.global_config.hours_base_month,
            shift_length_hours=web_config.global_config.shift_length_hours,
            shift_start_time=shift_start_time,
            day_start=day_start,
            night_start=night_start,
            sunday_threshold=web_config.global_config.sunday_threshold,
            min_fixed_per_post=web_config.global_config.min_fixed_per_post,
            max_posts_per_comodin=web_config.global_config.max_posts_per_comodin,
            he_pct=web_config.global_config.he_pct,
            rf_pct=web_config.global_config.rf_pct,
            rn_pct=web_config.global_config.rn_pct,
            w_he=web_config.global_config.w_he,
            w_rf=web_config.global_config.w_rf,
            w_rn=web_config.global_config.w_rn,
            w_base=web_config.global_config.w_base,
            use_lexicographic=web_config.global_config.use_lexicographic,
            min_rest_hours=0.0  # Default value
        )
        
        # Convert holidays
        holidays = []
        for holiday_config in web_config.holidays:
            holiday_date = datetime.strptime(holiday_config.date, '%Y-%m-%d').date()
            holidays.append(Holiday(
                date=holiday_date,
                description=holiday_config.name
            ))
        
        # Convert posts and employees
        posts = []
        employees = []
        
        if web_config.use_simple_config and web_config.simple_posts:
            # Simple configuration: just post_id -> employee_count
            posts, employees = WebConfigService._create_simple_config(
                web_config.simple_posts, 
                web_config.comodines_count,
                web_config.comodines_salaries,
                web_config.global_config.year,
                web_config.global_config.month
            )
        else:
            # Detailed configuration
            posts, employees = WebConfigService._create_detailed_config(
                web_config.posts_config,
                web_config.comodines_count,
                web_config.comodines_salaries,
                web_config.global_config.year,
                web_config.global_config.month
            )
        
        return Config(
            global_config=global_config,
            posts=posts,
            employees=employees,
            holidays=holidays
        )
    
    @staticmethod
    def _create_simple_config(simple_posts: Dict[str, int], comodines_count: int, 
                             comodines_salaries: List[float],
                             year: int, month: int) -> tuple[List[Post], List[Employee]]:
        """Create posts and employees from simple configuration"""
        
        posts = []
        employees = []
        
        # Create posts
        for post_id, employee_count in simple_posts.items():
            post = Post(
                post_id=post_id,
                nombre=f"Puesto {post_id}",
                required_coverage=1,
                allow_day_shift=True,
                allow_night_shift=True
            )
            posts.append(post)
            
            # Create FIJO employees for this post
            for i in range(employee_count):
                emp_id = f"{post_id}_E{i+1:03d}"
                salary = 1400000.0  # Default salary
                
                employee = Employee(
                    emp_id=emp_id,
                    empresa="SERVAGRO",
                    cargo="VIGILANTE",
                    cliente="CLIENT",
                    tipo="FIJO",
                    asignado_post_id=post_id,
                    salario_contrato=salary,
                    max_posts_if_comodin=0
                )
                employees.append(employee)
        
        # Create COMODIN employees
        for i in range(comodines_count):
            emp_id = f"C{i+1:03d}"
            salary = comodines_salaries[i] if i < len(comodines_salaries) else 1400000.0
            
            employee = Employee(
                emp_id=emp_id,
                tipo="COMODIN",
                asignado_post_id=None,
                empresa="SERVAGRO",
                cargo="VIGILANTE",
                cliente="CLIENT",
                salario_contrato=salary,
                disponible_desde=date(year, month, 1),
                disponible_hasta=date(year, month, calendar.monthrange(year, month)[1]),
                max_posts_if_comodin=5
            )
            employees.append(employee)
        
        return posts, employees
    
    @staticmethod
    def _create_detailed_config(posts_config: List, comodines_count: int,
                               comodines_salaries: List[float],
                               year: int, month: int) -> tuple[List[Post], List[Employee]]:
        """Create posts and employees from detailed configuration"""
        
        posts = []
        employees = []
        
        # Create posts and their FIJO employees
        for post_config in posts_config:
            post = Post(
                post_id=post_config.post_id,
                nombre=f"Puesto {post_config.post_id}",
                required_coverage=1,
                allow_day_shift=True,
                allow_night_shift=True
            )
            posts.append(post)
            
            # Create FIJO employees for this post
            for i in range(post_config.fixed_employees_count):
                emp_id = f"{post_config.post_id}_E{i+1:03d}"
                salary = (post_config.employee_salaries[i] 
                         if i < len(post_config.employee_salaries) 
                         else 1400000.0)
                
                employee = Employee(
                    emp_id=emp_id,
                    tipo="FIJO",
                    asignado_post_id=post_config.post_id,
                    empresa="SERVAGRO",
                    cargo="VIGILANTE",
                    cliente="CLIENT",
                    salario_contrato=salary,
                    disponible_desde=date(year, month, 1),
                    disponible_hasta=date(year, month, calendar.monthrange(year, month)[1]),
                    max_posts_if_comodin=0
                )
                employees.append(employee)
        
        # Create COMODIN employees
        for i in range(comodines_count):
            emp_id = f"C{i+1:03d}"
            salary = comodines_salaries[i] if i < len(comodines_salaries) else 1400000.0
            
            employee = Employee(
                emp_id=emp_id,
                tipo="COMODIN",
                asignado_post_id=None,
                empresa="SERVAGRO",
                cargo="VIGILANTE",
                cliente="CLIENT",
                salario_contrato=salary,
                disponible_desde=date(year, month, 1),
                disponible_hasta=date(year, month, calendar.monthrange(year, month)[1]),
                max_posts_if_comodin=5
            )
            employees.append(employee)
        
        return posts, employees
    
    @staticmethod
    def generate_quick_config(quick_request: QuickConfigRequest) -> OptimizationConfig:
        """Generate a complete configuration from quick parameters"""
        
        # Generate base salary with variation
        base_salary = quick_request.base_salary
        variation = quick_request.salary_variation
        
        posts_config = []
        
        # Create posts configuration
        for i in range(1, quick_request.posts_count + 1):
            post_id = f"P{i:03d}"
            
            # Generate salaries with variation
            employee_salaries = []
            for j in range(quick_request.employees_per_post):
                # Add random variation to base salary
                salary_variation = random.uniform(-variation, variation)
                salary = base_salary * (1 + salary_variation)
                employee_salaries.append(round(salary, 2))
            
            post_config = {
                'post_id': post_id,
                'fixed_employees_count': quick_request.employees_per_post,
                'employee_salaries': employee_salaries
            }
            posts_config.append(post_config)
        
        # Generate COMODIN salaries
        comodines_salaries = []
        for i in range(quick_request.comodines_count):
            salary_variation = random.uniform(-variation, variation)
            salary = base_salary * (1 + salary_variation)
            comodines_salaries.append(round(salary, 2))
        
        # Convert holidays from strings to HolidayConfig
        holidays = []
        for holiday_date in quick_request.holidays:
            holidays.append({
                'date': holiday_date,
                'name': 'Holiday'
            })
        
        # Create complete configuration
        from .api_models import GlobalConfig as APIGlobalConfig, PostConfig
        
        global_config = APIGlobalConfig(
            year=quick_request.year,
            month=quick_request.month,
            shift_length_hours=quick_request.shift_length_hours,
            shift_start_time=quick_request.shift_start_time,
            day_start=quick_request.day_start,
            night_start=quick_request.night_start
        )
        
        # Convert to PostConfig objects  
        from .api_models import PostConfig, HolidayConfig
        
        detailed_posts_config = []
        for post in posts_config:
            detailed_posts_config.append(PostConfig(
                post_id=post['post_id'],
                fixed_employees_count=post['fixed_employees_count'],
                employee_salaries=post['employee_salaries']
            ))
        
        # Convert holidays properly
        holiday_configs = []
        for h in holidays:
            holiday_configs.append(HolidayConfig(date=h['date'], name=h['name']))
        
        config = OptimizationConfig(
            global_config=global_config,
            holidays=holiday_configs,
            posts_count=quick_request.posts_count,
            posts_config=detailed_posts_config,
            comodines_count=quick_request.comodines_count,
            comodines_salaries=comodines_salaries,
            use_simple_config=False
        )
        
        return config
    
    @staticmethod
    def validate_web_config(web_config: OptimizationConfig) -> tuple[bool, List[str], List[str]]:
        """Validate web configuration and return errors/warnings"""
        
        errors = []
        warnings = []
        
        # Validate global config
        if web_config.global_config.year < 2020 or web_config.global_config.year > 2030:
            errors.append("Year must be between 2020 and 2030")
        
        if web_config.global_config.month < 1 or web_config.global_config.month > 12:
            errors.append("Month must be between 1 and 12")
        
        # Validate posts
        if web_config.posts_count < 1:
            errors.append("Must have at least 1 post")
        
        if web_config.posts_count > 20:
            warnings.append("More than 20 posts may affect performance")
        
        # Validate employees
        total_fijos = 0
        if web_config.posts_config:
            for post_config in web_config.posts_config:
                if post_config.fixed_employees_count < 1:
                    errors.append(f"Post {post_config.post_id} must have at least 1 FIJO employee")
                
                if post_config.fixed_employees_count > 10:
                    warnings.append(f"Post {post_config.post_id} has many employees ({post_config.fixed_employees_count})")
                
                total_fijos += post_config.fixed_employees_count
                
                # Validate salaries
                if len(post_config.employee_salaries) != post_config.fixed_employees_count:
                    errors.append(f"Post {post_config.post_id}: salary count doesn't match employee count")
                
                for salary in post_config.employee_salaries:
                    if salary < 500000:
                        errors.append(f"Salary {salary} is too low (minimum 500,000)")
                    if salary > 10000000:
                        warnings.append(f"Salary {salary} is very high")
        
        # Validate COMODINES
        if web_config.comodines_count < 0:
            errors.append("COMODINES count cannot be negative")
        
        if web_config.comodines_count > 10:
            warnings.append(f"Many COMODINES ({web_config.comodines_count}) may complicate optimization")
        
        if len(web_config.comodines_salaries) != web_config.comodines_count:
            if web_config.comodines_count > 0:
                warnings.append("COMODIN salary count doesn't match COMODIN count, will use defaults")
        
        # Overall validation
        total_employees = total_fijos + web_config.comodines_count
        if total_employees < web_config.posts_count:
            errors.append(f"Not enough employees ({total_employees}) to cover all posts ({web_config.posts_count})")
        
        if total_employees > 100:
            warnings.append("Large number of employees may affect optimization performance")
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings