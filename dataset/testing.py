import os
import joblib
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sentence_transformers import SentenceTransformer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# --- Configuration ---
INPUT_CSV_FILE = "training_data.csv"
LABELED_DATA_FOLDER = "labeled_dataset"
SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"
SAVED_MODEL_FILE = "page_classifier.joblib"
LABEL_ENCODER_FILE = "label_encoder.joblib"
CONFUSION_MATRIX_OUTPUT_FILE = "confusion_matrix.png"


def test_and_analyze_errors():
    """
    Loads the best trained model and performs a detailed error analysis
    on the test set.
    """
    # ==============================================================================
    # Step 1: Load Models and Original Dataset
    # ==============================================================================
    print("🔄 Step 1/5: Loading saved models and the original dataset...")
    try:
        classifier = joblib.load(SAVED_MODEL_FILE)
        le = joblib.load(LABEL_ENCODER_FILE)
        df = pd.read_csv(INPUT_CSV_FILE)
        df.dropna(subset=['text'], inplace=True)
        print(f"✅ Models and dataset loaded successfully.")
    except FileNotFoundError as e:
        print(f"❌ Error: Could not find a required file: {e}. Please run 'train_model.py' first.")
        return

    # ==============================================================================
    # Step 2: Recreate the EXACT Same Test Split
    # ==============================================================================
    print("\n🔄 Step 2/5: Recreating the exact same test data split...")
    df['label_encoded'] = le.transform(df['label'])
    
    # We need to keep track of original filenames and labels
    X = df[['filename', 'text']]
    y = df[['label', 'label_encoded']]

    # Using the same random_state and stratify ensures the split is identical
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y['label_encoded']
    )
    print(f"✅ Test set with {len(X_test)} records recreated.")

    # ==============================================================================
    # Step 3: Create Vector Embeddings for the Test Set
    # ==============================================================================
    print("\n🔄 Step 3/5: Creating vector embeddings for the test set...")
    model_st = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
    X_test_vectors = model_st.encode(X_test['text'].tolist(), show_progress_bar=True)
    print("✅ Vector embeddings created.")

    # ==============================================================================
    # Step 4: Make Predictions and Generate Reports
    # ==============================================================================
    print("\n🔄 Step 4/5: Making predictions and generating reports...")
    y_pred_encoded = classifier.predict(X_test_vectors)
    y_pred_labels = le.inverse_transform(y_pred_encoded)

    # --- Colorful Confusion Matrix ---
    cm = confusion_matrix(y_test['label_encoded'], y_pred_encoded)
    plt.figure(figsize=(10, 7))
    sns.heatmap(cm, annot=True, fmt='d', cmap='YlGnBu', 
                xticklabels=le.classes_, yticklabels=le.classes_)
    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')
    plt.title('Confusion Matrix for the Best Model (XGBoost)')
    plt.savefig(CONFUSION_MATRIX_OUTPUT_FILE)
    print(f"✅ Colorful confusion matrix saved to '{CONFUSION_MATRIX_OUTPUT_FILE}'")
    

    # --- Colorful Classification Report ---
    print("\n--- Colorful Classification Report ---")
    report = classification_report(y_test['label_encoded'], y_pred_encoded, target_names=le.classes_, output_dict=True)
    for label, metrics in report.items():
        if isinstance(metrics, dict):
            p, r, f1 = metrics['precision'], metrics['recall'], metrics['f1-score']
            color = 'green' if f1 > 0.9 else 'yellow' if f1 > 0.8 else 'red'
            print(f"\033[1m{label:<12}\033[0m: "
                  f"Precision: \033[94m{p:.2f}\033[0m | "
                  f"Recall: \033[94m{r:.2f}\033[0m | "
                  f"F1-Score: \033[1;{32 if color == 'green' else 33 if color == 'yellow' else 31}m{f1:.2f}\033[0m")

    # ==============================================================================
    # Step 5: Identify and List Misclassifications
    # ==============================================================================
    print("\n🔄 Step 5/5: Analyzing misclassified files...")
    
    misclassified = []
    for i in range(len(X_test)):
        true_label = y_test['label'].iloc[i]
        pred_label = y_pred_labels[i]
        if true_label != pred_label:
            filename = X_test['filename'].iloc[i]
            # Reconstruct the original path to the file
            original_path = os.path.join(LABELED_DATA_FOLDER, true_label, filename)
            misclassified.append({
                "path": original_path,
                "true_label": true_label,
                "predicted_label": pred_label
            })

    if not misclassified:
        print("\n🎉 No misclassifications found on the test set! The model is perfect on this data.")
    else:
        print(f"\n❌ Found {len(misclassified)} misclassified files:")
        print("-" * 50)
        # Group errors by type for better analysis
        fp = [m for m in misclassified if m['true_label'] == 'irrelevant']
        fn = [m for m in misclassified if m['true_label'] == 'relevant']

        if fn:
            print("\n🚨 CRITICAL: Relevant pages predicted as Irrelevant (False Negatives):")
            for error in fn:
                print(f"   -> {error['path']}")
        
        if fp:
            print("\n⚠️ REVIEW: Irrelevant pages predicted as Relevant (False Positives):")
            for error in fp:
                print(f"   -> {error['path']}")
    
    print("\n✅ Error analysis complete.")


if __name__ == "__main__":
    test_and_analyze_errors()
