from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import calendar
from datetime import date, timedelta
from ortools.sat.python import cp_model

try:
    from .config_loader import Config, Employee, Post
    from .shift_generator import Shift, calculate_night_hours, get_shifts_with_conflicts
except ImportError:
    from config_loader import Config, Employee, Post
    from shift_generator import Shift, calculate_night_hours, get_shifts_with_conflicts


@dataclass
class Solution:
    assignments: Dict[str, str]  # shift_id -> emp_id
    active_employees: List[str]
    employee_metrics: Dict[str, Dict]
    post_metrics: Dict[str, Dict]
    total_metrics: Dict
    objective_value: float
    solver_status: str
    solve_time: float


class ShiftOptimizer:
    def __init__(self, config: Config, shifts: List[Shift]):
        self.config = config
        self.shifts = shifts
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # Create indices
        self.employees = {emp.emp_id: emp for emp in config.employees}
        self.posts = {post.post_id: post for post in config.posts}
        self.shifts_by_id = {shift.shift_id: shift for shift in shifts}
        
        # Calculate derived data
        self._calculate_employee_data()
        self._calculate_shift_conflicts()
        
        # Variables
        self.x = {}  # x[emp_id, shift_id] = 1 if employee works shift
        self.active = {}  # active[emp_id] = 1 if employee is used
        self.z = {}  # z[emp_id, post_id] = 1 if comodin works in post
        self.sunday_worked = {}  # sunday_worked[emp_id, date] = 1 if worked sunday
        self.excess_sundays = {}  # excess_sundays[emp_id] = 1 if >threshold sundays
        
        # Continuous variables for metrics
        self.hours_assigned = {}
        self.hours_night = {}
        self.hours_holiday = {}
        self.hours_sunday = {}
        self.he_hours = {}
        self.has_he = {}
        
        self._create_variables()
        self._create_constraints()
    
    def _calculate_employee_data(self):
        """Calculate derived data for each employee."""
        year = self.config.global_config.year
        month = self.config.global_config.month
        days_in_month = calendar.monthrange(year, month)[1]
        
        self.employee_data = {}
        for emp_id, emp in self.employees.items():
            # Calculate salary per hour
            salary_per_hour = emp.salario_contrato / self.config.global_config.hours_base_month
            
            # Calculate hours to work (assuming full month availability)
            hours_to_work = (self.config.global_config.hours_per_week / 7) * days_in_month
            
            self.employee_data[emp_id] = {
                'salary_per_hour': salary_per_hour,
                'hours_to_work': hours_to_work,
                'linked_days': days_in_month,  # Assuming no disconnections
                'vacation_days': 0  # Assuming no vacations
            }
    
    def _calculate_shift_conflicts(self):
        """Calculate which shifts conflict due to rest requirements."""
        self.shift_conflicts = get_shifts_with_conflicts(
            self.shifts, 
            self.config.global_config.min_rest_hours
        )
    
    def _create_variables(self):
        """Create all optimization variables."""
        
        # Assignment variables x[emp_id, shift_id]
        for emp_id in self.employees:
            for shift in self.shifts:
                # Check if assignment is valid
                if self._is_valid_assignment(emp_id, shift):
                    var_name = f"x_{emp_id}_{shift.shift_id}"
                    self.x[emp_id, shift.shift_id] = self.model.NewBoolVar(var_name)
        
        # Active employee variables
        for emp_id in self.employees:
            self.active[emp_id] = self.model.NewBoolVar(f"active_{emp_id}")
        
        # Comodin-post assignment variables
        for emp_id, emp in self.employees.items():
            if emp.tipo == "COMODIN":
                for post_id in self.posts:
                    var_name = f"z_{emp_id}_{post_id}"
                    self.z[emp_id, post_id] = self.model.NewBoolVar(var_name)
        
        # Sunday worked variables
        sundays = self._get_sundays()
        for emp_id in self.employees:
            for sunday in sundays:
                date_str = sunday.strftime('%Y%m%d')
                var_name = f"sunday_{emp_id}_{date_str}"
                self.sunday_worked[emp_id, sunday] = self.model.NewBoolVar(var_name)
        
        # Excess sundays indicator
        for emp_id in self.employees:
            var_name = f"excess_sundays_{emp_id}"
            self.excess_sundays[emp_id] = self.model.NewBoolVar(var_name)
        
        # Continuous variables for hours and costs
        max_hours = len(self.shifts) * self.config.global_config.shift_length_hours
        max_centihours = max_hours * 100  # Convert to centihours for precision
        
        for emp_id in self.employees:
            # Hours assigned (keep in hours)
            self.hours_assigned[emp_id] = self.model.NewIntVar(0, max_hours, f"hours_assigned_{emp_id}")
            # Special hour types in centihours for precision
            self.hours_night[emp_id] = self.model.NewIntVar(0, max_centihours, f"hours_night_{emp_id}")
            self.hours_holiday[emp_id] = self.model.NewIntVar(0, max_centihours, f"hours_holiday_{emp_id}")
            self.hours_sunday[emp_id] = self.model.NewIntVar(0, max_centihours, f"hours_sunday_{emp_id}")
            
            # Overtime hours
            max_he = max(0, max_hours - self.employee_data[emp_id]['hours_to_work'])
            self.he_hours[emp_id] = self.model.NewIntVar(0, int(max_he), f"he_hours_{emp_id}")
            self.has_he[emp_id] = self.model.NewBoolVar(f"has_he_{emp_id}")
    
    def _is_valid_assignment(self, emp_id: str, shift: Shift) -> bool:
        """Check if an employee can be assigned to a shift."""
        emp = self.employees[emp_id]
        
        # Fixed employees can only work in their assigned post
        if emp.tipo == "FIJO":
            return shift.post_id == emp.asignado_post_id
        
        # Comodins can work in any post
        return True
    
    def _get_sundays(self) -> List[date]:
        """Get all Sunday dates in the month."""
        year = self.config.global_config.year
        month = self.config.global_config.month
        days_in_month = calendar.monthrange(year, month)[1]
        
        sundays = []
        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            if current_date.weekday() == 6:  # Sunday
                sundays.append(current_date)
        
        return sundays
    
    def _create_constraints(self):
        """Create all optimization constraints."""
        
        # 1. Coverage constraints - each shift must have exactly one employee
        shifts_by_post = {}
        for shift in self.shifts:
            if shift.post_id not in shifts_by_post:
                shifts_by_post[shift.post_id] = []
            shifts_by_post[shift.post_id].append(shift)
        
        for post_id, post_shifts in shifts_by_post.items():
            required_coverage = self.posts[post_id].required_coverage
            for shift in post_shifts:
                assigned_employees = []
                for emp_id in self.employees:
                    if (emp_id, shift.shift_id) in self.x:
                        assigned_employees.append(self.x[emp_id, shift.shift_id])
                
                if assigned_employees:
                    self.model.Add(sum(assigned_employees) == required_coverage)
        
        # 2. Employee activation constraints
        for emp_id in self.employees:
            for shift in self.shifts:
                if (emp_id, shift.shift_id) in self.x:
                    self.model.Add(self.x[emp_id, shift.shift_id] <= self.active[emp_id])
        
        # 3. Minimum rest and conflict constraints
        for shift_id1, shift_id2 in self.shift_conflicts:
            for emp_id in self.employees:
                vars_to_constrain = []
                if (emp_id, shift_id1) in self.x:
                    vars_to_constrain.append(self.x[emp_id, shift_id1])
                if (emp_id, shift_id2) in self.x:
                    vars_to_constrain.append(self.x[emp_id, shift_id2])
                
                if len(vars_to_constrain) == 2:
                    self.model.Add(sum(vars_to_constrain) <= 1)
        
        # 4. Minimum fixed employees per post
        for post_id, post in self.posts.items():
            fixed_employees_for_post = [
                emp_id for emp_id, emp in self.employees.items()
                if emp.tipo == "FIJO" and emp.asignado_post_id == post_id
            ]
            
            if len(fixed_employees_for_post) < self.config.global_config.min_fixed_per_post:
                raise ValueError(f"Post {post_id} has only {len(fixed_employees_for_post)} fixed employees, minimum required is {self.config.global_config.min_fixed_per_post}")
        
        # 5. Comodin post limits
        for emp_id, emp in self.employees.items():
            if emp.tipo == "COMODIN":
                max_posts = min(emp.max_posts_if_comodin, self.config.global_config.max_posts_per_comodin)
                comodin_posts = [self.z[emp_id, post_id] for post_id in self.posts]
                self.model.Add(sum(comodin_posts) <= max_posts)
                
                # Link z variables to x variables
                for post_id in self.posts:
                    post_shifts = [shift for shift in self.shifts if shift.post_id == post_id]
                    post_assignments = []
                    for shift in post_shifts:
                        if (emp_id, shift.shift_id) in self.x:
                            post_assignments.append(self.x[emp_id, shift.shift_id])
                    
                    if post_assignments:
                        # z[emp_id, post_id] >= any x[emp_id, shift] for shifts in post
                        for assignment in post_assignments:
                            self.model.Add(self.z[emp_id, post_id] >= assignment)
                        
                        # z[emp_id, post_id] <= sum of all x[emp_id, shift] for shifts in post
                        self.model.Add(self.z[emp_id, post_id] * len(post_assignments) >= sum(post_assignments))
        
        # 6. Sunday tracking constraints
        sundays = self._get_sundays()
        for emp_id in self.employees:
            for sunday in sundays:
                sunday_shifts = [shift for shift in self.shifts if shift.date == sunday]
                sunday_assignments = []
                for shift in sunday_shifts:
                    if (emp_id, shift.shift_id) in self.x:
                        sunday_assignments.append(self.x[emp_id, shift.shift_id])
                
                if sunday_assignments:
                    # Link sunday_worked to actual assignments
                    for assignment in sunday_assignments:
                        self.model.Add(self.sunday_worked[emp_id, sunday] >= assignment)
                    
                    self.model.Add(
                        self.sunday_worked[emp_id, sunday] * len(sunday_assignments) >= 
                        sum(sunday_assignments)
                    )
        
        # 7. Excess sundays tracking
        threshold = self.config.global_config.sunday_threshold
        for emp_id in self.employees:
            sundays_worked = [self.sunday_worked[emp_id, sunday] for sunday in sundays]
            if sundays_worked:
                # excess_sundays[emp_id] = 1 if sum(sundays_worked) > threshold
                self.model.Add(sum(sundays_worked) <= threshold + len(sundays) * self.excess_sundays[emp_id])
                self.model.Add(sum(sundays_worked) >= (threshold + 1) * self.excess_sundays[emp_id])
        
        # 8. Hours calculation constraints
        for emp_id in self.employees:
            # Total hours assigned
            total_hours_expr = []
            night_hours_expr = []
            holiday_hours_expr = []
            sunday_hours_expr = []
            
            for shift in self.shifts:
                if (emp_id, shift.shift_id) in self.x:
                    # Total hours (unchanged)
                    total_hours_expr.append(self.x[emp_id, shift.shift_id] * shift.duration_hours)
                    
                    # Calculate actual night hours from hours_by_day (convert to centihours for integer math)
                    shift_night_hours = sum(day_hours.night_hours for day_hours in shift.hours_by_day.values())
                    if shift_night_hours > 0:
                        night_hours_expr.append(self.x[emp_id, shift.shift_id] * int(shift_night_hours * 100))
                    
                    # Calculate actual holiday hours from hours_by_day (convert to centihours)
                    shift_holiday_hours = sum(day_hours.total_hours for day_hours in shift.hours_by_day.values() if day_hours.is_holiday)
                    if shift_holiday_hours > 0:
                        holiday_hours_expr.append(self.x[emp_id, shift.shift_id] * int(shift_holiday_hours * 100))
                    
                    # Calculate actual Sunday hours from hours_by_day (convert to centihours)
                    shift_sunday_hours = sum(day_hours.total_hours for day_hours in shift.hours_by_day.values() if day_hours.is_sunday)
                    if shift_sunday_hours > 0:
                        sunday_hours_expr.append(self.x[emp_id, shift.shift_id] * int(shift_sunday_hours * 100))
            
            if total_hours_expr:
                self.model.Add(self.hours_assigned[emp_id] == sum(total_hours_expr))
            else:
                self.model.Add(self.hours_assigned[emp_id] == 0)
            
            if night_hours_expr:
                self.model.Add(self.hours_night[emp_id] == sum(night_hours_expr))
            else:
                self.model.Add(self.hours_night[emp_id] == 0)
            
            if holiday_hours_expr:
                self.model.Add(self.hours_holiday[emp_id] == sum(holiday_hours_expr))
            else:
                self.model.Add(self.hours_holiday[emp_id] == 0)
            
            if sunday_hours_expr:
                self.model.Add(self.hours_sunday[emp_id] == sum(sunday_hours_expr))
            else:
                self.model.Add(self.hours_sunday[emp_id] == 0)
            
            # Overtime calculation
            hours_to_work = int(self.employee_data[emp_id]['hours_to_work'])
            self.model.Add(self.he_hours[emp_id] >= self.hours_assigned[emp_id] - hours_to_work)
            self.model.Add(self.he_hours[emp_id] >= 0)
            
            # Has overtime indicator
            big_m = 1000
            self.model.Add(self.he_hours[emp_id] <= big_m * self.has_he[emp_id])
            self.model.Add(self.he_hours[emp_id] >= self.has_he[emp_id])
    
    def solve_lexicographic(self) -> Solution:
        """Solve using lexicographic optimization strategy."""
        
        # Level 1: Minimize total overtime hours and employees with overtime
        print("Optimizing Level 1: Overtime...")
        
        # Minimize total HE hours
        total_he = sum(self.he_hours[emp_id] for emp_id in self.employees)
        self.model.Minimize(total_he)
        
        status = self.solver.Solve(self.model)
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._create_failed_solution("Level 1 failed")
        
        # Fix the overtime constraint for next level
        optimal_he = self.solver.Value(total_he)
        self.model.Add(total_he <= optimal_he)
        
        # Level 1b: Minimize number of employees with overtime
        total_has_he = sum(self.has_he[emp_id] for emp_id in self.employees)
        self.model.Minimize(total_has_he)
        
        status = self.solver.Solve(self.model)
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._create_failed_solution("Level 1b failed")
        
        optimal_has_he = self.solver.Value(total_has_he)
        self.model.Add(total_has_he <= optimal_has_he)
        
        # Level 2: Minimize holiday surcharge (focus on excess sundays)
        print("Optimizing Level 2: Holiday surcharge...")
        
        # Minimize employees with excess sundays
        total_excess_sundays = sum(self.excess_sundays[emp_id] for emp_id in self.employees)
        self.model.Minimize(total_excess_sundays)
        
        status = self.solver.Solve(self.model)
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._create_failed_solution("Level 2 failed")
        
        optimal_excess_sundays = self.solver.Value(total_excess_sundays)
        self.model.Add(total_excess_sundays <= optimal_excess_sundays)
        
        # Level 3: Minimize night hours
        print("Optimizing Level 3: Night hours...")
        
        total_night_hours = sum(self.hours_night[emp_id] for emp_id in self.employees)
        self.model.Minimize(total_night_hours)
        
        status = self.solver.Solve(self.model)
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._create_failed_solution("Level 3 failed")
        
        return self._extract_solution(status)
    
    def solve_weighted(self) -> Solution:
        """Solve using weighted objective function."""
        
        # Calculate weighted objective
        objective_terms = []
        
        # Overtime costs
        for emp_id in self.employees:
            salary_per_hour = self.employee_data[emp_id]['salary_per_hour']
            he_cost = self.he_hours[emp_id] * salary_per_hour * self.config.global_config.he_pct
            objective_terms.append(int(he_cost * self.config.global_config.w_he))
        
        # Holiday costs (simplified) - convert centihours to hours
        for emp_id in self.employees:
            salary_per_hour = self.employee_data[emp_id]['salary_per_hour']
            # RF applies only to holiday hours + excess sunday hours (in centihours, so divide by 100)
            rf_hours_centihours = self.hours_holiday[emp_id] + self.excess_sundays[emp_id] * self.hours_sunday[emp_id]
            rf_cost = rf_hours_centihours * salary_per_hour * self.config.global_config.rf_pct / 100  # Convert centihours to hours
            objective_terms.append(int(rf_cost * self.config.global_config.w_rf))
        
        # Night costs - convert centihours to hours
        for emp_id in self.employees:
            salary_per_hour = self.employee_data[emp_id]['salary_per_hour']
            rn_cost = self.hours_night[emp_id] * salary_per_hour * self.config.global_config.rn_pct / 100  # Convert centihours to hours
            objective_terms.append(int(rn_cost * self.config.global_config.w_rn))
        
        # Base salary costs
        for emp_id in self.employees:
            base_cost = self.active[emp_id] * self.employees[emp_id].salario_contrato
            objective_terms.append(int(base_cost * self.config.global_config.w_base))
        
        if objective_terms:
            self.model.Minimize(sum(objective_terms))
        
        status = self.solver.Solve(self.model)
        return self._extract_solution(status)
    
    def _create_failed_solution(self, message: str) -> Solution:
        """Create a failed solution object."""
        return Solution(
            assignments={},
            active_employees=[],
            employee_metrics={},
            post_metrics={},
            total_metrics={},
            objective_value=float('inf'),
            solver_status=message,
            solve_time=0.0
        )
    
    def _extract_solution(self, status) -> Solution:
        """Extract solution from solved model."""
        
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._create_failed_solution(f"Solver status: {status}")
        
        # Extract assignments
        assignments = {}
        for emp_id in self.employees:
            for shift in self.shifts:
                if (emp_id, shift.shift_id) in self.x:
                    if self.solver.Value(self.x[emp_id, shift.shift_id]):
                        assignments[shift.shift_id] = emp_id
        
        # Extract active employees
        active_employees = []
        for emp_id in self.employees:
            if self.solver.Value(self.active[emp_id]):
                active_employees.append(emp_id)
        
        # Store employee metrics for post calculation
        self.employee_metrics = self._calculate_employee_metrics()
        
        # Calculate metrics
        employee_metrics = self.employee_metrics
        post_metrics = self._calculate_post_metrics(assignments)
        total_metrics = self._calculate_total_metrics(employee_metrics)
        
        return Solution(
            assignments=assignments,
            active_employees=active_employees,
            employee_metrics=employee_metrics,
            post_metrics=post_metrics,
            total_metrics=total_metrics,
            objective_value=self.solver.ObjectiveValue() if status == cp_model.OPTIMAL else 0,
            solver_status="OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
            solve_time=self.solver.WallTime()
        )
    
    def _calculate_employee_metrics(self) -> Dict[str, Dict]:
        """Calculate metrics for each employee."""
        metrics = {}
        
        for emp_id in self.employees:
            emp = self.employees[emp_id]
            emp_data = self.employee_data[emp_id]
            
            if self.solver.Value(self.active[emp_id]):
                hours_assigned = self.solver.Value(self.hours_assigned[emp_id])
                # Convert centihours back to hours
                hours_night = self.solver.Value(self.hours_night[emp_id]) / 100.0
                hours_holiday = self.solver.Value(self.hours_holiday[emp_id]) / 100.0
                hours_sunday = self.solver.Value(self.hours_sunday[emp_id]) / 100.0
                he_hours = self.solver.Value(self.he_hours[emp_id])
                
                # Count worked sundays - use same logic as verifier
                # Count all Sunday dates where the employee actually worked hours
                sunday_dates_worked = set()
                for shift in self.shifts:
                    if (emp_id, shift.shift_id) in self.x and self.solver.Value(self.x[emp_id, shift.shift_id]):
                        # This employee was assigned this shift
                        for work_date, day_hours in shift.hours_by_day.items():
                            if day_hours.is_sunday and day_hours.total_hours > 0:
                                sunday_dates_worked.add(work_date)
                
                num_sundays = len(sunday_dates_worked)
                
                # Calculate RF hours based on Sunday work rule
                # Rule: ≤2 Sundays = only holiday hours, ≥3 Sundays = holiday + Sunday hours
                threshold = self.config.global_config.sunday_threshold
                if num_sundays > threshold:
                    # Employee worked more than threshold Sundays, so pay for both holiday and Sunday hours
                    rf_hours_applied = hours_holiday + hours_sunday
                else:
                    # Employee worked ≤ threshold Sundays, so only pay for holiday hours (not Sunday hours)
                    rf_hours_applied = hours_holiday
                
                # Calculate monetary values
                salary_per_hour = emp_data['salary_per_hour']
                val_rn = self.config.global_config.rn_pct * hours_night * salary_per_hour
                val_rf = self.config.global_config.rf_pct * rf_hours_applied * salary_per_hour
                val_he = self.config.global_config.he_pct * he_hours * salary_per_hour
                salary_base = emp.salario_contrato
                total_employee = val_rn + val_rf + val_he + salary_base
                
                metrics[emp_id] = {
                    'empresa': emp.empresa,
                    'cargo': emp.cargo,
                    'cliente': emp.cliente,
                    'salario_contrato': emp.salario_contrato,
                    'sueldo_hora': salary_per_hour,
                    'hours_assigned': hours_assigned,
                    'hours_night': hours_night,
                    'hours_holiday': hours_holiday,
                    'hours_sunday': hours_sunday,
                    'num_sundays': num_sundays,
                    'he_hours': he_hours,
                    'rf_hours_applied': rf_hours_applied,
                    'val_rn': val_rn,
                    'val_rf': val_rf,
                    'val_he': val_he,
                    'salary_base': salary_base,
                    'total_employee': total_employee
                }
            else:
                # Inactive employee
                metrics[emp_id] = {
                    'empresa': emp.empresa,
                    'cargo': emp.cargo,
                    'cliente': emp.cliente,
                    'salario_contrato': emp.salario_contrato,
                    'sueldo_hora': emp_data['salary_per_hour'],
                    'hours_assigned': 0,
                    'hours_night': 0,
                    'hours_holiday': 0,
                    'hours_sunday': 0,
                    'num_sundays': 0,
                    'he_hours': 0,
                    'rf_hours_applied': 0,
                    'val_rn': 0,
                    'val_rf': 0,
                    'val_he': 0,
                    'salary_base': 0,
                    'total_employee': 0
                }
        
        return metrics
    
    def _calculate_post_metrics(self, assignments: Dict[str, str]) -> Dict[str, Dict]:
        """Calculate metrics for each post."""
        metrics = {}
        
        for post_id in self.posts:
            post_shifts = [shift for shift in self.shifts if shift.post_id == post_id]
            total_cost = 0
            
            for shift in post_shifts:
                if shift.shift_id in assignments:
                    emp_id = assignments[shift.shift_id]
                    if emp_id in self.employee_metrics:
                        # Proportional cost allocation (simplified)
                        emp_total = self.employee_metrics[emp_id]['total_employee']
                        emp_hours = self.employee_metrics[emp_id]['hours_assigned']
                        if emp_hours > 0:
                            shift_cost = (emp_total / emp_hours) * shift.duration_hours
                            total_cost += shift_cost
            
            metrics[post_id] = {
                'nombre': self.posts[post_id].nombre,
                'total_shifts': len(post_shifts),
                'total_cost': total_cost
            }
        
        return metrics
    
    def _calculate_total_metrics(self, employee_metrics: Dict[str, Dict]) -> Dict:
        """Calculate total metrics across all employees."""
        
        active_employees = [emp_id for emp_id in employee_metrics if employee_metrics[emp_id]['hours_assigned'] > 0]
        
        # Count fixed vs comodines
        fixed_active = sum(1 for emp_id in active_employees if self.employees[emp_id].tipo == "FIJO")
        comodines_active = sum(1 for emp_id in active_employees if self.employees[emp_id].tipo == "COMODIN")
        
        # Sum totals
        total_he_hours = sum(employee_metrics[emp_id]['he_hours'] for emp_id in active_employees)
        total_rf_hours = sum(employee_metrics[emp_id]['rf_hours_applied'] for emp_id in active_employees)
        total_rn_hours = sum(employee_metrics[emp_id]['hours_night'] for emp_id in active_employees)
        
        total_val_he = sum(employee_metrics[emp_id]['val_he'] for emp_id in active_employees)
        total_val_rf = sum(employee_metrics[emp_id]['val_rf'] for emp_id in active_employees)
        total_val_rn = sum(employee_metrics[emp_id]['val_rn'] for emp_id in active_employees)
        total_salary_base = sum(employee_metrics[emp_id]['salary_base'] for emp_id in active_employees)
        
        total_cost = total_val_he + total_val_rf + total_val_rn + total_salary_base
        
        # Sunday distribution
        employees_with_excess_sundays = sum(
            1 for emp_id in active_employees 
            if employee_metrics[emp_id]['num_sundays'] > self.config.global_config.sunday_threshold
        )
        
        return {
            'total_empleados_activos': len(active_employees),
            'fijos_activos': fixed_active,
            'comodines_activos': comodines_active,
            'total_he_hours': total_he_hours,
            'total_rf_hours': total_rf_hours,
            'total_rn_hours': total_rn_hours,
            'total_val_he': total_val_he,
            'total_val_rf': total_val_rf,
            'total_val_rn': total_val_rn,
            'total_salary_base': total_salary_base,
            'total_cost': total_cost,
            'cost_per_post': total_cost / len(self.posts) if self.posts else 0,
            'employees_with_excess_sundays': employees_with_excess_sundays
        }