#!/usr/bin/env python
"""
Environment Verification Script

Checks your Python environment for WarMachine AI and identifies any issues.
"""

import os
import sys
import importlib
import subprocess
import platform
from pathlib import Path

def print_header(text):
    """Print formatted header text"""
    print("\n" + "=" * 60)
    print(f" {text} ".center(60))
    print("=" * 60)

def print_success(text):
    """Print success message"""
    print(f"✅ {text}")

def print_error(text):
    """Print error message"""
    print(f"❌ {text}")

def print_warning(text):
    """Print warning message"""
    print(f"⚠️ {text}")

def print_info(text):
    """Print info message"""
    print(f"ℹ️ {text}")

def check_python_version():
    """Check Python version"""
    print_info(f"Python version: {platform.python_version()}")
    
    major, minor, micro = sys.version_info[:3]
    if major != 3 or minor < 9:
        print_error(f"Python 3.9+ required, got {major}.{minor}.{micro}")
        return False
    
    print_success("Python version is compatible")
    return True

def check_package(package_name, required_version=None):
    """Check if a package is installed and matches the required version"""
    try:
        module = importlib.import_module(package_name)
        version = getattr(module, "__version__", "unknown")
        
        if required_version and version != required_version:
            print_warning(f"{package_name} version mismatch: got {version}, expected {required_version}")
            return False
        
        print_success(f"{package_name} {version} is installed")
        return True
    except ImportError:
        print_error(f"{package_name} is not installed")
        return False
    except Exception as e:
        print_error(f"Error checking {package_name}: {str(e)}")
        return False

def check_numpy_indentation_error():
    """Specifically check for the numpy indentation error"""
    try:
        # Try to import numpy
        import numpy
        print_success("NumPy imported successfully")
        return True
    except IndentationError as e:
        file_path = getattr(e, 'filename', 'unknown')
        lineno = getattr(e, 'lineno', 'unknown')
        print_error(f"NumPy indentation error detected in {file_path} at line {lineno}")
        
        # If it's the specific _add_newdocs_scalars.py error
        if '_add_newdocs_scalars.py' in file_path:
            print_info("This is the error reported in the error message")
            print_info("Recommended fix: Run fix_numpy_error.ps1 script")
        return False
    except ImportError:
        print_error("NumPy is not installed")
        return False
    except Exception as e:
        print_error(f"Error importing NumPy: {str(e)}")
        return False

def fix_numpy_issue():
    """Try to fix the NumPy issue by reinstalling it"""
    try:
        print_info("Attempting to fix NumPy installation...")
        
        # Uninstall NumPy
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "numpy"])
        
        # Reinstall NumPy
        subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy==1.24.3"])
        
        # Try importing again
        import numpy
        print_success("NumPy fixed successfully!")
        print_info(f"NumPy version: {numpy.__version__}")
        return True
    except Exception as e:
        print_error(f"Failed to fix NumPy: {str(e)}")
        print_info("Please use the fix_numpy_error.ps1 script instead")
        return False

def check_config_file():
    """Check if the configuration file exists"""
    config_path = Path("config/warmachine_config.json")
    if config_path.exists():
        print_success("Configuration file found")
        return True
    else:
        print_error("Configuration file not found at config/warmachine_config.json")
        return False

def check_directories():
    """Check if required directories exist"""
    required_dirs = ["data", "logs", "cache", "examples", "utils"]
    missing_dirs = []
    
    for directory in required_dirs:
        if not Path(directory).exists():
            missing_dirs.append(directory)
    
    if missing_dirs:
        print_warning(f"Missing directories: {', '.join(missing_dirs)}")
        return False
    else:
        print_success("All required directories exist")
        return True

def main():
    """Main function"""
    print_header("WarMachine AI Environment Verification")
    
    # Check Python version
    python_ok = check_python_version()
    
    # Check core packages
    numpy_ok = check_package("numpy", "1.24.3")
    pandas_ok = check_package("pandas", "2.0.3")
    
    # If numpy failed, check for the specific indentation error
    if not numpy_ok:
        numpy_indent_error = check_numpy_indentation_error()
        if not numpy_indent_error:
            print_info("Would you like to attempt to fix the NumPy issue? (y/n)")
            choice = input().lower()
            if choice.startswith('y'):
                fix_numpy_issue()
    
    # Check more packages
    requests_ok = check_package("requests")
    matplotlib_ok = check_package("matplotlib")
    
    # Check configuration and directories
    config_ok = check_config_file()
    dirs_ok = check_directories()
    
    # Print summary
    print_header("Verification Summary")
    
    all_ok = python_ok and numpy_ok and pandas_ok and requests_ok and config_ok and dirs_ok
    
    if all_ok:
        print_success("All checks passed. Your environment is ready to run WarMachine AI.")
    else:
        print_warning("Some checks failed. Please fix the issues before running the system.")
        print_info("You can run fix_numpy_error.ps1 to fix package installation issues.")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main()) 