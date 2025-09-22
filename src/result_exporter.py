from pathlib import Path
from typing import List, Dict
import pandas as pd
from datetime import datetime

try:
    from .optimizer import Solution
    from .config_loader import Config
    from .shift_generator import Shift
except ImportError:
    from optimizer import Solution
    from config_loader import Config
    from shift_generator import Shift


def export_solution(solution: Solution, config: Config, shifts: List[Shift], 
                   output_path: Path) -> None:
    """Export solution to Excel file with multiple sheets."""
    
    # Create assignments sheet
    assignments_df = create_assignments_sheet(solution, config, shifts)
    
    # Create employee summary sheet
    employee_summary_df = create_employee_summary_sheet(solution)
    
    # Create post summary sheet
    post_summary_df = create_post_summary_sheet(solution)
    
    # Create KPIs sheet
    kpis_df = create_kpis_sheet(solution)
    
    # Write to Excel file
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        assignments_df.to_excel(writer, sheet_name='Asignacion', index=False)
        employee_summary_df.to_excel(writer, sheet_name='Resumen_Empleado', index=False)
        post_summary_df.to_excel(writer, sheet_name='Resumen_Puesto', index=False)
        kpis_df.to_excel(writer, sheet_name='KPIs', index=False)
        
        # Add metadata sheet
        metadata = create_metadata_sheet(solution, config)
        metadata.to_excel(writer, sheet_name='Metadata', index=False)
    
    print(f"Results exported to: {output_path}")


def create_assignments_sheet(solution: Solution, config: Config, 
                           shifts: List[Shift]) -> pd.DataFrame:
    """Create the assignments sheet showing daily schedule."""
    
    assignments_data = []
    employees = {emp.emp_id: emp for emp in config.employees}
    
    for shift in shifts:
        emp_id = solution.assignments.get(shift.shift_id, "UNASSIGNED")
        
        # Determine shift type and label
        if shift.is_night:
            turno_label = "N"
            turno_inicio = shift.start_time.strftime("%H:%M")
            turno_fin = shift.end_time.strftime("%H:%M")
        else:
            turno_label = "D"
            turno_inicio = shift.start_time.strftime("%H:%M")
            turno_fin = shift.end_time.strftime("%H:%M")
        
        # Get employee info
        emp_tipo = employees[emp_id].tipo if emp_id in employees else "UNKNOWN"
        
        assignments_data.append({
            'PostID': shift.post_id,
            'Fecha': shift.date.strftime("%Y-%m-%d"),
            'TurnoInicio': turno_inicio,
            'TurnoFin': turno_fin,
            'EmpID': emp_id,
            'Tipo': emp_tipo,
            'TurnoLabel': turno_label,
            'IsSunday': 1 if shift.is_sunday else 0,
            'IsHoliday': 1 if shift.is_holiday else 0,
            'DurationHours': shift.duration_hours
        })
    
    # Sort by post, date, and shift start time
    assignments_df = pd.DataFrame(assignments_data)
    assignments_df = assignments_df.sort_values(['PostID', 'Fecha', 'TurnoInicio'])
    
    return assignments_df


def create_employee_summary_sheet(solution: Solution) -> pd.DataFrame:
    """Create employee summary sheet with hours and costs."""
    
    employee_data = []
    
    for emp_id, metrics in solution.employee_metrics.items():
        employee_data.append({
            'EmpID': emp_id,
            'Empresa': metrics['empresa'],
            'Cargo': metrics['cargo'],
            'Cliente': metrics['cliente'],
            'SalarioContrato': metrics['salario_contrato'],
            'SueldoHora': round(metrics['sueldo_hora'], 2),
            'HoursAssigned': metrics['hours_assigned'],
            'HoursToWork': round(metrics['hours_to_work'], 2),  # Required hours before overtime
            'HoursNight': round(metrics['hours_night'], 2),
            'HoursHoliday': round(metrics['hours_holiday'], 2),
            'HoursSunday': round(metrics['hours_sunday'], 2),
            'NumDomingos': metrics['num_sundays'],
            'HE_horas': round(metrics['he_hours'], 2),  # Now with decimals
            'RF_horasAplicadas': round(metrics['rf_hours_applied'], 2),
            'Val_RN': round(metrics['val_rn'], 2),
            'Val_RF': round(metrics['val_rf'], 2),
            'Val_HE': round(metrics['val_he'], 2),
            'SalaryBase': round(metrics['salary_base'], 2),
            'TotalEmpleado': round(metrics['total_employee'], 2)
        })
    
    employee_df = pd.DataFrame(employee_data)
    
    # Sort by total cost descending, then by employee ID
    employee_df = employee_df.sort_values(['TotalEmpleado', 'EmpID'], ascending=[False, True])
    
    return employee_df


def create_post_summary_sheet(solution: Solution) -> pd.DataFrame:
    """Create post summary sheet with aggregated costs."""
    
    post_data = []
    
    for post_id, metrics in solution.post_metrics.items():
        post_data.append({
            'PostID': post_id,
            'Nombre': metrics['nombre'],
            'TotalShifts': metrics['total_shifts'],
            'TotalCost': round(metrics['total_cost'], 2),
            'CostPerShift': round(metrics['total_cost'] / metrics['total_shifts'] if metrics['total_shifts'] > 0 else 0, 2)
        })
    
    post_df = pd.DataFrame(post_data)
    post_df = post_df.sort_values('TotalCost', ascending=False)
    
    return post_df


def create_kpis_sheet(solution: Solution) -> pd.DataFrame:
    """Create KPIs sheet with overall metrics."""
    
    total_metrics = solution.total_metrics
    
    kpis_data = [
        {'Metric': 'TotalEmpleadosActivos', 'Value': total_metrics['total_empleados_activos']},
        {'Metric': 'FijosActivos', 'Value': total_metrics['fijos_activos']},
        {'Metric': 'ComodinesActivos', 'Value': total_metrics['comodines_activos']},
        {'Metric': 'TotalHE_horas', 'Value': total_metrics['total_he_hours']},
        {'Metric': 'TotalRF_horasAplicadas', 'Value': total_metrics['total_rf_hours']},
        {'Metric': 'TotalRN_horas', 'Value': total_metrics['total_rn_hours']},
        {'Metric': 'TotalVal_HE', 'Value': round(total_metrics['total_val_he'], 2)},
        {'Metric': 'TotalVal_RF', 'Value': round(total_metrics['total_val_rf'], 2)},
        {'Metric': 'TotalVal_RN', 'Value': round(total_metrics['total_val_rn'], 2)},
        {'Metric': 'TotalSalaryBase', 'Value': round(total_metrics['total_salary_base'], 2)},
        {'Metric': 'CostoTotal', 'Value': round(total_metrics['total_cost'], 2)},
        {'Metric': 'CostoPorPuesto', 'Value': round(total_metrics['cost_per_post'], 2)},
        {'Metric': 'EmpleadosConDomingos>2', 'Value': total_metrics['employees_with_excess_sundays']}
    ]
    
    return pd.DataFrame(kpis_data)


def create_metadata_sheet(solution: Solution, config: Config) -> pd.DataFrame:
    """Create metadata sheet with solution information."""
    
    metadata_data = [
        {'Parameter': 'SolutionStatus', 'Value': solution.solver_status},
        {'Parameter': 'ObjectiveValue', 'Value': solution.objective_value},
        {'Parameter': 'SolveTime', 'Value': round(solution.solve_time, 2)},
        {'Parameter': 'GeneratedAt', 'Value': datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
        {'Parameter': 'Year', 'Value': config.global_config.year},
        {'Parameter': 'Month', 'Value': config.global_config.month},
        {'Parameter': 'OptimizationStrategy', 'Value': 'Lexicographic' if config.global_config.use_lexicographic else 'Weighted'},
        {'Parameter': 'TotalShifts', 'Value': len(solution.assignments)},
        {'Parameter': 'TotalEmployees', 'Value': len(config.employees)},
        {'Parameter': 'TotalPosts', 'Value': len(config.posts)}
    ]
    
    return pd.DataFrame(metadata_data)


def create_detailed_validation_report(solution: Solution, config: Config, 
                                    shifts: List[Shift]) -> pd.DataFrame:
    """Create detailed validation report for verification."""
    
    validation_data = []
    employees = {emp.emp_id: emp for emp in config.employees}
    
    # Validate coverage
    for shift in shifts:
        assigned_emp = solution.assignments.get(shift.shift_id)
        if not assigned_emp:
            validation_data.append({
                'ValidationCheck': 'Coverage',
                'ShiftID': shift.shift_id,
                'PostID': shift.post_id,
                'Date': shift.date.strftime("%Y-%m-%d"),
                'Issue': 'No employee assigned',
                'Severity': 'ERROR'
            })
    
    # Validate employee constraints
    for emp_id in solution.active_employees:
        emp = employees[emp_id]
        emp_shifts = [shift_id for shift_id, assigned_emp in solution.assignments.items() 
                     if assigned_emp == emp_id]
        
        # Check fixed employee assignment constraints
        if emp.tipo == "FIJO":
            for shift_id in emp_shifts:
                shift = next(s for s in shifts if s.shift_id == shift_id)
                if shift.post_id != emp.asignado_post_id:
                    validation_data.append({
                        'ValidationCheck': 'FixedEmployeeAssignment',
                        'EmpID': emp_id,
                        'ShiftID': shift_id,
                        'PostID': shift.post_id,
                        'ExpectedPost': emp.asignado_post_id,
                        'Issue': 'Fixed employee assigned to wrong post',
                        'Severity': 'ERROR'
                    })
    
    return pd.DataFrame(validation_data) if validation_data else pd.DataFrame([{'ValidationCheck': 'All validations passed', 'Issue': 'None', 'Severity': 'INFO'}])