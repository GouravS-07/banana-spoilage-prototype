"""
Baseline Computer Vision Evaluation for Banana Ripeness Classification.
Extracts HSV color and dark-spot texture features and evaluates scikit-learn classifiers
on the verified Chuquimarca et al. Real Cavendish Banana Dataset (CC BY 4.0).
"""

import os
import glob
import json
import random
from pathlib import Path
import numpy as np
from PIL import Image
import joblib

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

RANDOM_SEED = 42
TARGET_PER_CLASS_1K = 250
DATASET_BASE = Path(__file__).resolve().parent / "dataset_raw" / "Banana Images" / "Real Dataset"
OUTPUT_DIR = Path(__file__).resolve().parent

CLASS_NAMES = ["Class A (Unripe)", "Class B (Half-Ripe)", "Class C (Ripe)", "Class D (Overripe)"]
CLASS_CODES = ["UNDER_RIPE", "HALF_RIPE", "RIPE", "OVER_RIPE"]

from app.services.vision_feature_extractor import extract_features_from_image, FEATURE_NAMES

def collect_all_real_images():
    """Gathers all image paths per class across train/validation/test folders."""
    class_map = {
        "Class A": 0,
        "Class B": 1,
        "Class C": 2,
        "Class D": 3,
    }
    data_by_class = {0: [], 1: [], 2: [], 3: []}
    
    for split in ["train", "validation", "test"]:
        split_dir = DATASET_BASE / split
        for cls_name, cls_idx in class_map.items():
            cls_dir = split_dir / cls_name
            for img_file in glob.glob(str(cls_dir / "*.png")):
                data_by_class[cls_idx].append(img_file)
                
    return data_by_class

def build_stratified_split(data_by_class, samples_per_class=250, train_ratio=0.70, val_ratio=0.15, seed=42):
    """
    Subsamples a deterministic, balanced set per class and partitions into
    Train (70%), Validation (15%), and Test (15%).
    """
    random.seed(seed)
    train_paths, train_y = [], []
    val_paths, val_y = [], []
    test_paths, test_y = [], []
    
    for cls_idx in range(4):
        paths = sorted(data_by_class[cls_idx])
        # Deterministic shuffle
        random.shuffle(paths)
        if samples_per_class and samples_per_class < len(paths):
            paths = paths[:samples_per_class]
            
        n = len(paths)
        n_train = int(round(n * train_ratio))
        n_val = int(round(n * val_ratio))
        
        c_train = paths[:n_train]
        c_val = paths[n_train:n_train + n_val]
        c_test = paths[n_train + n_val:]
        
        train_paths.extend(c_train)
        train_y.extend([cls_idx] * len(c_train))
        
        val_paths.extend(c_val)
        val_y.extend([cls_idx] * len(c_val))
        
        test_paths.extend(c_test)
        test_y.extend([cls_idx] * len(c_test))
        
    return (
        (train_paths, np.array(train_y)),
        (val_paths, np.array(val_y)),
        (test_paths, np.array(test_y)),
    )

def extract_dataset_features(file_paths):
    feats = []
    for p in file_paths:
        feats.append(extract_features_from_image(p))
    return np.array(feats, dtype=np.float32)

def main():
    print("=" * 70)
    print("PHASE 2 COMPUTER VISION BASELINE EVALUATION")
    print("Dataset: Chuquimarca et al. Real Cavendish Bananas (CC BY 4.0)")
    print("Feature Extraction: 12-dim HSV Color Distribution & Dark Spot Area")
    print("=" * 70)

    data_by_class = collect_all_real_images()
    for cls_idx in range(4):
        print(f"Verified {CLASS_NAMES[cls_idx]}: {len(data_by_class[cls_idx])} total images")

    # 1. Build balanced 1,000-image dataset (250/class)
    print("\n--- Partitioning Balanced 1,000-Image Benchmark (Seed 42) ---")
    (train_p, train_y), (val_p, val_y), (test_p, test_y) = build_stratified_split(
        data_by_class, samples_per_class=250, train_ratio=0.70, val_ratio=0.15, seed=RANDOM_SEED
    )
    print(f"Train set: {len(train_p)} images (Class counts: {np.bincount(train_y)})")
    print(f"Val set:   {len(val_p)} images (Class counts: {np.bincount(val_y)})")
    print(f"Test set:  {len(test_p)} images (Class counts: {np.bincount(test_y)})")

    # Extract features
    print("\nExtracting HSV & Dark-Spot features...")
    X_train = extract_dataset_features(train_p)
    X_val = extract_dataset_features(val_p)
    X_test = extract_dataset_features(test_p)
    print(f"Feature matrix shapes: Train {X_train.shape}, Val {X_val.shape}, Test {X_test.shape}")

    # 2. Model Evaluation on Validation Split
    print("\n--- Comparing Candidates on Validation Set ---")
    models = {
        "Majority Baseline (Dummy)": DummyClassifier(strategy="most_frequent"),
        "Logistic Regression": Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=1000, random_state=RANDOM_SEED))]),
        "Linear SVM": Pipeline([("scaler", StandardScaler()), ("clf", LinearSVC(dual="auto", random_state=RANDOM_SEED))]),
        "Random Forest (100 Trees)": RandomForestClassifier(n_estimators=100, max_depth=8, random_state=RANDOM_SEED),
    }

    val_results = {}
    for name, model in models.items():
        model.fit(X_train, train_y)
        preds = model.predict(X_val)
        acc = accuracy_score(val_y, preds)
        macro_f1 = f1_score(val_y, preds, average="macro")
        val_results[name] = {"accuracy": acc, "macro_f1": macro_f1, "model": model}
        print(f"  {name:30s} | Val Macro-F1: {macro_f1:.4f} | Val Accuracy: {acc:.4f}")

    # Select best model on validation set
    best_name = max(val_results, key=lambda k: val_results[k]["macro_f1"])
    best_model = val_results[best_name]["model"]
    print(f"\n>> Selected Best Model from Validation: {best_name}")

    # 3. Final Evaluation on Untouched Held-Out Test Set
    print("\n" + "=" * 70)
    print(f"FINAL HELD-OUT TEST EVALUATION: {best_name}")
    print("=" * 70)
    
    test_preds = best_model.predict(X_test)
    test_acc = accuracy_score(test_y, test_preds)
    test_macro_p = precision_score(test_y, test_preds, average="macro")
    test_macro_r = recall_score(test_y, test_preds, average="macro")
    test_macro_f1 = f1_score(test_y, test_preds, average="macro")
    
    # Majority baseline comparison on test set
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_train, train_y)
    dummy_preds = dummy.predict(X_test)
    dummy_f1 = f1_score(test_y, dummy_preds, average="macro")
    dummy_acc = accuracy_score(test_y, dummy_preds)

    print(f"\nTest Set Metrics:")
    print(f"  Macro Precision: {test_macro_p:.4f}")
    print(f"  Macro Recall:    {test_macro_r:.4f}")
    print(f"  Macro F1-Score:  {test_macro_f1:.4f} (vs. Dummy Majority F1: {dummy_f1:.4f})")
    print(f"  Overall Accuracy:{test_acc:.4f} (vs. Dummy Majority Acc: {dummy_acc:.4f})")

    report_str = classification_report(test_y, test_preds, target_names=CLASS_NAMES, digits=4)
    print("\nPer-Class Detailed Classification Report:")
    print(report_str)

    cm = confusion_matrix(test_y, test_preds)
    print("Confusion Matrix:")
    print("                 Pred A  Pred B  Pred C  Pred D")
    for idx, row in enumerate(cm):
        print(f"  True {CLASS_NAMES[idx]:18s} {row[0]:6d}  {row[1]:6d}  {row[2]:6d}  {row[3]:6d}")

    # 4. Check Probability Calibration & Confidence Distribution
    if hasattr(best_model, "predict_proba"):
        test_probs = best_model.predict_proba(X_test)
        max_probs = np.max(test_probs, axis=1)
        mean_conf = float(np.mean(max_probs))
        min_conf = float(np.min(max_probs))
        max_conf = float(np.max(max_probs))
        print(f"\nPrediction Confidence (Tree-Voting Proportion):")
        print(f"  Mean Confidence: {mean_conf:.3f} | Min: {min_conf:.3f} | Max: {max_conf:.3f}")
        print("  NOTICE: This output represents uncalibrated ensemble vote proportions,")
        print("          not true Bayesian probabilities.")
    else:
        mean_conf = None

    # 5. Save Model and Evaluation Artifacts
    artifact_path = OUTPUT_DIR / "baseline_color_rf.joblib"
    joblib.dump({
        "model": best_model,
        "feature_names": [
            "mean_h", "std_h", "mean_s", "std_s", "mean_v", "std_v",
            "green_ratio", "yellow_ratio", "brown_ratio",
            "dark_spot_ratio", "bright_ratio", "green_to_yellow"
        ],
        "class_codes": CLASS_CODES,
        "class_names": CLASS_NAMES,
        "random_seed": RANDOM_SEED,
    }, artifact_path)
    print(f"\nSaved trained model artifact to: {artifact_path}")

    # Save metrics JSON
    metrics_summary = {
        "model_architecture": best_name,
        "dataset_name": "Chuquimarca et al. Real Cavendish Dataset",
        "dataset_license": "CC BY 4.0",
        "random_seed": RANDOM_SEED,
        "sample_size_evaluated": 1000,
        "split_counts": {"train": len(train_y), "val": len(val_y), "test": len(test_y)},
        "test_metrics": {
            "macro_precision": round(float(test_macro_p), 4),
            "macro_recall": round(float(test_macro_r), 4),
            "macro_f1": round(float(test_macro_f1), 4),
            "accuracy": round(float(test_acc), 4),
            "dummy_baseline_f1": round(float(dummy_f1), 4),
            "dummy_baseline_accuracy": round(float(dummy_acc), 4),
        },
        "confusion_matrix": cm.tolist(),
        "classes": CLASS_CODES,
    }

    metrics_path = OUTPUT_DIR / "evaluation_summary.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics_summary, f, indent=2)
    print(f"Saved evaluation metrics to: {metrics_path}")

if __name__ == "__main__":
    main()
