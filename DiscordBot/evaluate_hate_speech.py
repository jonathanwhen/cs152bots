import asyncio
import csv
import json
import os
import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns
from bot import ModBot

# Get the absolute path to the project directory
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configuration with absolute paths
DATASET_PATH = os.path.join(PROJECT_DIR, "data", "Stanford Class H.S5 Sub-Sample.csv")
RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluation_results.json")
SAMPLE_SIZE = None  # Specify number for partial testing (e.g., 20) or None for full dataset

async def load_dataset(path, sample_size=None):
    """Load dataset from CSV and optionally take a sample"""
    # Check if file exists
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Dataset file not found at: {path}")
    
    print(f"Reading dataset from: {path}")
    df = pd.read_csv(path)
    if sample_size and sample_size < len(df):
        return df.sample(sample_size, random_state=42)
    return df

async def evaluate_detection(bot, dataset):
    """Evaluate the bot's hate speech detection on the dataset"""
    results = []
    true_labels = []
    predicted_labels = []
    
    print(f"Processing {len(dataset)} dataset entries...")
    
    for idx, (text, label) in enumerate(zip(dataset['content_text'], dataset['label'])):
        if idx % 10 == 0:
            print(f"Processing item {idx}/{len(dataset)}...")
        
        # Strip out all non-ASCII characters to avoid encoding issues
        cleaned_text = ''.join(char for char in text if ord(char) < 128)
        
        # Get prediction from the bot
        prediction = await bot.eval_text(cleaned_text)
        
        # Check if hate speech was detected
        is_hate_speech = prediction.get('hate_speech_detected', False)
        
        # Store results
        results.append({
            'text': cleaned_text,
            'true_label': int(label),  # 1 for hate speech, 0 for not
            'predicted': int(is_hate_speech),  # 1 for detected, 0 for not detected
            'confidence': prediction.get('confidence_score', 'N/A'),
            'category': prediction.get('category', 'N/A'),
            'explanation': prediction.get('explanation', 'N/A')
        })
        
        true_labels.append(int(label))
        predicted_labels.append(int(is_hate_speech))
    
    return results, true_labels, predicted_labels

def save_results(results, path):
    """Save evaluation results to JSON file"""
    with open(path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {path}")

def create_confusion_matrix(true_labels, predicted_labels):
    """Generate and display confusion matrix"""
    # Calculate confusion matrix
    cm = confusion_matrix(true_labels, predicted_labels)
    
    # Display confusion matrix as text
    tn, fp, fn, tp = cm.ravel()
    total = tn + fp + fn + tp
    accuracy = (tn + tp) / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print("\nConfusion Matrix:")
    print(f"               | Predicted No | Predicted Yes")
    print(f"True No        | {tn} (TN)     | {fp} (FP)")
    print(f"True Yes       | {fn} (FN)     | {tp} (TP)")
    
    print("\nMetrics:")
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    
    # Create and save visualization
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Not Hate Speech', 'Hate Speech'],
                yticklabels=['Not Hate Speech', 'Hate Speech'])
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.title('Hate Speech Detection Confusion Matrix')
    plt.tight_layout()
    plt.savefig('confusion_matrix.png')
    print("Confusion matrix visualization saved as 'confusion_matrix.png'")
    
    # Prepare detailed classification report
    print("\nDetailed Classification Report:")
    report = classification_report(true_labels, predicted_labels, 
                                  target_names=['Not Hate Speech', 'Hate Speech'])
    print(report)
    
    return cm, accuracy, precision, recall, f1

async def main():
    """Main evaluation process"""
    print("Starting evaluation of hate speech detection...")
    
    # Verify dataset path
    if not os.path.isfile(DATASET_PATH):
        # Try to find the file in common locations
        possible_paths = [
            DATASET_PATH,
            os.path.join(PROJECT_DIR, "Stanford Class H.S5 Sub-Sample.csv"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "Stanford Class H.S5 Sub-Sample.csv"),
            os.path.join(os.getcwd(), "data", "Stanford Class H.S5 Sub-Sample.csv"),
            os.path.join(os.getcwd(), "Stanford Class H.S5 Sub-Sample.csv")
        ]
        
        found_path = None
        for path in possible_paths:
            if os.path.isfile(path):
                found_path = path
                break
        
        if found_path:
            print(f"Found dataset at alternate location: {found_path}")
            dataset_path = found_path
        else:
            print("ERROR: Dataset file not found. Please provide the correct path.")
            print(f"Looked in: {DATASET_PATH}")
            print("Current working directory:", os.getcwd())
            print("Project directory:", PROJECT_DIR)
            return
    else:
        dataset_path = DATASET_PATH
    
    # Initialize the bot
    bot = ModBot()
    
    try:
        # Load the dataset
        print(f"Loading dataset from {dataset_path}...")
        dataset = await load_dataset(dataset_path, SAMPLE_SIZE)
        print(f"Loaded {len(dataset)} entries")
        
        # Evaluate the bot on the dataset
        results, true_labels, predicted_labels = await evaluate_detection(bot, dataset)
        
        # Save detailed results
        save_results(results, RESULTS_PATH)
        
        # Create and display confusion matrix
        cm, accuracy, precision, recall, f1 = create_confusion_matrix(true_labels, predicted_labels)
        
        # Additional analysis
        print("\nSample False Positives (Non-hate speech classified as hate speech):")
        false_positives = [r for r in results if r['true_label'] == 0 and r['predicted'] == 1]
        for i, fp in enumerate(false_positives[:5]):  # Show first 5
            print(f"{i+1}. \"{fp['text'][:100]}...\" - Explanation: {fp['explanation'][:100]}...")
        
        print("\nSample False Negatives (Hate speech not detected):")
        false_negatives = [r for r in results if r['true_label'] == 1 and r['predicted'] == 0]
        for i, fn in enumerate(false_negatives[:5]):  # Show first 5
            print(f"{i+1}. \"{fn['text'][:100]}...\" - Explanation: {fn['explanation'][:100]}...")
    
    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\nEvaluation completed.")

if __name__ == "__main__":
    asyncio.run(main())
