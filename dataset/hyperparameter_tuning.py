import os

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sentence_transformers import SentenceTransformer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

# --- Configuration ---
INPUT_CSV_FILE = "training_data.csv"
SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"
# --- UPDATE: We will now save the tuned model ---
SAVED_MODEL_FILE = "best_xgboost_classifier.joblib"
LABEL_ENCODER_FILE = "label_encoder_best_xgboost.joblib"
CONFUSION_MATRIX_OUTPUT_FILE = "tuned_confusion_matrix.png"


def tune_and_save_best_xgboost():
    """
    Loads the dataset, performs hyperparameter tuning for XGBoost using GridSearchCV,
    evaluates the best model, and saves it.
    """
    # ==============================================================================
    # Step 1: Load the Dataset
    # ==============================================================================
    print(f"🔄 Step 1/6: Loading dataset from '{INPUT_CSV_FILE}'...")
    try:
        df = pd.read_csv(INPUT_CSV_FILE)
        df.dropna(subset=["text"], inplace=True)
        print(f"✅ Loaded {len(df)} records successfully.")
    except FileNotFoundError:
        print(f"❌ Error: The file '{INPUT_CSV_FILE}' was not found.")
        return

    # ==============================================================================
    # Step 2: Prepare Data and Split into Training/Testing Sets
    # ==============================================================================
    print(f"\n🔄 Step 2/6: Preparing and splitting the data...")
    le = LabelEncoder()
    df["label_encoded"] = le.fit_transform(df["label"])

    X = df["text"]
    y = df["label_encoded"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(
        f"✅ Data split into {len(X_train)} training records and {len(X_test)} testing records."
    )

    # ==============================================================================
    # Step 3: Create Vector Embeddings for the Data
    # ==============================================================================
    print(f"\n🔄 Step 3/6: Converting text to numerical vectors...")
    model_st = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
    X_train_vectors = model_st.encode(X_train.tolist(), show_progress_bar=True)
    X_test_vectors = model_st.encode(X_test.tolist(), show_progress_bar=True)
    print("✅ Vector embeddings created.")

    # ==============================================================================
    # Step 4: Hyperparameter Tuning with GridSearchCV
    # ==============================================================================
    print("\n🔄 Step 4/6: Starting hyperparameter tuning for XGBoost...")

    # Define the grid of parameters to search
    param_grid = {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 5, 7],
        "learning_rate": [0.01, 0.1, 0.2],
        "subsample": [0.7, 0.8, 1.0],
        "colsample_bytree": [0.7, 0.8, 1.0],
    }

    # Handle class imbalance
    counts = np.bincount(y_train)
    scale_pos_weight = counts[0] / counts[1]

    xgb = XGBClassifier(
        random_state=42,
        use_label_encoder=False,
        eval_metric="logloss",
        scale_pos_weight=scale_pos_weight,
    )

    # Set up GridSearchCV to find the best parameters based on F1-score for the 'relevant' class
    # The 'relevant' class is label '1' after encoding
    relevant_class_index = np.where(le.classes_ == "relevant")[0][0]
    grid_search = GridSearchCV(
        estimator=xgb,
        param_grid=param_grid,
        scoring=f"f1_macro",
        cv=3,
        n_jobs=-1,
        verbose=2,
    )

    grid_search.fit(X_train_vectors, y_train)

    print("\n--- Tuning Complete ---")
    print(f"🏆 Best Parameters Found: {grid_search.best_params_}")
    best_model = grid_search.best_estimator_

    # ==============================================================================
    # Step 5: Evaluate the Best Model
    # ==============================================================================
    print("\n🔄 Step 5/6: Evaluating the best tuned model on the test set...")
    y_pred_encoded = best_model.predict(X_test_vectors)

    print("\n--- Final Classification Report (Tuned Model) ---")
    print(classification_report(y_test, y_pred_encoded, target_names=le.classes_))

    cm = confusion_matrix(y_test, y_pred_encoded)
    plt.figure(figsize=(10, 7))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="YlGnBu",
        xticklabels=le.classes_,
        yticklabels=le.classes_,
    )
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.title("Confusion Matrix for the Tuned XGBoost Model")
    plt.savefig(CONFUSION_MATRIX_OUTPUT_FILE)
    print(f"\n✅ Tuned confusion matrix saved to '{CONFUSION_MATRIX_OUTPUT_FILE}'")

    # ==============================================================================
    # Step 6: Save the Best Model
    # ==============================================================================
    print(f"\n🔄 Step 6/6: Saving the best tuned model and label encoder...")
    joblib.dump(best_model, SAVED_MODEL_FILE)
    joblib.dump(le, LABEL_ENCODER_FILE)
    print(f"✅ Best model saved to '{SAVED_MODEL_FILE}'")
    print(f"✅ Label encoder saved to '{LABEL_ENCODER_FILE}'")

    print("\n🎉 Hyperparameter tuning workflow complete!")


if __name__ == "__main__":
    tune_and_save_best_xgboost()
