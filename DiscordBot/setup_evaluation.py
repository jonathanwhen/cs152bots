#!/usr/bin/env python3

import os
import shutil
import sys

def find_file(filename, start_dir=None):
    """Find a file by walking through directories"""
    if start_dir is None:
        start_dir = os.getcwd()
    
    print(f"Searching for {filename} starting from {start_dir}")
    
    for root, dirs, files in os.walk(start_dir):
        if filename in files:
            return os.path.join(root, filename)
    
    # If not found in current directory tree, try parent directory
    parent_dir = os.path.dirname(start_dir)
    if parent_dir != start_dir:  # Prevent infinite recursion
        return find_file(filename, parent_dir)
    
    return None

def ensure_data_directory():
    """Create data directory if it doesn't exist"""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_dir, "data")
    
    if not os.path.exists(data_dir):
        print(f"Creating data directory at {data_dir}")
        os.makedirs(data_dir)
    
    return data_dir

def main():
    """Main setup function"""
    print("Setting up hate speech evaluation...")
    
    # Define the dataset filename
    dataset_filename = "Stanford Class H.S5 Sub-Sample.csv"
    
    # Get the correct paths
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.join(project_dir, "data", dataset_filename)
    
    # Check if dataset already exists in the target location
    if os.path.isfile(target_path):
        print(f"Dataset already exists at {target_path}")
        return True
    
    # Ensure data directory exists
    data_dir = ensure_data_directory()
    
    # Try to find the dataset file
    found_path = find_file(dataset_filename)
    
    if found_path:
        print(f"Found dataset at: {found_path}")
        
        # Copy to the target location
        shutil.copy2(found_path, target_path)
        print(f"Copied dataset to: {target_path}")
        return True
    else:
        print(f"ERROR: Could not find {dataset_filename} in directory tree.")
        print("Please manually copy the dataset file to:", target_path)
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\nSetup completed successfully. You can now run evaluate_hate_speech.py")
        print("Command: python evaluate_hate_speech.py")
    else:
        print("\nSetup failed. Please resolve the issues before running the evaluation.")
    
    sys.exit(0 if success else 1)
