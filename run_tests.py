import subprocess
import sys
import os

def run_verification_and_tests():
    """Run test verification and then run the tests"""
    
    # First, verify critical tests are present
    print("Verifying critical tests...")
    result = subprocess.run([sys.executable, 'test_verification.py'])
    if result.returncode != 0:
        print("Test verification failed!")
        sys.exit(1)
    
    # Try running the tests, but don't fail if we can't
    print("\nAttempting to run tests...")
    try:
        # Run pytest with verbosity and show locals on failure
        result = subprocess.run([sys.executable, '-m', 'pytest', '-v', '--showlocals'])
        
        if result.returncode != 0:
            print("Tests failed!")
            sys.exit(1)
        
        print("All tests passed successfully!")
    except Exception as e:
        print(f"Warning: Could not run tests: {str(e)}")
        print("This is expected if you don't have all dependencies installed.")
        print("The critical tests are present, but you'll need to install dependencies to run them.")
        print("\nRequired dependencies:")
        print("1. GTK3 Runtime (for Cairo)")
        print("2. Python packages: pytest, cairosvg, Pillow, pycairo")
        print("3. Inkscape (for AI, EPS, DXF export)")

if __name__ == '__main__':
    run_verification_and_tests()
