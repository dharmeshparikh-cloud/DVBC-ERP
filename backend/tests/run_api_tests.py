#!/usr/bin/env python3
"""
Comprehensive API Test Suite Runner

Usage:
    python run_api_tests.py                    # Run all tests
    python run_api_tests.py -k auth            # Run only auth tests
    python run_api_tests.py -v                 # Verbose output
    python run_api_tests.py --security         # Run only OWASP security tests
    python run_api_tests.py --performance      # Run only performance tests
"""

import subprocess
import sys
import os
from pathlib import Path

# Test categories
TEST_FILES = {
    "auth": "test_api_auth.py",
    "leads": "test_api_leads.py",
    "employees": "test_api_employees.py",
    "clients_expenses": "test_api_clients_expenses.py",
    "projects_meetings": "test_api_projects_meetings.py",
    "sales_pipeline": "test_api_sales_pipeline.py",
    "hr_module": "test_api_hr_module.py",
    "users_roles": "test_api_users_roles.py",
    "security": "test_owasp_security.py",
    "performance": "test_api_performance.py",
}

def run_tests(test_files=None, extra_args=None):
    """Run pytest with specified test files."""
    test_dir = Path(__file__).parent
    os.chdir(test_dir)
    
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--asyncio-mode=auto",
    ]
    
    if test_files:
        cmd.extend(test_files)
    else:
        # Run all test_api_*.py and test_owasp_*.py files
        cmd.extend([
            "test_api_auth.py",
            "test_api_leads.py",
            "test_api_employees.py",
            "test_api_clients_expenses.py",
            "test_api_projects_meetings.py",
            "test_api_sales_pipeline.py",
            "test_api_hr_module.py",
            "test_api_users_roles.py",
            "test_owasp_security.py",
            "test_api_performance.py",
        ])
    
    if extra_args:
        cmd.extend(extra_args)
    
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def main():
    args = sys.argv[1:]
    
    # Parse custom flags
    test_files = None
    extra_args = []
    
    if "--security" in args:
        args.remove("--security")
        test_files = ["test_owasp_security.py"]
    elif "--performance" in args:
        args.remove("--performance")
        test_files = ["test_api_performance.py"]
    elif "--auth" in args:
        args.remove("--auth")
        test_files = ["test_api_auth.py"]
    elif "--leads" in args:
        args.remove("--leads")
        test_files = ["test_api_leads.py"]
    elif "--hr" in args:
        args.remove("--hr")
        test_files = ["test_api_hr_module.py"]
    elif "--sales" in args:
        args.remove("--sales")
        test_files = ["test_api_sales_pipeline.py"]
    
    extra_args.extend(args)
    
    sys.exit(run_tests(test_files, extra_args))


if __name__ == "__main__":
    main()
