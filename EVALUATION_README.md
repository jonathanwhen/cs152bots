# Hate Speech Detection Evaluation

This tool evaluates the performance of the Discord ModBot's hate speech detection system using a labeled dataset.

## Getting Started

1. Make sure you have all dependencies installed:
   ```
   pip install -r requirements.txt
   ```

2. Ensure your OpenAI API key is properly configured in `tokens.json`

3. Run the evaluation script:
   ```
   python evaluate_hate_speech.py
   ```
   
   Alternatively, you can use the provided shell scripts:
   - Windows: `run_evaluation.bat`
   - macOS/Linux: `bash run_evaluation.sh` (make sure to `chmod +x run_evaluation.sh` first)

## Interpretation of Results

The evaluation generates several outputs:

1. **Confusion Matrix**: Shows the count of True Positives (TP), True Negatives (TN), 
   False Positives (FP), and False Negatives (FN)

2. **Performance Metrics**:
   - **Accuracy**: Overall correctness (TP + TN) / Total
   - **Precision**: When the model predicts hate speech, how often is it correct? TP / (TP + FP)
   - **Recall**: What percentage of actual hate speech does the model catch? TP / (TP + FN)
   - **F1 Score**: Harmonic mean of precision and recall

3. **Visualization**: A heatmap of the confusion matrix saved as `confusion_matrix.png`

4. **Detailed Results**: Complete analysis saved in `evaluation_results.json`

5. **Sample Error Analysis**: Examples of false positives and false negatives

## Customizing the Evaluation

You can modify the following parameters in `evaluate_hate_speech.py`:

- `DATASET_PATH`: Path to your dataset CSV file
- `RESULTS_PATH`: Where to save the detailed results
- `SAMPLE_SIZE`: Number of entries to sample from the dataset (None for all)

## Dataset Format

The evaluation expects a CSV dataset with at least two columns:
- `content_text`: The text to analyze
- `label`: Binary classification (0 = not hate speech, 1 = hate speech)
