import os
import pandas as pd
import numpy as np

# Resolve the data directory relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

# =====================================================================
# QA Checks, Thresholds & Data Leakage
# Reads  : profiled_data.xlsx  (raw_data sheet)
# Writes : qa_checked_data.xlsx
#
# ARCHITECTURAL NOTE — Consistency ≠ Uniqueness:
# -----------------------------------------------------------------------
# Consistency is a FORMATTING problem: same entity encoded differently
# ('Bangalore' vs 'Bengaluru' vs 'bangalore ').  Fix: canonical mapping.
#
# Uniqueness is an ENTITY RESOLUTION problem: same event appears more
# than once as an exact-duplicate row.  Fix: drop_duplicates().
#
# Failing to dedup before a Train/Test split causes DATA LEAKAGE —
# identical observations in both partitions inflate validation metrics
# and produce models that collapse in production (the Accuracy Paradox).
#
# Always fix Consistency BEFORE Uniqueness: normalising labels first
# may reveal duplicates hidden by formatting mismatches.
# =====================================================================

# --- Read input from previous stage ---
input_file = os.path.join(DATA_DIR, "profiled_data.xlsx")
df = pd.read_excel(input_file, sheet_name="raw_data", engine="openpyxl")

print("=" * 60)
print("  NOTEBOOK 3 — QA CHECKS, THRESHOLDS & DATA LEAKAGE")
print("=" * 60)
print(f"\n✅ Loaded: {input_file}  ({df.shape[0]} rows, {df.shape[1]} cols)")


# =====================================================================
# 1. COMPLETENESS — fraction of values that are NOT missing
# =====================================================================
completeness_per_col = (1 - df.isnull().mean()) * 100
overall_completeness = round(completeness_per_col.mean(), 1)

print("\n" + "=" * 55)
print("1. COMPLETENESS  (% non-missing)")
print("=" * 55)
print(completeness_per_col.round(1).to_string())
print(f"\n   Overall completeness: {overall_completeness}%")


# =====================================================================
# 2. VALIDITY — explicit boolean threshold checks
# =====================================================================
validity_rules = {
    "marks_math":     (0, 100),
    "marks_science":  (0, 100),
    "attendance_pct": (0, 100),
}

validity_issues = []
print(f"\n{'=' * 55}")
print("2. VALIDITY  (values within allowed range)")
print("=" * 55)

for col, (lo, hi) in validity_rules.items():
    valid_mask = df[col].notna()
    too_low = df.loc[valid_mask, col] < lo
    too_high = df.loc[valid_mask, col] > hi
    bad_count = too_low.sum() + too_high.sum()
    total = valid_mask.sum()
    pct_valid = round((1 - bad_count / total) * 100, 1) if total else 100.0

    validity_issues.append({
        "column": col,
        "rule": f"{lo} <= value <= {hi}",
        "checked": total,
        "invalid": int(bad_count),
        "validity_pct": pct_valid,
    })

    # Print actual offending rows
    offenders = df.loc[valid_mask & (too_low | too_high), ["student_id", col]]
    if not offenders.empty:
        print(f"\n   ⚠️  {col} — {bad_count} violation(s):")
        print(f"   {offenders.to_string(index=False)}")

validity_df = pd.DataFrame(validity_issues)
overall_validity = round(validity_df["validity_pct"].mean(), 1)

print(f"\n{validity_df.to_string(index=False)}")
print(f"\n   Overall validity: {overall_validity}%")


# =====================================================================
# 3. UNIQUENESS — duplicate detection (Data Leakage risk)
# =====================================================================
full_dup_mask = df.duplicated(keep=False)
full_dup_count = df.duplicated().sum()
id_dup_count = df["student_id"].duplicated().sum()
uniqueness_score = round((1 - full_dup_count / len(df)) * 100, 1)

print(f"\n{'=' * 55}")
print("3. UNIQUENESS  (no unwarranted duplicates)")
print("=" * 55)
print(f"   Fully duplicate rows   : {full_dup_count}")
print(f"   Duplicate student_ids  : {id_dup_count}")
print(f"   Uniqueness score       : {uniqueness_score}%")

if full_dup_count > 0:
    print(f"\n   ⚠️  Duplicate rows (all copies shown):")
    dup_rows = df[full_dup_mask].sort_values("student_id")
    print(dup_rows[["student_id", "marks_math", "marks_science",
                     "attendance_pct", "city"]].to_string(index=True))
    print(
        "\n   🚨 DATA LEAKAGE RISK: These identical rows would leak into both"
        "\n   Train and Test partitions, inflating validation accuracy."
    )


# =====================================================================
# 4. CONSISTENCY — formatting analysis
# =====================================================================
city_raw = df["city"].dropna()
city_normalised = city_raw.str.strip().str.title()

distinct_raw = city_raw.nunique()
distinct_normalised = city_normalised.nunique()
inconsistency_count = distinct_raw - distinct_normalised
consistency_score = (
    round((distinct_normalised / distinct_raw) * 100, 1) if distinct_raw else 100.0
)

consistency_map = (
    pd.DataFrame({"raw": city_raw, "normalised": city_normalised})
    .drop_duplicates()
    .sort_values("normalised")
    .reset_index(drop=True)
)

print(f"\n{'=' * 55}")
print("4. CONSISTENCY  (uniform representation)")
print("=" * 55)
print(f"   Column checked         : city")
print(f"   Distinct raw values    : {distinct_raw}")
print(f"   After normalisation    : {distinct_normalised}")
print(f"   Inconsistent spellings : {inconsistency_count}")
print(f"   Consistency score      : {consistency_score}%")
print(f"\n   Raw → Normalised mapping:")
print(consistency_map.to_string(index=False))
print(
    "\n   📌 Note: 'Bangalore' and 'Bengaluru' are the SAME city."
    "\n   Simple title-casing won't catch this — we need a canonical"
    "\n   mapping dictionary (applied in Notebook 4)."
)


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
])

overall_quality = round(scorecard["score_pct"].mean(), 1)

print(f"\n{'=' * 55}")
print("OVERALL QUALITY SCORECARD")
print("=" * 55)
print(scorecard.to_string(index=False))
print(f"\n   Overall quality score: {overall_quality}%")


# =====================================================================
# SAVE OUTPUT
# =====================================================================
output_file = os.path.join(DATA_DIR, "qa_checked_data.xlsx")
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="raw_data", index=False)
    scorecard.to_excel(writer, sheet_name="scorecard", index=False)
    validity_df.to_excel(writer, sheet_name="validity_detail", index=False)
    consistency_map.to_excel(writer, sheet_name="consistency_map", index=False)

print(f"\n✅ Saved: {output_file}")
print("   Sheets: raw_data, scorecard, validity_detail, consistency_map")
