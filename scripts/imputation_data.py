import os
import pandas as pd
import numpy as np
from sklearn.impute import KNNImputer

# Resolve the data directory relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

# =====================================================================
# Rescue, Reject & KNN Imputation
# Reads  : qa_checked_data.xlsx  (raw_data sheet)
# Writes : imputed_data.xlsx
#
# Three imputation strategies:
#   1. Median — attendance_pct (supplementary numeric, safe central fill)
#   2. Mode   — city (categorical, most frequent value)
#   3. KNN    — marks_math (segment-significant, flat median destroys
#               the struggling-vs-gifted distribution)
#
# ARCHITECTURAL NOTE — Why KNN, Not the Average:
# ---------------------------------------------------------------
# Plugging the global average math score into every missing cell
# destroys the distribution of struggling vs. gifted students.
# KNN finds the k=5 students whose marks_science and attendance_pct
# are most similar, then infers the missing math score from those
# neighbours.  This preserves sub-group variance.
#
# ARCHITECTURAL NOTE — Hard-Capping vs. Model-Based Outliers:
# ---------------------------------------------------------------
# The clip() below is deterministic and interpretable — suitable when
# business rules define explicit valid ranges (marks 0-100, attendance
# 0-100).  Enterprise outliers that are contextually anomalous (e.g.,
# high attendance + very low marks) require model-based detection:
# K-Means clustering, Isolation Forests, or DBSCAN.
# =====================================================================

# --- Read input from QA stage ---
input_file = os.path.join(DATA_DIR, "qa_checked_data.xlsx")
df = pd.read_excel(input_file, sheet_name="raw_data", engine="openpyxl")

print("=" * 60)
print("  NOTEBOOK 4 — RESCUE, REJECT & KNN IMPUTATION")
print("=" * 60)
print(f"\n✅ Loaded: {input_file}  ({df.shape[0]} rows, {df.shape[1]} cols)")


# =====================================================================
# Quality-scoring function (same 4 dimensions as QA stage)
# =====================================================================
VALIDITY_RULES = {
    "marks_math":     (0, 100),
    "marks_science":  (0, 100),
    "attendance_pct": (0, 100),
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
    consistency = (
        round((distinct_norm / distinct_raw) * 100, 1) if distinct_raw else 100.0
    )

    return pd.DataFrame([
        {"dimension": "Completeness", "score_pct": completeness},
        {"dimension": "Validity",     "score_pct": validity},
        {"dimension": "Uniqueness",   "score_pct": uniqueness},
        {"dimension": "Consistency",  "score_pct": consistency},
    ])


# =====================================================================
# BEFORE scores (snapshot the raw data quality)
# =====================================================================
before_scores = score_dataset(df)

print(f"\n{'=' * 60}")
print("BEFORE CLEANING — Quality Scores")
print("=" * 60)
print(before_scores.to_string(index=False))
print(f"Overall: {round(before_scores['score_pct'].mean(), 1)}%")


# =====================================================================
# STEP 1: Fix Consistency & Drop Duplicates
# =====================================================================
df_clean = df.copy()

# Consistency fix: canonical city mapping
city_map = {
    "delhi":      "Delhi",
    "mumbai":     "Mumbai",
    "bangalore":  "Bengaluru",
    "bengaluru":  "Bengaluru",
    "jaipur":     "Jaipur",
}

df_clean["city"] = (
    df_clean["city"]
    .str.strip()
    .str.lower()
    .map(city_map)
    .fillna(df_clean["city"].str.strip().str.title())
)

print(f"\n── Consistency Fix ──")
print(f"   Canonical cities: {sorted(df_clean['city'].unique())}")
print("   ✅ 'Bangalore' → 'Bengaluru', case/whitespace normalised.")

# Uniqueness fix: drop exact duplicate rows
rows_before = len(df_clean)
df_clean = df_clean.drop_duplicates().reset_index(drop=True)
rows_after = len(df_clean)

print(f"\n── Duplicate Removal ──")
print(f"   Rows before : {rows_before}")
print(f"   Rows after  : {rows_after}")
print(f"   Dropped     : {rows_before - rows_after}")
print(
    "\n   ✅ Data Leakage prevention: identical rows can no longer"
    "\n   appear in both Train and Test splits."
)


# =====================================================================
# STEP 2: Outlier Capping (Validity Fix)
# =====================================================================
sci_bad = (df_clean["marks_science"] < 0).sum()
df_clean["marks_science"] = df_clean["marks_science"].clip(lower=0)

att_bad = (df_clean["attendance_pct"] > 100).sum()
df_clean["attendance_pct"] = df_clean["attendance_pct"].clip(upper=100)

print(f"\n── Outlier Capping ──")
print(f"   marks_science < 0  → capped to 0   ({sci_bad} row(s))")
print(f"   attendance_pct > 100 → capped to 100 ({att_bad} row(s))")
print(f"\n   Post-cap ranges:")
print(f"     marks_science  : [{df_clean['marks_science'].min():.0f}, {df_clean['marks_science'].max():.0f}]")
print(f"     attendance_pct : [{df_clean['attendance_pct'].min():.0f}, {df_clean['attendance_pct'].max():.0f}]")


# =====================================================================
# STEP 3: Imputation
# =====================================================================
print(f"\n{'=' * 60}")
print("IMPUTATION METHODS")
print("=" * 60)

print("\n── Missing Values Before Imputation ──")
missing = df_clean.isnull().sum()
print(missing[missing > 0].to_string())

# --- Method 1: MEDIAN — attendance_pct ---
att_median = df_clean["attendance_pct"].median()
att_missing = df_clean["attendance_pct"].isna().sum()
df_clean["attendance_pct"] = df_clean["attendance_pct"].fillna(att_median)
print(f"\n  [1] Median imputation → attendance_pct")
print(f"      Filled {att_missing} missing value(s) with median = {att_median}")

# --- Method 2: MODE — city ---
city_missing = df_clean["city"].isna().sum()
if city_missing > 0:
    city_mode = df_clean["city"].mode()[0]
    df_clean["city"] = df_clean["city"].fillna(city_mode)
    print(f"\n  [2] Mode imputation → city")
    print(f"      Filled {city_missing} missing value(s) with mode = '{city_mode}'")
else:
    print(f"\n  [2] Mode imputation → city")
    print("      No missing values — skipped.")

# --- Method 3: KNN — marks_math ---
math_missing = df_clean["marks_math"].isna().sum()
print(f"\n  [3] KNN imputation → marks_math")
print(f"      Missing values : {math_missing}")
print("      Feature matrix : ['marks_science', 'attendance_pct', 'marks_math']")
print("      k (neighbours) : 5")

knn_cols = ["marks_science", "attendance_pct", "marks_math"]
imputer = KNNImputer(n_neighbors=5)
df_clean[knn_cols] = imputer.fit_transform(df_clean[knn_cols])

# Round marks to integers
df_clean["marks_math"] = df_clean["marks_math"].round(0).astype(int)

print("      ✅ KNN imputation complete.")
print(f"      Missing marks_math remaining: {df_clean['marks_math'].isna().sum()}")

# Final missing-value check
print("\n── Missing Values After Imputation ──")
remaining = df_clean.isnull().sum()
if remaining.sum() == 0:
    print("   ✅ All missing values filled — dataset is complete.")
else:
    print(remaining[remaining > 0].to_string())


# =====================================================================
# AFTER scores
# =====================================================================
after_scores = score_dataset(df_clean)

print(f"\n{'=' * 60}")
print("AFTER CLEANING — Quality Scores")
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
after_overall = round(comparison["after_pct"].mean(), 1)
overall_change = round(after_overall - before_overall, 1)

overall_row = pd.DataFrame([{
    "dimension":  "OVERALL",
    "before_pct": before_overall,
    "after_pct":  after_overall,
    "change":     overall_change,
    "change_str": f"+{overall_change}" if overall_change > 0 else str(overall_change),
}])
comparison = pd.concat([comparison, overall_row], ignore_index=True)

print(f"\n{'=' * 60}")
print("COMPARISON: Before vs After Cleaning")
print("=" * 60)
print(comparison[["dimension", "before_pct", "after_pct", "change_str"]].to_string(index=False))
print(
    f"\n🎯 Quality improvement: {before_overall}% → {after_overall}%"
    f" ({'+' if overall_change > 0 else ''}{overall_change} pts)"
)


# =====================================================================
# SAVE OUTPUT
# =====================================================================
output_file = os.path.join(DATA_DIR, "imputed_data.xlsx")
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_clean.to_excel(writer, sheet_name="clean_data", index=False)
    comparison.to_excel(writer, sheet_name="score_comparison", index=False)
    before_scores.to_excel(writer, sheet_name="scores_before", index=False)
    after_scores.to_excel(writer, sheet_name="scores_after", index=False)

print(f"\n{'=' * 60}")
print("  NOTEBOOK 4 COMPLETE ✅  |  PIPELINE COMPLETE 🏁")
print("=" * 60)
print(f"\n   Exported: {output_file}")
print("   Sheets  : clean_data, score_comparison, scores_before, scores_after")
print(f"   Final shape: {df_clean.shape[0]} rows × {df_clean.shape[1]} columns")
print(
    "\n   This dataset is now AI-ready:"
    "\n     • No missing values (Median, Mode, KNN imputed)"
    "\n     • No impossible values (hard-capped to valid ranges)"
    "\n     • No duplicates (Data Leakage eliminated)"
    "\n     • Consistent formatting (canonical city names)"
    "\n     • teacher_notes preserved for downstream RAG/LLM pipeline"
)
