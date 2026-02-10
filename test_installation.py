#!/usr/bin/env python3
"""
Quick test script to verify installation and basic functionality.
"""

import sys
import subprocess
import importlib


def check_command(cmd, name):
    """Check if a command is available"""
    try:
        result = subprocess.run([cmd, '--version'], 
                              capture_output=True, 
                              text=True,
                              timeout=5)
        print(f"✓ {name} is installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print(f"✗ {name} is NOT installed")
        return False


def check_python_module(module_name, display_name=None):
    """Check if a Python module is available"""
    if display_name is None:
        display_name = module_name
    
    try:
        importlib.import_module(module_name)
        print(f"✓ Python module '{display_name}' is available")
        return True
    except ImportError:
        print(f"✗ Python module '{display_name}' is NOT available")
        return False


def test_mininet():
    """Test Mininet basic functionality"""
    print("\nTesting Mininet...")
    try:
        result = subprocess.run(['sudo', 'mn', '--test', 'pingall'],
                              capture_output=True,
                              text=True,
                              timeout=30)
        if result.returncode == 0:
            print("✓ Mininet test passed")
            return True
        else:
            print("✗ Mininet test failed")
            return False
    except Exception as e:
        print(f"✗ Mininet test error: {e}")
        return False


def main():
    print("="*60)
    print("AI Data Center Routing - Installation Check")
    print("="*60)
    
    all_ok = True
    
    print("\n### System Commands ###")
    all_ok &= check_command('mn', 'Mininet')
    all_ok &= check_command('ovs-vsctl', 'Open vSwitch')
    all_ok &= check_command('iperf3', 'iperf3')
    all_ok &= check_command('python3', 'Python 3')
    
    print("\n### Python Modules ###")
    all_ok &= check_python_module('mininet')
    all_ok &= check_python_module('matplotlib')
    all_ok &= check_python_module('numpy')
    
    print("\n### Project Files ###")
    import os
    
    required_files = [
        'topologies/leaf_spine.py',
        'routing/ecmp_routing.py',
        'routing/adaptive_routing.py',
        'routing/traffic_generator.py',
        'routing/monitor.py',
        'run_experiment.py',
        'analyze_results.py'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} NOT found")
            all_ok = False
    
    # Test Mininet (requires sudo)
    if os.geteuid() == 0:  # Running as root
        all_ok &= test_mininet()
    else:
        print("\n⚠ Skipping Mininet test (requires sudo)")
        print("  Run: sudo python3 test_installation.py")
    
    print("\n" + "="*60)
    if all_ok:
        print("✓ All checks passed! Ready to run experiments.")
        print("\nQuick start:")
        print("  sudo python3 run_experiment.py --mode comparison --duration 10")
    else:
        print("✗ Some checks failed. Please install missing dependencies.")
        print("\nRun setup script:")
        print("  sudo bash setup.sh")
    print("="*60)
    
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
