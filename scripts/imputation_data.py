import os
import pandas as pd
import numpy as np
from sklearn.impute import KNNImputer

# Resolve the data directory relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

# =====================================================================
# Imputation & Cleaning Stage
# Reads  : qa_checked_data.xlsx  (raw_data sheet + scorecard sheet)
# Writes : imputed_data.xlsx     (input for next stage)
# =====================================================================

# --- Read input from QA stage ---
input_file = os.path.join(DATA_DIR, "qa_checked_data.xlsx")
df = pd.read_excel(input_file, sheet_name="raw_data", engine="openpyxl")
qa_scorecard = pd.read_excel(input_file, sheet_name="scorecard", engine="openpyxl")
print(f"Loaded : {input_file}  ({df.shape[0]} rows, {df.shape[1]} cols)")


# =====================================================================
# Quality-scoring function (same 4 quantitative dimensions as QA stage)
# =====================================================================
VALIDITY_RULES = {
    "attendance_pct": (0, 100),
    "marks_math":     (0, 100),
    "marks_science":  (0, 100),
    "marks_english":  (0, 100),
}

def score_dataset(data: pd.DataFrame) -> pd.DataFrame:
    """Return a scorecard DataFrame with one row per quality dimension."""

    # 1. Completeness
    completeness = round((1 - data.isnull().mean().mean()) * 100, 1)

    # 2. Validity
    validity_scores = []
    for col, (lo, hi) in VALIDITY_RULES.items():
        valid = data[col].notna()
        bad = data.loc[valid, col].apply(lambda v: v < lo or v > hi).sum()
        total = valid.sum()
        validity_scores.append(
            round((1 - bad / total) * 100, 1) if total else 100.0
        )
    validity = round(np.mean(validity_scores), 1)

    # 3. Uniqueness
    uniqueness = round((1 - data.duplicated().sum() / len(data)) * 100, 1)

    # 4. Consistency (city column)
    city_raw = data["city"].dropna()
    distinct_raw = city_raw.nunique()
    distinct_norm = city_raw.str.strip().str.title().nunique()
    consistency = round((distinct_norm / distinct_raw) * 100, 1) if distinct_raw else 100.0

    return pd.DataFrame([
        {"dimension": "Completeness", "score_pct": completeness},
        {"dimension": "Validity",     "score_pct": validity},
        {"dimension": "Uniqueness",   "score_pct": uniqueness},
        {"dimension": "Consistency",  "score_pct": consistency},
    ])


# =====================================================================
# BEFORE scores (from the raw data as-is)
# =====================================================================
before_scores = score_dataset(df)

print(f"\n{'=' * 60}")
print("BEFORE IMPUTATION — quality scores")
print("=" * 60)
print(before_scores.to_string(index=False))
print(f"Overall: {round(before_scores['score_pct'].mean(), 1)}%")


# =====================================================================
# CLEANING  (fix validity & consistency before imputing)
# =====================================================================
df_clean = df.copy()

# Fix validity: cap impossible values to allowed range
df_clean["attendance_pct"] = df_clean["attendance_pct"].clip(0, 100)
df_clean["marks_science"]  = df_clean["marks_science"].clip(0, 100)

# Fix consistency: normalise city spellings
city_map = {
    "delhi":     "Delhi",
    "new delhi": "Delhi",
    "mumbai":    "Mumbai",
    "jaipur":    "Jaipur",
}
df_clean["city"] = (
    df_clean["city"]
    .str.strip()
    .str.lower()
    .map(city_map)
    .fillna(df_clean["city"].str.strip().str.title())
)

# Drop exact duplicate rows
before_dup = len(df_clean)
df_clean = df_clean.drop_duplicates().reset_index(drop=True)
print(f"\nDropped {before_dup - len(df_clean)} exact duplicate row(s)  "
      f"({len(df_clean)} rows remain)")


# =====================================================================
# IMPUTATION — 3 methods taught side by side
# =====================================================================
print(f"\n{'=' * 60}")
print("IMPUTATION METHODS")
print("=" * 60)

print(f"\nMissing values before imputation:")
missing = df_clean.isnull().sum()
print(missing[missing > 0].to_string())

# -----------------------------------------------------------------
# Method 1: MEDIAN imputation  (robust to outliers in numeric data)
# -----------------------------------------------------------------
med_val = df_clean["marks_math"].median()
df_clean["marks_math"] = df_clean["marks_math"].fillna(med_val)
print(f"\n  [1] Median imputation   -> marks_math  filled with median = {med_val}")

# -----------------------------------------------------------------
# Method 2: MODE imputation   (for categorical / discrete columns)
# -----------------------------------------------------------------
mode_val = df_clean["class"].mode()[0]
df_clean["class"] = df_clean["class"].fillna(mode_val)
print(f"  [2] Mode imputation     -> class        filled with mode  = '{mode_val}'")

# -----------------------------------------------------------------
# Method 3: KNN imputation    (uses similar rows to infer values)
# -----------------------------------------------------------------
knn_cols = ["attendance_pct", "marks_math", "marks_science", "marks_english"]
imputer = KNNImputer(n_neighbors=3)
df_clean[knn_cols] = imputer.fit_transform(df_clean[knn_cols])
print(f"  [3] KNN imputation (k=3)-> attendance_pct (+ numeric cols as features)")

print(f"\nMissing values after imputation:")
remaining = df_clean.isnull().sum()
if remaining.sum() == 0:
    print("  None -- all missing values filled!")
else:
    print(remaining[remaining > 0].to_string())


# =====================================================================
# AFTER scores
# =====================================================================
after_scores = score_dataset(df_clean)

print(f"\n{'=' * 60}")
print("AFTER IMPUTATION — quality scores")
print("=" * 60)
print(after_scores.to_string(index=False))
print(f"Overall: {round(after_scores['score_pct'].mean(), 1)}%")


# =====================================================================
# COMPARISON TABLE  (Before vs After, side by side)
# =====================================================================
comparison = before_scores.rename(columns={"score_pct": "before_pct"}).merge(
    after_scores.rename(columns={"score_pct": "after_pct"}),
    on="dimension",
)
comparison["change"] = (comparison["after_pct"] - comparison["before_pct"]).round(1)
comparison["change_str"] = comparison["change"].apply(
    lambda x: f"+{x}" if x > 0 else str(x)
)

before_overall = round(comparison["before_pct"].mean(), 1)
after_overall  = round(comparison["after_pct"].mean(), 1)
overall_change = round(after_overall - before_overall, 1)

# Add overall row
overall_row = pd.DataFrame([{
    "dimension":  "OVERALL",
    "before_pct": before_overall,
    "after_pct":  after_overall,
    "change":     overall_change,
    "change_str": f"+{overall_change}" if overall_change > 0 else str(overall_change),
}])
comparison = pd.concat([comparison, overall_row], ignore_index=True)

print(f"\n{'=' * 60}")
print("COMPARISON: QA-Check Phase  vs  Imputation Phase")
print("=" * 60)
print(comparison[["dimension", "before_pct", "after_pct", "change_str"]].to_string(index=False))


# =====================================================================
# SAVE OUTPUT FOR NEXT STAGE
# =====================================================================
output_file = os.path.join(DATA_DIR, "imputed_data.xlsx")
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_clean.to_excel(writer, sheet_name="clean_data", index=False)
    comparison.to_excel(writer, sheet_name="score_comparison", index=False)
    before_scores.to_excel(writer, sheet_name="scores_before", index=False)
    after_scores.to_excel(writer, sheet_name="scores_after", index=False)

print(f"\nSaved : {output_file}")
print("Sheets: clean_data, score_comparison, scores_before, scores_after")
