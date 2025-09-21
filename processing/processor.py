#!/usr/bin/env python3
"""
Shift Processor - Wrapper class for the existing shift optimization logic
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

import pandas as pd

# Add src directory to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from src.config_loader import load_config
from src.shift_generator import generate_shifts
from src.optimizer import ShiftOptimizer
from src.result_exporter import export_solution, create_detailed_validation_report
from src.verifier import verify_solution

@dataclass
class ProcessingResult:
    """Result of schedule processing operation."""
    success: bool
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    strategy_used: Optional[str] = None
    total_assignments: Optional[int] = None
    output_file: Optional[str] = None
    validation_file: Optional[str] = None

class ShiftProcessor:
    """
    Wrapper class for the shift optimization system.
    Provides a clean interface for the FastAPI to call the existing processing logic.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def _setup_logging(self, log_level: str = "INFO") -> None:
        """Setup logging configuration for the processing operation."""
        # Set the log level for all relevant loggers
        loggers_to_configure = [
            __name__,
            'src.config_loader',
            'src.shift_generator', 
            'src.optimizer',
            'src.result_exporter',
            'src.verifier'
        ]
        
        level = getattr(logging, log_level.upper())
        for logger_name in loggers_to_configure:
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
    
    def process_schedule(
        self,
        config_file: str,
        output_file: str,
        strategy: str = "lexicographic",
        log_level: str = "INFO",
        validate: bool = False
    ) -> ProcessingResult:
        """
        Process shift schedule optimization.
        
        Args:
            config_file: Path to the configuration Excel file
            output_file: Path where to save the output Excel file
            strategy: Optimization strategy ("lexicographic" or "weighted")
            log_level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR")
            validate: Whether to generate detailed validation report
            
        Returns:
            ProcessingResult with success status and metadata
        """
        
        start_time = datetime.now()
        validation_file = None
        
        try:
            # Setup logging
            self._setup_logging(log_level)
            self.logger.info("Starting shift schedule processing")
            
            # Validate inputs
            config_path = Path(config_file)
            if not config_path.exists():
                return ProcessingResult(
                    success=False,
                    error_message=f"Configuration file not found: {config_file}"
                )
            
            output_path = Path(output_file)
            
            # Load configuration
            self.logger.info(f"Loading configuration from: {config_path}")
            config = load_config(config_path)
            self.logger.info(f"Configuration loaded successfully")
            self.logger.info(f"Year: {config.global_config.year}, Month: {config.global_config.month}")
            self.logger.info(f"Posts: {len(config.posts)}, Employees: {len(config.employees)}")
            
            # Generate shifts
            self.logger.info("Generating shifts...")
            shifts = generate_shifts(config)
            self.logger.info(f"Generated {len(shifts)} shifts")
            
            # Create and solve optimization model
            self.logger.info("Creating optimization model...")
            optimizer = ShiftOptimizer(config, shifts)
            
            self.logger.info(f"Starting optimization using {strategy} strategy...")
            optimization_start = datetime.now()
            
            # Choose optimization strategy
            if strategy == "lexicographic" or config.global_config.use_lexicographic:
                solution = optimizer.solve_lexicographic()
                actual_strategy = "lexicographic"
            else:
                solution = optimizer.solve_weighted()
                actual_strategy = "weighted"
            
            optimization_duration = (datetime.now() - optimization_start).total_seconds()
            
            # Check solution status
            if solution.solver_status not in ["OPTIMAL", "FEASIBLE"]:
                return ProcessingResult(
                    success=False,
                    error_message=f"Optimization failed with status: {solution.solver_status}",
                    processing_time=optimization_duration,
                    strategy_used=actual_strategy
                )
            
            self.logger.info(f"Optimization completed successfully in {optimization_duration:.2f} seconds")
            self.logger.info(f"Status: {solution.solver_status}")
            self.logger.info(f"Active employees: {len(solution.active_employees)}")
            self.logger.info(f"Total assignments: {len(solution.assignments)}")
            
            # Log key metrics
            metrics = solution.total_metrics
            self.logger.info("=== Key Metrics ===")
            self.logger.info(f"Total cost: ${metrics['total_cost']:,.2f}")
            self.logger.info(f"Overtime hours: {metrics['total_he_hours']}")
            self.logger.info(f"Holiday hours applied: {metrics['total_rf_hours']}")
            self.logger.info(f"Night hours: {metrics['total_rn_hours']}")
            self.logger.info(f"Employees with excess sundays: {metrics['employees_with_excess_sundays']}")
            
            # Create output directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Verify solution
            self.logger.info("Verifying solution...")
            verification_result = verify_solution(solution, config, shifts)
            
            if not verification_result.is_valid:
                self.logger.warning("Solution verification found issues, but continuing with export")
                if log_level == "DEBUG":
                    self.logger.debug("Verification details available in debug mode")
            
            # Export solution
            self.logger.info(f"Exporting solution to: {output_path}")
            export_solution(solution, config, shifts, output_path)
            
            # Generate validation report if requested
            if validate:
                validation_file = output_path.parent / f"validation_{output_path.stem}.xlsx"
                self.logger.info(f"Generating validation report: {validation_file}")
                
                validation_df = create_detailed_validation_report(solution, config, shifts)
                with pd.ExcelWriter(validation_file, engine='openpyxl') as writer:
                    validation_df.to_excel(writer, sheet_name='ValidationReport', index=False)
                
                self.logger.info("Validation report generated")
            
            total_duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Process completed successfully in {total_duration:.2f} seconds!")
            
            return ProcessingResult(
                success=True,
                processing_time=total_duration,
                strategy_used=actual_strategy,
                total_assignments=len(solution.assignments),
                output_file=str(output_path),
                validation_file=str(validation_file) if validation_file else None
            )
            
        except FileNotFoundError as e:
            error_msg = f"File not found: {e}"
            self.logger.error(error_msg)
            return ProcessingResult(
                success=False,
                error_message=error_msg,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return ProcessingResult(
                success=False,
                error_message=error_msg,
                processing_time=(datetime.now() - start_time).total_seconds()
            )

    def validate_config_file(self, config_file: str) -> ProcessingResult:
        """
        Validate configuration file without running optimization.
        
        Args:
            config_file: Path to the configuration Excel file
            
        Returns:
            ProcessingResult with validation status
        """
        
        try:
            self.logger.info(f"Validating configuration file: {config_file}")
            
            config_path = Path(config_file)
            if not config_path.exists():
                return ProcessingResult(
                    success=False,
                    error_message=f"Configuration file not found: {config_file}"
                )
            
            # Try to load configuration
            config = load_config(config_path)
            
            # Basic validation checks
            if not config.posts:
                return ProcessingResult(
                    success=False,
                    error_message="No posts found in configuration"
                )
            
            if not config.employees:
                return ProcessingResult(
                    success=False,
                    error_message="No employees found in configuration"
                )
            
            self.logger.info(f"Configuration valid - Posts: {len(config.posts)}, Employees: {len(config.employees)}")
            
            return ProcessingResult(
                success=True,
                error_message=f"Configuration is valid. Posts: {len(config.posts)}, Employees: {len(config.employees)}"
            )
            
        except Exception as e:
            error_msg = f"Configuration validation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return ProcessingResult(
                success=False,
                error_message=error_msg
            )