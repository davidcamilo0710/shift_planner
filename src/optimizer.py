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
        """Calculate which shifts conflict due to consecutive shift rules."""
        self.shift_conflicts = get_shifts_with_conflicts(
            self.shifts, 
            0  # min_rest_hours no longer used - simplified consecutive rule
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
        for emp_id in self.employees:
            emp = self.employees[emp_id]
            
            # Calculate realistic max hours for this specific employee
            if emp.tipo == "FIJO":
                # FIJO employee can only work shifts from their assigned post
                employee_shifts = [s for s in self.shifts if s.post_id == emp.asignado_post_id]
            else:
                # COMODIN can work any shift, but still limited by time conflicts
                employee_shifts = self.shifts
            
            max_hours_for_employee = len(employee_shifts) * self.config.global_config.shift_length_hours
            max_centihours_for_employee = max_hours_for_employee * 100
            
            # Hours assigned (keep in hours)
            self.hours_assigned[emp_id] = self.model.NewIntVar(0, max_hours_for_employee, f"hours_assigned_{emp_id}")
            # Special hour types in centihours for precision
            self.hours_night[emp_id] = self.model.NewIntVar(0, max_centihours_for_employee, f"hours_night_{emp_id}")
            self.hours_holiday[emp_id] = self.model.NewIntVar(0, max_centihours_for_employee, f"hours_holiday_{emp_id}")
            self.hours_sunday[emp_id] = self.model.NewIntVar(0, max_centihours_for_employee, f"hours_sunday_{emp_id}")
            
            # Overtime hours in centihours
            max_he_centihours = max(0, int((max_hours_for_employee - self.employee_data[emp_id]['hours_to_work']) * 100))
            self.he_hours[emp_id] = self.model.NewIntVar(0, max_he_centihours, f"he_hours_{emp_id}")
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
    
    def _find_sunday_champions(self) -> Dict[str, str]:
        """
        Find Sunday Champions using multi-post strategy:
        - One champion per post (cheapest FIJO employee)
        - One global champion (cheapest COMODIN employee)
        
        Returns:
            Dict mapping champion_type -> emp_id
            e.g., {"P001": "E001", "P002": "E004", "Global": "E007"}
        """
        champions = {}
        
        # Champion per post (FIJO employees only)
        for post_id in self.posts:
            fixed_employees = [
                emp_id for emp_id, emp in self.employees.items()
                if emp.tipo == "FIJO" and emp.asignado_post_id == post_id
            ]
            
            if fixed_employees:
                # Find cheapest FIJO employee for this post
                post_champion = min(fixed_employees, key=lambda emp_id: self.employees[emp_id].salario_contrato)
                champions[f"Post {post_id}"] = post_champion
        
        # Global champion (COMODIN employees - can work anywhere)
        comodin_employees = [
            emp_id for emp_id, emp in self.employees.items()
            if emp.tipo == "COMODIN"
        ]
        
        if comodin_employees:
            # Find cheapest COMODIN employee
            global_champion = min(comodin_employees, key=lambda emp_id: self.employees[emp_id].salario_contrato)
            champions["Global"] = global_champion
        
        # If no COMODINES, find the overall cheapest employee as backup global champion
        if not comodin_employees and champions:
            # From existing post champions, find the absolute cheapest
            all_post_champions = list(champions.values())
            global_champion = min(all_post_champions, key=lambda emp_id: self.employees[emp_id].salario_contrato)
            champions["Global"] = global_champion
        elif not champions:
            # Fallback: just find cheapest employee overall
            cheapest_employee = min(self.employees.keys(), key=lambda emp_id: self.employees[emp_id].salario_contrato)
            champions["Global"] = cheapest_employee
        
        return champions
    
    def _analyze_sunday_roles(self) -> Dict[str, Dict]:
        """
        Analyze Sunday roles using intelligent strategy:
        
        For each post with FIJOS:
        - Champion: Cheapest FIJO (takes most Sundays)  
        - Helper: 2nd cheapest FIJO (≤2 Sundays max)
        - Others: Rest (minimal Sundays)
        
        COMODINES: Strategic relief workers (help where needed most)
        
        Returns:
            Dict with post_id -> roles mapping
        """
        roles = {}
        
        # Analyze each post with FIJO employees
        for post_id in self.posts:
            fixed_employees = [
                emp_id for emp_id, emp in self.employees.items()
                if emp.tipo == "FIJO" and emp.asignado_post_id == post_id
            ]
            
            if len(fixed_employees) >= 3:  # Normal case: 3+ FIJOS
                # Sort by salary (cheapest first)
                fixed_sorted = sorted(fixed_employees, key=lambda emp_id: self.employees[emp_id].salario_contrato)
                
                roles[post_id] = {
                    'champion': fixed_sorted[0],  # Cheapest takes most Sundays
                    'helper': fixed_sorted[1],    # 2nd cheapest helps (≤2 Sundays)
                    'others': fixed_sorted[2:]    # Rest avoid Sundays
                }
                
            elif len(fixed_employees) == 2:  # Special case: only 2 FIJOS
                fixed_sorted = sorted(fixed_employees, key=lambda emp_id: self.employees[emp_id].salario_contrato)
                roles[post_id] = {
                    'champion': fixed_sorted[0],  # Cheapest takes more
                    'helper': fixed_sorted[1]     # 2nd one helps
                }
                
            elif len(fixed_employees) == 1:  # Edge case: only 1 FIJO
                roles[post_id] = {
                    'champion': fixed_employees[0]  # Must take all Sundays
                }
        
        # COMODINES: Strategic relief workers
        comodin_employees = [
            emp_id for emp_id, emp in self.employees.items()
            if emp.tipo == "COMODIN"
        ]
        
        if comodin_employees:
            # Sort COMODINES by salary (cheapest first for relief work)
            comodines_sorted = sorted(comodin_employees, key=lambda emp_id: self.employees[emp_id].salario_contrato)
            roles["COMODINES"] = {
                'employees': comodines_sorted
            }
        
        return roles
    
    def _calculate_sunday_weight(self, emp_id: str, sunday_roles: Dict[str, Dict]) -> int:
        """
        Calculate AGGRESSIVE Sunday penalty weight based on employee's role.
        
        Lower weight = prefer this employee for excess Sundays
        Higher weight = avoid excess Sundays for this employee
        
        MUCH MORE AGGRESSIVE STRATEGY:
        - Champions: Weight 1 (WANT them to have excess)
        - Helpers: Weight 50 (can help but discouraged)  
        - Others: Weight 10000 (NEVER should have excess)
        - COMODINES: Weight 5 (encouraged for relief)
        """
        emp = self.employees[emp_id]
        base_salary_weight = int(emp.salario_contrato / 1000)
        
        if emp.tipo == "COMODIN":
            # COMODINES are strategic relief - encourage them for Sunday work
            return 5  # Very low penalty to encourage relief work
        
        # For FIJO employees, check their role in their post
        emp_post = emp.asignado_post_id
        if emp_post in sunday_roles:
            post_roles = sunday_roles[emp_post]
            
            if 'champion' in post_roles and post_roles['champion'] == emp_id:
                # Champion SHOULD take excess Sundays - lowest possible penalty
                print(f"      🏆 Champion {emp_id}: Weight 1 (WANTS excess Sundays)")
                return 1
                
            elif 'helper' in post_roles and post_roles['helper'] == emp_id:
                # Helper can help but should be discouraged from excess
                print(f"      🤝 Helper {emp_id}: Weight 50 (moderate excess OK)")
                return 50
                
            elif 'others' in post_roles and emp_id in post_roles['others']:
                # Others should NEVER have excess Sundays - BRUTAL penalty
                print(f"      🚫 Other {emp_id}: Weight 10000 (NO excess allowed)")
                return 10000
        
        # Default: high penalty
        return base_salary_weight * 10
    
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
            shift1 = self.shifts_by_id[shift_id1]
            shift2 = self.shifts_by_id[shift_id2]
            
            for emp_id in self.employees:
                emp = self.employees[emp_id]
                
                # Only apply conflict constraint if employee can potentially work both shifts
                can_work_shift1 = self._is_valid_assignment(emp_id, shift1)
                can_work_shift2 = self._is_valid_assignment(emp_id, shift2)
                
                if can_work_shift1 and can_work_shift2:
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
                # Prioritize individual max_posts_if_comodin, fallback to global max_posts_per_comodin
                max_posts = emp.max_posts_if_comodin if emp.max_posts_if_comodin > 0 else self.config.global_config.max_posts_per_comodin
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
            
            # Overtime calculation (use centihours for precision)
            hours_to_work_centihours = int(self.employee_data[emp_id]['hours_to_work'] * 100)
            hours_assigned_centihours = self.hours_assigned[emp_id] * 100
            self.model.Add(self.he_hours[emp_id] >= hours_assigned_centihours - hours_to_work_centihours)
            self.model.Add(self.he_hours[emp_id] >= 0)
            
            # Has overtime indicator
            # Calculate big_m based on the actual max bound of the HE variable
            emp = self.employees[emp_id]
            if emp.tipo == "FIJO":
                employee_shifts = [s for s in self.shifts if s.post_id == emp.asignado_post_id]
            else:
                employee_shifts = self.shifts
            max_hours_for_employee = len(employee_shifts) * self.config.global_config.shift_length_hours
            max_he_for_employee = max(0, int((max_hours_for_employee - self.employee_data[emp_id]['hours_to_work']) * 100))
            big_m = max_he_for_employee if max_he_for_employee > 0 else 1000
            self.model.Add(self.he_hours[emp_id] <= big_m * self.has_he[emp_id])
            self.model.Add(self.he_hours[emp_id] >= self.has_he[emp_id])
    
    def solve_lexicographic(self, sunday_strategy: str = "smart", random_seed: int = 42) -> Solution:
        """Solve using lexicographic optimization strategy."""
        
        # Set random seed for deterministic results
        self.solver.parameters.random_seed = random_seed
        print(f"🎲 Using random seed: {random_seed}")
        
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
        
        # Level 2: Minimize holiday surcharge (total RF hours)
        print("Optimizing Level 2: Holiday surcharge...")
        
        # Minimize total RF hours (holiday + conditional Sunday hours)
        # This is more complex because RF hours depend on Sunday count, but we can approximate
        # by minimizing: total_holiday_hours + total_sunday_hours
        # The solver will naturally prefer solutions that avoid excess Sunday hours when possible
        total_rf_hours = (
            sum(self.hours_holiday[emp_id] for emp_id in self.employees) +
            sum(self.hours_sunday[emp_id] for emp_id in self.employees)
        )
        self.model.Minimize(total_rf_hours)
        
        status = self.solver.Solve(self.model)
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._create_failed_solution("Level 2 failed")
        
        optimal_rf_hours = self.solver.Value(total_rf_hours)
        self.model.Add(total_rf_hours <= optimal_rf_hours)
        
        # Level 2b: Multiple Sunday optimization strategies
        if sunday_strategy == "smart":
            print("Optimizing Level 2b: Intelligent Sunday Strategy...")
            
            # Analyze setup: FIJOS vs COMODINES
            sunday_roles = self._analyze_sunday_roles()
            
            print("🧠 Sunday Strategy Analysis:")
            for post_id, roles in sunday_roles.items():
                if post_id == "COMODINES":
                    if roles['employees']:
                        print(f"   COMODINES: {len(roles['employees'])} relief employees")
                        for emp_id in roles['employees']:
                            print(f"     - {emp_id} (relief worker)")
                else:
                    print(f"   Post {post_id}:")
                    if 'champion' in roles:
                        print(f"     Champion: {roles['champion']} (takes most Sundays)")
                    if 'helper' in roles:
                        print(f"     Helper: {roles['helper']} (≤2 Sundays max)")
                    if 'others' in roles:
                        print(f"     Others: {roles['others']} (minimal Sundays)")
            
            # Create intelligent weights based on roles
            weighted_excess_sundays = []
            
            for emp_id in self.employees:
                emp = self.employees[emp_id]
                weight = self._calculate_sunday_weight(emp_id, sunday_roles)
                weighted_excess_sundays.append(self.excess_sundays[emp_id] * weight)
            
            smart_excess_objective = sum(weighted_excess_sundays)
            self.model.Minimize(smart_excess_objective)
            
        elif sunday_strategy == "balanced":
            print("Optimizing Level 2b: Balanced Sunday distribution...")
            # Equal penalty for all employees having excess Sundays
            total_excess_sundays = sum(self.excess_sundays[emp_id] for emp_id in self.employees)
            self.model.Minimize(total_excess_sundays)
            
        elif sunday_strategy == "cost_focused":
            print("Optimizing Level 2b: Cost-focused Sunday optimization...")
            # Directly minimize Sunday cost (skip to Level 2c logic)
            sunday_cost_terms = []
            for emp_id in self.employees:
                salary_per_hour = self.employee_data[emp_id]['salary_per_hour']
                rf_cost_per_centihour = salary_per_hour * self.config.global_config.rf_pct / 100
                sunday_cost = self.hours_sunday[emp_id] * int(rf_cost_per_centihour)
                sunday_cost_terms.append(sunday_cost)
            
            total_sunday_cost = sum(sunday_cost_terms)
            self.model.Minimize(total_sunday_cost)
            
        elif sunday_strategy == "load_balancing":
            print("Optimizing Level 2b: Load balancing (equal hours distribution)...")
            # Calculate total hours per employee (assigned hours = total hours worked)
            total_hours_per_emp = []
            for emp_id in self.employees:
                # hours_assigned is already the total hours worked by the employee
                total_hours_per_emp.append(self.hours_assigned[emp_id])
            
            # Minimize the maximum total hours worked by any employee
            max_hours = self.model.NewIntVar(0, 1000, 'max_hours')
            for total_hours in total_hours_per_emp:
                self.model.Add(max_hours >= total_hours)
            
            self.model.Minimize(max_hours)
            
        elif sunday_strategy == "surcharge_equity":
            print("Optimizing Level 2b: Surcharge equity distribution...")
            # Calculate surcharge value per employee (RF + RN + HE)
            surcharge_values = []
            for emp_id in self.employees:
                salary_per_hour = self.employee_data[emp_id]['salary_per_hour']
                
                # RF surcharge - use excess sundays logic similar to the existing code
                # If employee works excess sundays, RF applies to holiday + sunday hours
                # Otherwise, RF applies only to holiday hours
                rf_hours_applied = self.model.NewIntVar(0, 100000, f'rf_hours_applied_{emp_id}')
                
                # Use a conditional: if excess_sundays then holiday+sunday else holiday only
                rf_with_sunday = self.hours_holiday[emp_id] + self.hours_sunday[emp_id]
                rf_without_sunday = self.hours_holiday[emp_id]
                
                # If excess_sundays[emp_id] is true, use holiday+sunday, else use holiday only
                self.model.Add(rf_hours_applied >= rf_without_sunday)
                self.model.Add(rf_hours_applied <= rf_with_sunday)
                
                # Link to excess sundays: if no excess, then rf_hours_applied = holiday only
                self.model.Add(rf_hours_applied <= rf_without_sunday + (rf_with_sunday - rf_without_sunday) * self.excess_sundays[emp_id])
                self.model.Add(rf_hours_applied >= rf_without_sunday + (rf_with_sunday - rf_without_sunday) * self.excess_sundays[emp_id])
                
                # Calculate surcharge values (using integer math to avoid float issues)
                rf_value = int(salary_per_hour * self.config.global_config.rf_pct / 100) * rf_hours_applied
                rn_value = int(salary_per_hour * self.config.global_config.rn_pct / 100) * self.hours_night[emp_id]
                he_value = int(salary_per_hour * self.config.global_config.he_pct / 100) * self.he_hours[emp_id]
                
                total_surcharge = rf_value + rn_value + he_value
                surcharge_values.append(total_surcharge)
            
            # Minimize the maximum surcharge value (equitable distribution)
            max_surcharge = self.model.NewIntVar(0, 10000000, 'max_surcharge')
            for surcharge in surcharge_values:
                self.model.Add(max_surcharge >= surcharge)
            
            self.model.Minimize(max_surcharge)
            
        else:
            # Default: simple minimize excess employees
            total_excess_sundays = sum(self.excess_sundays[emp_id] for emp_id in self.employees)
            self.model.Minimize(total_excess_sundays)
        
        status = self.solver.Solve(self.model)
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._create_failed_solution("Level 2b failed")
        
        # Fix the objective value based on strategy
        if sunday_strategy == "smart":
            optimal_smart_excess = self.solver.Value(smart_excess_objective)
            self.model.Add(smart_excess_objective <= optimal_smart_excess)
        elif sunday_strategy == "cost_focused":
            optimal_sunday_cost_2b = self.solver.Value(total_sunday_cost)
            self.model.Add(total_sunday_cost <= optimal_sunday_cost_2b)
        else:
            optimal_excess_sundays = self.solver.Value(total_excess_sundays)
            self.model.Add(total_excess_sundays <= optimal_excess_sundays)
        
        # Level 2c: Minimize total Sunday cost (salary-weighted) for smarter distribution
        print("Optimizing Level 2c: Minimize total Sunday cost...")
        sunday_cost_terms = []
        for emp_id in self.employees:
            # Calculate cost per centihour for this employee's Sunday work
            salary_per_hour = self.employee_data[emp_id]['salary_per_hour']
            rf_cost_per_centihour = salary_per_hour * self.config.global_config.rf_pct / 100
            
            # Total Sunday cost for this employee (in integer units)
            sunday_cost = self.hours_sunday[emp_id] * int(rf_cost_per_centihour)
            sunday_cost_terms.append(sunday_cost)
        
        total_sunday_cost = sum(sunday_cost_terms)
        self.model.Minimize(total_sunday_cost)
        
        status = self.solver.Solve(self.model)
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._create_failed_solution("Level 2c failed")
        
        optimal_sunday_cost = self.solver.Value(total_sunday_cost) 
        self.model.Add(total_sunday_cost <= optimal_sunday_cost)
        
        # Level 3: Minimize night hours
        print("Optimizing Level 3: Night hours...")
        
        total_night_hours = sum(self.hours_night[emp_id] for emp_id in self.employees)
        self.model.Minimize(total_night_hours)
        
        status = self.solver.Solve(self.model)
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._create_failed_solution("Level 3 failed")
        
        return self._extract_solution(status)
    
    def solve_weighted(self, random_seed: int = 42) -> Solution:
        """Solve using weighted objective function."""
        
        # Set random seed for deterministic results
        self.solver.parameters.random_seed = random_seed
        print(f"🎲 Using random seed: {random_seed}")
        
        # Calculate weighted objective
        objective_terms = []
        
        # Overtime costs - convert centihours to hours
        for emp_id in self.employees:
            salary_per_hour = self.employee_data[emp_id]['salary_per_hour']
            he_cost = self.he_hours[emp_id] * salary_per_hour * self.config.global_config.he_pct / 100  # Convert centihours
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
                he_hours = self.solver.Value(self.he_hours[emp_id]) / 100.0  # Convert HE from centihours
                
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
                    'hours_to_work': emp_data['hours_to_work'],  # Required hours before overtime
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
                    'hours_to_work': emp_data['hours_to_work'],  # Required hours before overtime
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