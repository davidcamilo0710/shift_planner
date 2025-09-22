"""
Solution verification module for the shift scheduler.

This module provides functions to verify that the generated solution
is valid and meets all business constraints.
"""

from typing import List, Dict, Tuple, Set
from datetime import datetime, timedelta, date
import logging

try:
    from .config_loader import Config, Employee, Post
    from .shift_generator import Shift, shifts_conflict
    from .optimizer import Solution
except ImportError:
    from config_loader import Config, Employee, Post
    from shift_generator import Shift, shifts_conflict
    from optimizer import Solution


logger = logging.getLogger(__name__)


class VerificationResult:
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.metrics = {}
    
    def add_error(self, message: str):
        self.errors.append(message)
        self.is_valid = False
        logger.error(f"VERIFICATION ERROR: {message}")
    
    def add_warning(self, message: str):
        self.warnings.append(message)
        logger.warning(f"VERIFICATION WARNING: {message}")
    
    def add_metric(self, key: str, value):
        self.metrics[key] = value


def verify_solution(solution: Solution, config: Config, shifts: List[Shift]) -> VerificationResult:
    """
    Comprehensive verification of the solution.
    
    Checks:
    1. Coverage constraints
    2. Employee constraints (fixed/comodin rules)
    3. Rest period violations
    4. Shift conflicts
    5. Calculation accuracy
    """
    
    result = VerificationResult()
    
    # Create lookup dictionaries
    employees = {emp.emp_id: emp for emp in config.employees}
    posts = {post.post_id: post for post in config.posts}
    shifts_by_id = {shift.shift_id: shift for shift in shifts}
    
    # Group shifts by employee
    employee_shifts = {}
    for shift_id, emp_id in solution.assignments.items():
        if emp_id not in employee_shifts:
            employee_shifts[emp_id] = []
        employee_shifts[emp_id].append(shifts_by_id[shift_id])
    
    # 1. Verify coverage constraints
    _verify_coverage_constraints(result, solution, shifts, posts)
    
    # 2. Verify employee assignment rules
    _verify_employee_constraints(result, solution, shifts_by_id, employees)
    
    # 3. Verify rest period constraints
    _verify_rest_constraints(result, employee_shifts, config)
    
    # 4. Verify no overlapping shifts
    _verify_no_overlaps(result, employee_shifts)
    
    # 5. Verify comodin post limits
    _verify_comodin_limits(result, solution, shifts_by_id, employees, config)
    
    # 6. Verify minimum fixed employees per post
    _verify_minimum_fixed_per_post(result, solution, shifts_by_id, employees, posts, config)
    
    # 7. Verify calculation accuracy
    _verify_calculation_accuracy(result, solution, config, employees, shifts_by_id)
    
    # Add summary metrics
    result.add_metric("total_assignments", len(solution.assignments))
    result.add_metric("active_employees", len(solution.active_employees))
    result.add_metric("total_errors", len(result.errors))
    result.add_metric("total_warnings", len(result.warnings))
    
    if result.is_valid:
        logger.info("Solution verification PASSED")
    else:
        logger.error(f"Solution verification FAILED with {len(result.errors)} errors")
    
    return result


def _verify_coverage_constraints(result: VerificationResult, solution: Solution, 
                                shifts: List[Shift], posts: Dict[str, Post]):
    """Verify that all shifts have the required coverage."""
    
    shifts_by_post = {}
    for shift in shifts:
        if shift.post_id not in shifts_by_post:
            shifts_by_post[shift.post_id] = []
        shifts_by_post[shift.post_id].append(shift)
    
    uncovered_shifts = 0
    
    for post_id, post_shifts in shifts_by_post.items():
        required_coverage = posts[post_id].required_coverage
        
        for shift in post_shifts:
            # Count assignments for this shift
            assigned_count = 0
            if shift.shift_id in solution.assignments:
                assigned_count = 1
            
            if assigned_count != required_coverage:
                result.add_error(
                    f"Shift {shift.shift_id} has {assigned_count} assignments, "
                    f"requires {required_coverage}"
                )
                uncovered_shifts += 1
    
    result.add_metric("uncovered_shifts", uncovered_shifts)


def _verify_employee_constraints(result: VerificationResult, solution: Solution,
                                shifts_by_id: Dict[str, Shift], employees: Dict[str, Employee]):
    """Verify employee assignment rules (fixed employees, comodins)."""
    
    for shift_id, emp_id in solution.assignments.items():
        emp = employees.get(emp_id)
        shift = shifts_by_id[shift_id]
        
        if not emp:
            result.add_error(f"Unknown employee {emp_id} assigned to shift {shift_id}")
            continue
        
        # Check fixed employee constraints
        if emp.tipo == "FIJO":
            if shift.post_id != emp.asignado_post_id:
                result.add_error(
                    f"Fixed employee {emp_id} assigned to post {shift.post_id}, "
                    f"should be {emp.asignado_post_id}"
                )
        
        # Check employee availability (basic check)
        if shift.date < emp.disponible_desde or shift.date > emp.disponible_hasta:
            result.add_error(
                f"Employee {emp_id} assigned to shift {shift_id} outside availability window"
            )


def _verify_rest_constraints(result: VerificationResult, employee_shifts: Dict[str, List[Shift]], 
                           config: Config):
    """Verify minimum rest period between shifts."""
    
    min_rest_hours = config.global_config.min_rest_hours
    violations = 0
    
    for emp_id, shifts in employee_shifts.items():
        if len(shifts) < 2:
            continue
        
        # Sort shifts by start time
        sorted_shifts = sorted(shifts, key=lambda s: datetime.combine(s.date, s.start_time))
        
        for i in range(len(sorted_shifts) - 1):
            shift1 = sorted_shifts[i]
            shift2 = sorted_shifts[i + 1]
            
            # Calculate end time of first shift
            end1 = datetime.combine(shift1.date, shift1.start_time) + timedelta(hours=shift1.duration_hours)
            start2 = datetime.combine(shift2.date, shift2.start_time)
            
            # Check rest period
            rest_hours = (start2 - end1).total_seconds() / 3600
            
            if rest_hours < min_rest_hours:
                result.add_error(
                    f"Employee {emp_id}: Rest period between shifts {shift1.shift_id} and "
                    f"{shift2.shift_id} is {rest_hours:.1f}h, minimum required {min_rest_hours}h"
                )
                violations += 1
    
    result.add_metric("rest_violations", violations)


def _verify_no_overlaps(result: VerificationResult, employee_shifts: Dict[str, List[Shift]]):
    """Verify that no employee has overlapping shifts."""
    
    overlaps = 0
    
    for emp_id, shifts in employee_shifts.items():
        if len(shifts) < 2:
            continue
        
        for i, shift1 in enumerate(shifts):
            for j, shift2 in enumerate(shifts[i+1:], i+1):
                # Check for time overlap
                start1 = datetime.combine(shift1.date, shift1.start_time)
                end1 = start1 + timedelta(hours=shift1.duration_hours)
                start2 = datetime.combine(shift2.date, shift2.start_time)
                end2 = start2 + timedelta(hours=shift2.duration_hours)
                
                # Shifts overlap if not (end1 <= start2 or end2 <= start1)
                if not (end1 <= start2 or end2 <= start1):
                    result.add_error(
                        f"Employee {emp_id}: Overlapping shifts {shift1.shift_id} and {shift2.shift_id}"
                    )
                    overlaps += 1
    
    result.add_metric("overlapping_shifts", overlaps)


def _verify_comodin_limits(result: VerificationResult, solution: Solution,
                          shifts_by_id: Dict[str, Shift], employees: Dict[str, Employee], 
                          config: Config):
    """Verify comodin post assignment limits."""
    
    max_posts_global = config.global_config.max_posts_per_comodin
    
    for emp_id in solution.active_employees:
        emp = employees[emp_id]
        if emp.tipo != "COMODIN":
            continue
        
        # Count unique posts for this comodin
        posts_used = set()
        for shift_id, assigned_emp in solution.assignments.items():
            if assigned_emp == emp_id:
                shift = shifts_by_id[shift_id]
                posts_used.add(shift.post_id)
        
        # Check limit
        max_posts_emp = min(emp.max_posts_if_comodin, max_posts_global)
        if len(posts_used) > max_posts_emp:
            result.add_error(
                f"Comodin {emp_id} assigned to {len(posts_used)} posts, "
                f"maximum allowed {max_posts_emp}"
            )


def _verify_minimum_fixed_per_post(result: VerificationResult, solution: Solution,
                                  shifts_by_id: Dict[str, Shift], employees: Dict[str, Employee],
                                  posts: Dict[str, Post], config: Config):
    """Verify minimum fixed employees per post."""
    
    min_fixed = config.global_config.min_fixed_per_post
    
    for post_id in posts:
        # Count active fixed employees for this post
        fixed_count = 0
        for emp_id in solution.active_employees:
            emp = employees[emp_id]
            if emp.tipo == "FIJO" and emp.asignado_post_id == post_id:
                fixed_count += 1
        
        if fixed_count < min_fixed:
            result.add_warning(
                f"Post {post_id} has {fixed_count} active fixed employees, "
                f"minimum recommended {min_fixed}"
            )


def _verify_calculation_accuracy(result: VerificationResult, solution: Solution, 
                               config: Config, employees: Dict[str, Employee],
                               shifts_by_id: Dict[str, Shift]):
    """Verify calculation accuracy by recalculating metrics independently."""
    
    tolerance = 0.01  # Tolerance for floating-point comparisons
    
    for emp_id, metrics in solution.employee_metrics.items():
        if emp_id not in solution.active_employees:
            continue
        
        emp = employees[emp_id]
        
        # Recalculate hours
        assigned_shifts = [
            shifts_by_id[shift_id] for shift_id, assigned_emp 
            in solution.assignments.items() if assigned_emp == emp_id
        ]
        
        calc_hours_assigned = sum(shift.duration_hours for shift in assigned_shifts)
        calc_hours_night = sum(
            shift.duration_hours for shift in assigned_shifts if shift.is_night
        )
        calc_hours_holiday = sum(
            shift.duration_hours for shift in assigned_shifts if shift.is_holiday
        )
        calc_hours_sunday = sum(
            shift.duration_hours for shift in assigned_shifts if shift.is_sunday
        )
        
        # Count sundays worked (actual Sunday calendar dates that the employee worked)
        # This should match the optimizer's logic which only tracks actual Sunday dates
        sunday_dates_worked = set()
        for shift in assigned_shifts:
            # Only count if shift starts on an actual Sunday date
            if shift.date.weekday() == 6:  # Sunday
                sunday_dates_worked.add(shift.date)
        
        calc_num_sundays = len(sunday_dates_worked)
        
        # Verify hours calculations
        if abs(calc_hours_assigned - metrics['hours_assigned']) > tolerance:
            result.add_error(
                f"Employee {emp_id}: Hours assigned mismatch - "
                f"calculated {calc_hours_assigned}, reported {metrics['hours_assigned']}"
            )
        
        if abs(calc_hours_night - metrics['hours_night']) > tolerance:
            result.add_error(
                f"Employee {emp_id}: Night hours mismatch - "
                f"calculated {calc_hours_night}, reported {metrics['hours_night']}"
            )
        
        if calc_num_sundays != metrics['num_sundays']:
            result.add_error(
                f"Employee {emp_id}: Sunday count mismatch - "
                f"calculated {calc_num_sundays}, reported {metrics['num_sundays']}"
            )
        
        # Verify overtime calculation
        hours_to_work = (config.global_config.hours_per_week / 7) * 31  # Approximate
        calc_he_hours = max(0, calc_hours_assigned - hours_to_work)
        
        if abs(calc_he_hours - metrics['he_hours']) > 1.0:  # Allow some tolerance for date calculations
            result.add_warning(
                f"Employee {emp_id}: Overtime hours potential mismatch - "
                f"calculated ~{calc_he_hours:.1f}, reported {metrics['he_hours']}"
            )


def print_verification_report(result: VerificationResult):
    """Print a formatted verification report."""
    
    print("\n" + "="*50)
    print("SOLUTION VERIFICATION REPORT")
    print("="*50)
    
    print(f"Overall Status: {'PASSED' if result.is_valid else 'FAILED'}")
    print(f"Total Assignments: {result.metrics.get('total_assignments', 'N/A')}")
    print(f"Active Employees: {result.metrics.get('active_employees', 'N/A')}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for error in result.errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(result.errors) > 10:
            print(f"  ... and {len(result.errors) - 10} more errors")
    
    if result.warnings:
        print(f"\nWARNINGS ({len(result.warnings)}):")
        for warning in result.warnings[:5]:  # Show first 5 warnings
            print(f"  - {warning}")
        if len(result.warnings) > 5:
            print(f"  ... and {len(result.warnings) - 5} more warnings")
    
    print("\nMETRICS:")
    for key, value in result.metrics.items():
        print(f"  {key}: {value}")
    
    print("="*50)