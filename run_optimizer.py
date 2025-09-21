#!/usr/bin/env python3
"""
Runner script for the 24/7 shift scheduler.

This script provides a convenient way to run the optimizer with the
existing configuration file.
"""

import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.main import main

if __name__ == "__main__":
    sys.exit(main())