#!/usr/bin/env python3
"""
Basic test scenario for the shift scheduler.
Tests a minimal setup: 1 post, 7 days, 3 fixed employees + 1 comodin.
"""

import sys
import unittest
from pathlib import Path
from datetime import date, time
import tempfile
import pandas as pd

# Add src to path for testing
src_path = str(Path(__file__).parent.parent / 'src')
sys.path.insert(0, src_path)

from config_loader import Config, GlobalConfig, Holiday, Post, Employee
from shift_generator import generate_shifts
from optimizer import ShiftOptimizer
from result_exporter import export_solution
from verifier import verify_solution


class TestBasicScenario(unittest.TestCase):
    """Test basic scenario with minimal setup."""
    
    def setUp(self):
        """Set up test configuration."""
        
        # Create global configuration
        self.global_config = GlobalConfig(
            year=2025,
            month=1,
            day_start=time(6, 0),
            night_start=time(21, 0),
            rn_pct=0.35,
            rf_pct=0.80,
            he_pct=1.25,
            hours_base_month=220.0,
            hours_per_week=44.0,
            min_fixed_per_post=3,
            shift_length_hours=12,
            day_shift_start=time(6, 0),
            night_shift_start=time(18, 0),
            min_rest_hours=12.0,
            sunday_threshold=2,
            max_posts_per_comodin=4,
            use_lexicographic=True,
            w_he=100.0,
            w_rf=10.0,
            w_rn=1.0,
            w_base=1.0
        )
        
        # Create holidays (New Year's Day)
        self.holidays = [
            Holiday(date=date(2025, 1, 1), description="New Year's Day")
        ]
        
        # Create one post
        self.posts = [
            Post(
                post_id="P001",
                nombre="Security Post 1",
                required_coverage=1,
                allow_day_shift=True,
                allow_night_shift=True
            )
        ]
        
        # Create employees: 3 fixed + 1 comodin
        base_salary = 1423500  # Colombian minimum wage
        self.employees = [
            Employee(
                emp_id="E001",
                tipo="FIJO",
                asignado_post_id="P001",
                empresa="Test Company",
                cargo="Security Guard",
                cliente="Test Client",
                salario_contrato=base_salary,
                disponible_desde=date(2025, 1, 1),
                disponible_hasta=date(2025, 12, 31),
                max_posts_if_comodin=1
            ),
            Employee(
                emp_id="E002",
                tipo="FIJO",
                asignado_post_id="P001",
                empresa="Test Company",
                cargo="Security Guard",
                cliente="Test Client",
                salario_contrato=base_salary,
                disponible_desde=date(2025, 1, 1),
                disponible_hasta=date(2025, 12, 31),
                max_posts_if_comodin=1
            ),
            Employee(
                emp_id="E003",
                tipo="FIJO",
                asignado_post_id="P001",
                empresa="Test Company",
                cargo="Security Guard",
                cliente="Test Client",
                salario_contrato=base_salary,
                disponible_desde=date(2025, 1, 1),
                disponible_hasta=date(2025, 12, 31),
                max_posts_if_comodin=1
            ),
            Employee(
                emp_id="E004",
                tipo="COMODIN",
                asignado_post_id=None,
                empresa="Test Company",
                cargo="Security Guard",
                cliente="Test Client",
                salario_contrato=base_salary,
                disponible_desde=date(2025, 1, 1),
                disponible_hasta=date(2025, 12, 31),
                max_posts_if_comodin=4
            )
        ]
        
        # Create complete config
        self.config = Config(
            global_config=self.global_config,
            holidays=self.holidays,
            posts=self.posts,
            employees=self.employees
        )
    
    def test_shift_generation(self):
        """Test shift generation for January 2025."""
        shifts = generate_shifts(self.config)
        
        # January 2025 has 31 days
        # Each day has 2 shifts (day + night)
        # 1 post * 31 days * 2 shifts = 62 total shifts
        expected_shifts = 31 * 2
        self.assertEqual(len(shifts), expected_shifts)
        
        # Check that we have the right mix of day/night shifts
        day_shifts = [s for s in shifts if not s.is_night]
        night_shifts = [s for s in shifts if s.is_night]
        
        self.assertEqual(len(day_shifts), 31)
        self.assertEqual(len(night_shifts), 31)
        
        # Check holiday marking (New Year's Day)
        holiday_shifts = [s for s in shifts if s.is_holiday]
        self.assertEqual(len(holiday_shifts), 2)  # Day + Night shifts on Jan 1
        
        # Check Sunday marking (Sundays in Jan 2025: 5, 12, 19, 26)
        sunday_shifts = [s for s in shifts if s.is_sunday]
        self.assertEqual(len(sunday_shifts), 8)  # 4 Sundays * 2 shifts each
    
    def test_basic_optimization(self):
        """Test basic optimization with minimal scenario."""
        shifts = generate_shifts(self.config)
        
        # Create optimizer
        optimizer = ShiftOptimizer(self.config, shifts)
        
        # Solve using lexicographic strategy
        solution = optimizer.solve_lexicographic()
        
        # Check solution status
        self.assertIn(solution.solver_status, ["OPTIMAL", "FEASIBLE"])
        
        # Check that all shifts are assigned
        self.assertEqual(len(solution.assignments), len(shifts))
        
        # Check that we have active employees
        self.assertGreater(len(solution.active_employees), 0)
        self.assertLessEqual(len(solution.active_employees), len(self.employees))
        
        # All assignments should be to valid employees
        for shift_id, emp_id in solution.assignments.items():
            self.assertIn(emp_id, [emp.emp_id for emp in self.employees])
    
    def test_solution_verification(self):
        """Test solution verification."""
        shifts = generate_shifts(self.config)
        optimizer = ShiftOptimizer(self.config, shifts)
        solution = optimizer.solve_lexicographic()
        
        # Verify solution
        verification_result = verify_solution(solution, self.config, shifts)
        
        # Solution should be valid (or have only warnings)
        if not verification_result.is_valid:
            print("Verification errors:")
            for error in verification_result.errors[:5]:
                print(f"  - {error}")
        
        # Print some metrics for debugging
        print(f"Total assignments: {verification_result.metrics.get('total_assignments', 'N/A')}")
        print(f"Active employees: {verification_result.metrics.get('active_employees', 'N/A')}")
        print(f"Errors: {len(verification_result.errors)}")
        print(f"Warnings: {len(verification_result.warnings)}")
    
    def test_export_functionality(self):
        """Test that solution can be exported to Excel."""
        shifts = generate_shifts(self.config)
        optimizer = ShiftOptimizer(self.config, shifts)
        solution = optimizer.solve_lexicographic()
        
        # Export to temporary file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            export_solution(solution, self.config, shifts, tmp_path)
            
            # Verify file was created
            self.assertTrue(tmp_path.exists())
            
            # Try to read the file back
            assignments_df = pd.read_excel(tmp_path, sheet_name='Asignacion')
            employee_summary_df = pd.read_excel(tmp_path, sheet_name='Resumen_Empleado')
            kpis_df = pd.read_excel(tmp_path, sheet_name='KPIs')
            
            # Basic checks
            self.assertEqual(len(assignments_df), len(shifts))
            self.assertEqual(len(employee_summary_df), len(self.employees))
            self.assertGreater(len(kpis_df), 0)
            
            print(f"Export test completed successfully. File: {tmp_path}")
            
        finally:
            # Clean up
            if tmp_path.exists():
                tmp_path.unlink()
    
    def test_constraint_satisfaction(self):
        """Test that key constraints are satisfied."""
        shifts = generate_shifts(self.config)
        optimizer = ShiftOptimizer(self.config, shifts)
        solution = optimizer.solve_lexicographic()
        
        # Check that fixed employees are only assigned to their post
        employees_dict = {emp.emp_id: emp for emp in self.employees}
        shifts_dict = {shift.shift_id: shift for shift in shifts}
        
        for shift_id, emp_id in solution.assignments.items():
            emp = employees_dict[emp_id]
            shift = shifts_dict[shift_id]
            
            if emp.tipo == "FIJO":
                self.assertEqual(shift.post_id, emp.asignado_post_id)
        
        # Check that we have at least minimum fixed employees per post
        fixed_employees_used = set()
        for emp_id in solution.active_employees:
            emp = employees_dict[emp_id]
            if emp.tipo == "FIJO" and emp.asignado_post_id == "P001":
                fixed_employees_used.add(emp_id)
        
        self.assertGreaterEqual(len(fixed_employees_used), 
                               self.config.global_config.min_fixed_per_post)
    
    def test_metrics_calculation(self):
        """Test that metrics are calculated correctly."""
        shifts = generate_shifts(self.config)
        optimizer = ShiftOptimizer(self.config, shifts)
        solution = optimizer.solve_lexicographic()
        
        # Check total metrics consistency
        total_metrics = solution.total_metrics
        employee_metrics = solution.employee_metrics
        
        # Sum of individual employee costs should match total
        calc_total_cost = sum(
            metrics['total_employee'] 
            for metrics in employee_metrics.values()
            if metrics['hours_assigned'] > 0
        )
        
        # Allow small floating-point differences
        self.assertAlmostEqual(calc_total_cost, total_metrics['total_cost'], places=2)
        
        print(f"Total cost: ${total_metrics['total_cost']:,.2f}")
        print(f"Active employees: {total_metrics['total_empleados_activos']}")
        print(f"Overtime hours: {total_metrics['total_he_hours']}")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)