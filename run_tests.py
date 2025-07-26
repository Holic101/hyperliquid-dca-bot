#!/usr/bin/env python3
"""
Test runner script for the Hyperliquid DCA Bot.
Provides easy commands for running different types of tests.
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        print("""
Hyperliquid DCA Bot Test Runner

Usage: python run_tests.py <command>

Commands:
    all         - Run all tests with coverage
    unit        - Run only unit tests
    integration - Run only integration tests
    fast        - Run tests without coverage (faster)
    coverage    - Generate coverage report
    lint        - Run code linting
    format      - Format code with black
    check       - Run all checks (tests, lint, format check)

Examples:
    python run_tests.py all
    python run_tests.py unit
    python run_tests.py coverage
        """)
        return 1
    
    command = sys.argv[1].lower()
    project_root = Path(__file__).parent
    
    # Change to project directory
    import os
    os.chdir(project_root)
    
    success = True
    
    if command == "all":
        success &= run_command(
            "python -m pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html",
            "Running all tests with coverage"
        )
    
    elif command == "unit":
        success &= run_command(
            "python -m pytest tests/ -v -m 'not integration and not slow'",
            "Running unit tests"
        )
    
    elif command == "integration":
        success &= run_command(
            "python -m pytest tests/ -v -m integration",
            "Running integration tests"
        )
    
    elif command == "fast":
        success &= run_command(
            "python -m pytest tests/ -v --tb=short",
            "Running tests (fast mode)"
        )
    
    elif command == "coverage":
        success &= run_command(
            "python -m pytest tests/ --cov=src --cov-report=html --cov-report=term",
            "Generating coverage report"
        )
        if success:
            print("\n📊 Coverage report generated in htmlcov/index.html")
    
    elif command == "lint":
        # Check if flake8 is available
        try:
            success &= run_command(
                "python -m flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503",
                "Running code linting"
            )
        except:
            print("⚠️  flake8 not available. Install with: pip install flake8")
    
    elif command == "format":
        # Check if black is available
        try:
            success &= run_command(
                "python -m black src/ tests/ --line-length=100",
                "Formatting code with black"
            )
        except:
            print("⚠️  black not available. Install with: pip install black")
    
    elif command == "check":
        print("🔍 Running comprehensive checks...")
        
        success &= run_command(
            "python -m pytest tests/ -v --cov=src --cov-report=term-missing",
            "Running tests with coverage"
        )
        
        try:
            success &= run_command(
                "python -m flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503",
                "Running linting checks"
            )
        except:
            print("⚠️  Skipping lint check (flake8 not available)")
        
        try:
            success &= run_command(
                "python -m black src/ tests/ --check --line-length=100",
                "Checking code formatting"
            )
        except:
            print("⚠️  Skipping format check (black not available)")
    
    else:
        print(f"❌ Unknown command: {command}")
        return 1
    
    if success:
        print(f"\n✅ {command.capitalize()} completed successfully!")
        return 0
    else:
        print(f"\n❌ {command.capitalize()} failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())