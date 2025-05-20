#!/usr/bin/env python3

import os
import sys
import subprocess

def main():
    """Run the complete evaluation process"""
    print("===== Hate Speech Detection Evaluation =====")
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Run the setup script first
    print("\nStep 1: Setting up the evaluation environment...")
    setup_script = os.path.join(script_dir, "setup_evaluation.py")
    result = subprocess.run([sys.executable, setup_script], check=False)
    
    if result.returncode != 0:
        print("Setup failed. Please fix the issues and try again.")
        return False
    
    # Run the evaluation script
    print("\nStep 2: Running the evaluation...")
    eval_script = os.path.join(script_dir, "evaluate_hate_speech.py")
    result = subprocess.run([sys.executable, eval_script], check=False)
    
    if result.returncode != 0:
        print("Evaluation failed. Check the error messages above.")
        return False
    
    print("\nEvaluation completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
