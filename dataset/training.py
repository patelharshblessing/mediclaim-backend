import joblib
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

# --- NEW: Import new models ---
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
from sklearn.naive_bayes import GaussianNB # NEW
from xgboost import XGBClassifier

# --- Configuration ---
INPUT_CSV_FILE = "training_data.csv"
SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"
OUTPUT_MODEL_FILE = "page_classifier.joblib"
LABEL_ENCODER_FILE = "label_encoder.joblib"


def train_and_evaluate():
    """
    The main function to train, evaluate, and save the page classification model.
    This version compares multiple classifiers and saves the best one.
    """
    # ... (Step 1, 2, and 3 remain exactly the same)
    # ==============================================================================
    # Step 1: Load the Dataset
    # ==============================================================================
    print(f"🔄 Step 1/7: Loading dataset from '{INPUT_CSV_FILE}'...")
    try:
        df = pd.read_csv(INPUT_CSV_FILE)
        df.dropna(subset=['text'], inplace=True)
        print(f"✅ Loaded {len(df)} records successfully.")
        print("\nDataset balance:")
        print(df['label'].value_counts())
    except FileNotFoundError:
        print(f"❌ Error: The file '{INPUT_CSV_FILE}' was not found.")
        print("Please run the 'prepare_dataset.py' script first.")
        return

    # ==============================================================================
    # Step 2: Prepare Data and Split into Training/Testing Sets
    # ==============================================================================
    print(f"\n🔄 Step 2/7: Preparing and splitting the data...")
    le = LabelEncoder()
    df['label_encoded'] = le.fit_transform(df['label'])
    
    X = df['text']
    y = df['label_encoded']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"✅ Data split into {len(X_train)} training records and {len(X_test)} testing records.")

    # ==============================================================================
    # Step 3: Feature Extraction (Convert Text to Vectors)
    # ==============================================================================
    print(f"\n🔄 Step 3/7: Converting text to numerical vectors...")
    print(f"Loading the '{SENTENCE_TRANSFORMER_MODEL}' model. This may take a moment...")
    model_st = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)

    print("Creating vector embeddings for the training data...")
    X_train_vectors = model_st.encode(X_train.tolist(), show_progress_bar=True)
    
    print("Creating vector embeddings for the testing data...")
    X_test_vectors = model_st.encode(X_test.tolist(), show_progress_bar=True)
    print("✅ Text successfully converted to vectors.")

    # ==============================================================================
    # Step 4 & 5: Train and Evaluate Multiple Models
    # ==============================================================================
    
    # --- UPDATE: Add new models to the dictionary ---
    models = {
        "Logistic Regression": LogisticRegression(class_weight="balanced", random_state=42, max_iter=1000),
        "SVM": SVC(class_weight="balanced", random_state=42, probability=True),
        "Random Forest": RandomForestClassifier(class_weight="balanced", random_state=42),
        "XGBoost": XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss'),
        "LightGBM": LGBMClassifier(class_weight="balanced", random_state=42),
        "CatBoost": CatBoostClassifier(random_state=42, verbose=0),
        "Gaussian Naive Bayes": GaussianNB()
    }
    
    best_model = None
    best_f1_score = -1.0
    best_model_name = ""

    for model_name, classifier in models.items():
        print("-" * 50)
        print(f"\n🔄 Training the {model_name} model...")

        # Special handling for Gradient Boosting models class weight
        if model_name in ["XGBoost", "CatBoost"]:
            counts = np.bincount(y_train)
            if len(counts) > 1 and counts[1] > 0:
                scale_pos_weight = counts[0] / counts[1]
                if model_name == "XGBoost":
                    classifier.scale_pos_weight = scale_pos_weight
                elif model_name == "CatBoost":
                    classifier.set_params(scale_pos_weight=scale_pos_weight)

        classifier.fit(X_train_vectors, y_train)
        print(f"✅ {model_name} training complete.")

        print(f"\n📊 Evaluating {model_name} performance...")
        y_pred = classifier.predict(X_test_vectors)

        print(f"\n--- Classification Report for {model_name} ---")
        print(classification_report(y_test, y_pred, target_names=le.classes_))
        
        relevant_class_label = le.transform(['relevant'])[0]
        current_f1 = f1_score(y_test, y_pred, pos_label=relevant_class_label, average='binary')
        print(f"F1-Score (Relevant Class): {current_f1:.4f}")
        
        if current_f1 > best_f1_score:
            best_f1_score = current_f1
            best_model = classifier
            best_model_name = model_name

    # ==============================================================================
    # Step 6: Announce the Winner
    # ==============================================================================
    print("-" * 50)
    print(f"\n🏆 Best performing model is '{best_model_name}' with an F1-Score of {best_f1_score:.4f} for the 'relevant' class.")

    # ==============================================================================
    # Step 7: Save the Best Model
    # ==============================================================================
    print(f"\n🔄 Step 7/7: Saving the best model ('{best_model_name}')...")
    joblib.dump(best_model, OUTPUT_MODEL_FILE)
    joblib.dump(le, LABEL_ENCODER_FILE)
    print(f"✅ Model saved to '{OUTPUT_MODEL_FILE}'")
    print(f"✅ Label encoder saved to '{LABEL_ENCODER_FILE}'")
    
    print("\n🎉 Training workflow complete! Your best custom model is ready to be used.")


if __name__ == "__main__":
    train_and_evaluate()

