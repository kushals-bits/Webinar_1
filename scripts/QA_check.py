import os
import pandas as pd
import numpy as np

# Resolve the data directory relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

# =====================================================================
# Quality Assessment — "report card" for the dataset
# Reads  : profiled_data.xlsx  (from Data_profiling.py)
# Writes : qa_checked_data.xlsx (input for next stage)
# =====================================================================

# --- Read input from previous stage ---
input_file = os.path.join(DATA_DIR, "profiled_data.xlsx")
df = pd.read_excel(input_file, sheet_name="raw_data", engine="openpyxl")
print(f"Loaded : {input_file}  ({df.shape[0]} rows, {df.shape[1]} cols)\n")


# =====================================================================
# 1. COMPLETENESS — fraction of values that are NOT missing
# =====================================================================
completeness_per_col = (1 - df.isnull().mean()) * 100
overall_completeness = round(completeness_per_col.mean(), 1)

print("=" * 55)
print("1. COMPLETENESS  (% non-missing)")
print("=" * 55)
print(completeness_per_col.round(1).to_string())
print(f"\n   Overall completeness: {overall_completeness}%")


# =====================================================================
# 2. VALIDITY — do values fall within allowed / sensible ranges?
# =====================================================================
# Define business rules as {column: (min, max)}
validity_rules = {
    "attendance_pct": (0, 100),
    "marks_math":     (0, 100),
    "marks_science":  (0, 100),
    "marks_english":  (0, 100),
}

validity_issues = []
for col, (lo, hi) in validity_rules.items():
    # skip NaN rows when checking range
    valid_mask = df[col].notna()
    out_of_range = df.loc[valid_mask, col].apply(lambda v: v < lo or v > hi)
    bad_count = out_of_range.sum()
    total_valid = valid_mask.sum()
    pct_valid = round((1 - bad_count / total_valid) * 100, 1) if total_valid else 100.0
    validity_issues.append({
        "column": col,
        "rule": f"{lo} <= value <= {hi}",
        "total_checked": total_valid,
        "invalid_count": int(bad_count),
        "validity_pct": pct_valid,
    })

validity_df = pd.DataFrame(validity_issues)
overall_validity = round(validity_df["validity_pct"].mean(), 1)

print(f"\n{'=' * 55}")
print("2. VALIDITY  (values within allowed range)")
print("=" * 55)
print(validity_df.to_string(index=False))
print(f"\n   Overall validity: {overall_validity}%")


# =====================================================================
# 3. UNIQUENESS — duplicate records that shouldn't exist
# =====================================================================
full_dup_count = df.duplicated().sum()
id_dup_count = df["student_id"].duplicated().sum()
uniqueness_score = round((1 - full_dup_count / len(df)) * 100, 1)

print(f"\n{'=' * 55}")
print("3. UNIQUENESS  (no unwarranted duplicates)")
print("=" * 55)
print(f"   Fully duplicate rows  : {full_dup_count}")
print(f"   Duplicate student_id  : {id_dup_count}")
print(f"   Uniqueness score      : {uniqueness_score}%")


# =====================================================================
# 4. CONSISTENCY — same real-world value written the same way
# =====================================================================
# Normalise: strip whitespace, title-case
city_raw = df["city"].dropna()
city_normalised = city_raw.str.strip().str.title()
distinct_raw = city_raw.nunique()
distinct_normalised = city_normalised.nunique()
inconsistency_count = distinct_raw - distinct_normalised
consistency_score = round((distinct_normalised / distinct_raw) * 100, 1) if distinct_raw else 100.0

# Build a mapping table showing which raw spellings collapse to the same value
consistency_map = (
    pd.DataFrame({"raw": city_raw, "normalised": city_normalised})
    .drop_duplicates()
    .sort_values("normalised")
    .reset_index(drop=True)
)

print(f"\n{'=' * 55}")
print("4. CONSISTENCY  (uniform representation)")
print("=" * 55)
print(f"   Column checked        : city")
print(f"   Distinct raw values   : {distinct_raw}")
print(f"   After normalisation   : {distinct_normalised}")
print(f"   Inconsistent spellings: {inconsistency_count}")
print(f"   Consistency score     : {consistency_score}%")
print("\n   Raw -> Normalised mapping:")
print(consistency_map.to_string(index=False))


# =====================================================================
# 5. ACCURACY — does the value reflect reality?
#    (conceptual flag; would need an external source to verify)
# =====================================================================
accuracy_flags = []
# Flag impossible attendance
acc_mask = df["attendance_pct"].notna() & (
    (df["attendance_pct"] < 0) | (df["attendance_pct"] > 100)
)
for idx in df.loc[acc_mask].index:
    accuracy_flags.append({
        "row": int(idx),
        "column": "attendance_pct",
        "value": df.loc[idx, "attendance_pct"],
        "flag": "Impossible (>100%); likely data-entry error",
    })
# Flag negative marks
for marks_col in ["marks_math", "marks_science", "marks_english"]:
    neg_mask = df[marks_col].notna() & (df[marks_col] < 0)
    for idx in df.loc[neg_mask].index:
        accuracy_flags.append({
            "row": int(idx),
            "column": marks_col,
            "value": df.loc[idx, marks_col],
            "flag": "Negative marks; verify with source records",
        })

accuracy_df = pd.DataFrame(accuracy_flags) if accuracy_flags else pd.DataFrame(
    columns=["row", "column", "value", "flag"]
)

print(f"\n{'=' * 55}")
print("5. ACCURACY  (qualitative flags — needs external verification)")
print("=" * 55)
if accuracy_df.empty:
    print("   No accuracy flags raised.")
else:
    print(accuracy_df.to_string(index=False))


# =====================================================================
# OVERALL QUALITY SCORECARD
# =====================================================================
scorecard = pd.DataFrame([
    {"dimension": "Completeness", "score_pct": overall_completeness,
     "description": "Fraction of non-missing values"},
    {"dimension": "Validity", "score_pct": overall_validity,
     "description": "Values within allowed ranges"},
    {"dimension": "Uniqueness", "score_pct": uniqueness_score,
     "description": "No unwarranted duplicate rows"},
    {"dimension": "Consistency", "score_pct": consistency_score,
     "description": "Uniform representation of same entity"},
    {"dimension": "Accuracy", "score_pct": np.nan,
     "description": "Qualitative — needs external verification"},
])
# Overall (excluding Accuracy which is qualitative)
quantitative = scorecard["score_pct"].dropna()
overall_quality = round(quantitative.mean(), 1)

print(f"\n{'=' * 55}")
print("OVERALL QUALITY SCORECARD")
print("=" * 55)
print(scorecard.to_string(index=False))
print(f"\n   Overall quality score (excl. Accuracy): {overall_quality}%")


# =====================================================================
# SAVE OUTPUT FOR NEXT STAGE
# =====================================================================
output_file = os.path.join(DATA_DIR, "qa_checked_data.xlsx")
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="raw_data", index=False)
    scorecard.to_excel(writer, sheet_name="scorecard", index=False)
    validity_df.to_excel(writer, sheet_name="validity_detail", index=False)
    consistency_map.to_excel(writer, sheet_name="consistency_map", index=False)
    accuracy_df.to_excel(writer, sheet_name="accuracy_flags", index=False)

print(f"\nSaved : {output_file}")
print("Sheets: raw_data, scorecard, validity_detail, consistency_map, accuracy_flags")
