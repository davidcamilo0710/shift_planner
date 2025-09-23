#!/usr/bin/env python3
"""
Sunday Champion Strategy: Smart Sunday assignment optimization.
"""

from typing import List, Dict, Tuple
from datetime import date
import calendar
from ortools.sat.python import cp_model

def get_sunday_champion_constraints(model: cp_model.CpModel, config, employees: Dict, shifts: List, 
                                  x: Dict, excess_sundays: Dict, sunday_worked: Dict) -> List:
    """
    Implement Sunday Champion strategy: designate lowest-paid employee as Sunday Champion.
    """
    
    # Find the employee with the lowest salary (Sunday Champion)
    sunday_champion = min(employees.keys(), key=lambda emp_id: employees[emp_id].salario_contrato)
    
    print(f"🏆 Sunday Champion: {sunday_champion} (${employees[sunday_champion].salario_contrato:,})")
    
    # Get all Sundays in the month
    year = config.global_config.year
    month = config.global_config.month
    days_in_month = calendar.monthrange(year, month)[1]
    
    sundays = []
    for day in range(1, days_in_month + 1):
        current_date = date(year, month, day)
        if current_date.weekday() == 6:  # Sunday
            sundays.append(current_date)
    
    print(f"📅 Sundays in month: {len(sundays)}")
    
    constraints_added = []
    
    # Strategy 1: Sunday Champion should work as many Sundays as possible
    # This maximizes the Sunday coverage by the lowest-paid employee
    
    for sunday in sundays:
        sunday_shifts = [shift for shift in shifts if shift.date == sunday]
        
        for shift in sunday_shifts:
            # If Sunday Champion can work this shift, strongly prefer them
            if (sunday_champion, shift.shift_id) in x:
                # Add soft constraint: try to assign Sunday Champion to Sunday shifts
                # We'll implement this through weighted objectives in the main optimizer
                pass
    
    # Strategy 2: Limit other employees' Sunday exposure
    # Try to keep non-champion employees at ≤2 Sundays if mathematically possible
    
    threshold = config.global_config.sunday_threshold
    total_sunday_coverage_needed = len(sundays) * 2  # 2 shifts per Sunday (day + night)
    
    # Calculate if it's possible for non-champions to stay ≤ threshold
    non_champions = [emp_id for emp_id in employees.keys() if emp_id != sunday_champion]
    max_non_champion_sundays = len(non_champions) * threshold
    
    if total_sunday_coverage_needed > max_non_champion_sundays:
        # Champion MUST take excess Sundays
        excess_sundays_needed = total_sunday_coverage_needed - max_non_champion_sundays
        print(f"💪 Champion must cover {excess_sundays_needed} excess Sunday shifts")
        
        # Force champion to have excess Sundays
        model.Add(excess_sundays[sunday_champion] == 1)
        
        # Try to limit non-champions
        for emp_id in non_champions:
            if (emp_id, list(sundays)[0]) in sunday_worked:  # Check if Sunday variables exist
                total_sundays_worked = sum(sunday_worked[emp_id, sunday] for sunday in sundays 
                                         if (emp_id, sunday) in sunday_worked)
                
                # Soft constraint: prefer non-champions to stay at threshold
                # This will be handled by the weighted objective in main optimizer
                constraints_added.append(f"Prefer {emp_id} ≤ {threshold} Sundays")
    else:
        print(f"✅ Mathematically possible for all non-champions to stay ≤{threshold} Sundays")
    
    return constraints_added

def calculate_sunday_assignment_score(assignments: Dict, employees: Dict, shifts: List, config) -> float:
    """
    Calculate how good a Sunday assignment strategy is.
    Lower score = better (less total Sunday cost).
    """
    
    # Count Sundays per employee
    sunday_counts = {}
    total_sunday_cost = 0
    
    for emp_id in employees:
        sunday_counts[emp_id] = 0
        
    for shift in shifts:
        if shift.date.weekday() == 6 and shift.shift_id in assignments:  # Sunday
            emp_id = assignments[shift.shift_id]
            sunday_counts[emp_id] += 1
    
    # Calculate cost based on Sunday rule
    threshold = config.global_config.sunday_threshold
    
    for emp_id, sunday_count in sunday_counts.items():
        emp_salary_per_hour = employees[emp_id].salario_contrato / config.global_config.hours_base_month
        
        # Calculate total Sunday hours for this employee
        sunday_hours = 0
        for shift in shifts:
            if (shift.date.weekday() == 6 and shift.shift_id in assignments and 
                assignments[shift.shift_id] == emp_id):
                # Count Sunday hours in this shift
                for day_hours in shift.hours_by_day.values():
                    if day_hours.is_sunday:
                        sunday_hours += day_hours.total_hours
        
        if sunday_count > threshold:
            # Pay RF for all Sunday hours
            sunday_cost = sunday_hours * emp_salary_per_hour * config.global_config.rf_pct
        else:
            # No RF for Sunday hours (only for holidays, but we're focusing on Sundays here)
            sunday_cost = 0
        
        total_sunday_cost += sunday_cost
    
    return total_sunday_cost