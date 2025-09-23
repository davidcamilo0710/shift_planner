#!/usr/bin/env python3
"""
24/7 Shift Scheduler and Optimizer for Security Posts

This system optimizes shift assignments for security posts with the following objectives:
1. Minimize overtime (HE) - highest priority
2. Minimize holiday surcharge (RF) - focusing on Sunday excess
3. Minimize night surcharge (RN) - lowest priority

The system ensures complete coverage while respecting rest requirements,
employee constraints, and business rules.
"""

import sys
import argparse
from pathlib import Path
import logging
from datetime import datetime

import pandas as pd

from .config_loader import load_config
from .shift_generator import generate_shifts
from .optimizer import ShiftOptimizer
from .result_exporter import export_solution, create_detailed_validation_report
from .verifier import verify_solution, print_verification_report


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


def main():
    """Main function to run the shift optimizer."""
    
    parser = argparse.ArgumentParser(description="24/7 Shift Scheduler and Optimizer")
    parser.add_argument(
        "--config", 
        type=Path, 
        default=Path("config/optimizer_config.xlsx"),
        help="Path to the configuration Excel file"
    )
    parser.add_argument(
        "--output", 
        type=Path, 
        default=Path("output/scheduler_result.xlsx"),
        help="Path for the output Excel file"
    )
    parser.add_argument(
        "--strategy",
        choices=["lexicographic", "weighted"],
        default="lexicographic",
        help="Optimization strategy to use"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Generate detailed validation report"
    )
    parser.add_argument(
        "--sunday-strategy",
        choices=["smart", "balanced", "cost_focused"],
        default="smart",
        help="Sunday optimization strategy: smart (Sunday Champion - lowest paid employee takes more Sundays), balanced (equal distribution), cost_focused (direct cost minimization)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic results (default: 42)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from: {args.config}")
        config = load_config(args.config)
        logger.info(f"Configuration loaded successfully")
        logger.info(f"Year: {config.global_config.year}, Month: {config.global_config.month}")
        logger.info(f"Posts: {len(config.posts)}, Employees: {len(config.employees)}")
        
        # Generate shifts
        logger.info("Generating shifts...")
        shifts = generate_shifts(config)
        logger.info(f"Generated {len(shifts)} shifts")
        
        # Create and solve optimization model
        logger.info("Creating optimization model...")
        optimizer = ShiftOptimizer(config, shifts)
        
        logger.info(f"Starting optimization using {args.strategy} strategy...")
        if args.strategy == "lexicographic":
            logger.info(f"Sunday strategy: {args.sunday_strategy}")
        start_time = datetime.now()
        
        if args.strategy == "lexicographic" or config.global_config.use_lexicographic:
            solution = optimizer.solve_lexicographic(sunday_strategy=args.sunday_strategy, random_seed=args.seed)
        else:
            solution = optimizer.solve_weighted(random_seed=args.seed)
        
        solve_duration = (datetime.now() - start_time).total_seconds()
        
        # Check solution status
        if solution.solver_status in ["OPTIMAL", "FEASIBLE"]:
            logger.info(f"Optimization completed successfully in {solve_duration:.2f} seconds")
            logger.info(f"Status: {solution.solver_status}")
            logger.info(f"Active employees: {len(solution.active_employees)}")
            logger.info(f"Total assignments: {len(solution.assignments)}")
            
            # Log key metrics
            metrics = solution.total_metrics
            logger.info("=== Key Metrics ===")
            logger.info(f"Total cost: ${metrics['total_cost']:,.2f}")
            logger.info(f"Overtime hours: {metrics['total_he_hours']}")
            logger.info(f"Holiday hours applied: {metrics['total_rf_hours']}")
            logger.info(f"Night hours: {metrics['total_rn_hours']}")
            logger.info(f"Employees with excess sundays: {metrics['employees_with_excess_sundays']}")
            
        else:
            logger.error(f"Optimization failed: {solution.solver_status}")
            return 1
        
        # Create output directory if needed
        args.output.parent.mkdir(parents=True, exist_ok=True)
        
        # Verify solution
        logger.info("Verifying solution...")
        verification_result = verify_solution(solution, config, shifts)
        
        if not verification_result.is_valid:
            logger.error("Solution verification failed! Check the errors above.")
            if args.log_level == "DEBUG":
                print_verification_report(verification_result)
        
        # Export solution
        logger.info(f"Exporting solution to: {args.output}")
        export_solution(solution, config, shifts, args.output)
        
        # Generate validation report if requested
        if args.validate:
            validation_output = args.output.parent / f"validation_{args.output.stem}.xlsx"
            logger.info(f"Generating validation report: {validation_output}")
            
            validation_df = create_detailed_validation_report(solution, config, shifts)
            with pd.ExcelWriter(validation_output, engine='openpyxl') as writer:
                validation_df.to_excel(writer, sheet_name='ValidationReport', index=False)
            
            logger.info("Validation report generated")
        
        logger.info("Process completed successfully!")
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    exit(main())