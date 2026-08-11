import os
import pandas as pd
import numpy as np

# Resolve the data directory relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

# =====================================================================
# Data Profiling & The LLM Defense Line
# Reads  : student_data.xlsx
# Writes : profiled_data.xlsx (raw_data sheet + profile_summary sheet)
#
# ARCHITECTURAL NOTE — Why Tabular Cleaning Is the LLM's First Line of Defense:
# -------------------------------------------------------------------------------
# The `teacher_notes` column contains unstructured text — exactly the kind
# of data an enterprise RAG pipeline would embed into a Vector Database.
# But the retriever also pulls surrounding structured metadata as context.
# If that metadata says attendance_pct = 141 or marks_science = −10, the
# LLM treats those as ground truth and hallucinates around impossible facts.
# This tabular cleaning pipeline is a MANDATORY upstream gate: no row should
# reach the embedding layer until its structured columns are validated.
# =====================================================================

# --- Read input from previous stage ---
input_file = os.path.join(DATA_DIR, "student_data.xlsx")
df = pd.read_excel(input_file, engine="openpyxl")

print("=" * 60)
print("  NOTEBOOK 2 — DATA PROFILING & THE LLM DEFENSE LINE")
print("=" * 60)
print(f"\n✅ Loaded: {input_file}  ({df.shape[0]} rows, {df.shape[1]} cols)")

# --- Structure & types ---
print("\n── DataFrame .info() ──")
df.info()

print("\n── Data Types ──")
print(df.dtypes)

# --- Statistical summary ---
print("\n── Statistical Summary (.describe()) ──")
print(df.describe().to_string())

print(
    "\n📌 Look at the min/max rows above:"
    "\n   • marks_science min = -10  → impossible (valid range: 0–100)"
    "\n   • attendance_pct max = 141  → impossible (valid range: 0–100)"
)

# --- Missing values ---
print("\n── Missing Values ──")
missing = df.isnull().sum()
missing_pct = (df.isnull().mean() * 100).round(1)
missing_report = pd.DataFrame({"count": missing, "pct": missing_pct})
print(missing_report[missing_report["count"] > 0].to_string())
print(f"\n   Overall completeness: {(1 - df.isnull().mean().mean()) * 100:.1f}%")

# --- Unique values in text columns ---
print("\n── Unique Values (text columns) ──")
for col in df.select_dtypes(include="object").columns:
    print(f"\n   {col} → {df[col].nunique()} unique values")
    print(f"   {sorted(df[col].dropna().unique())}")

# =====================================================================
# Kurtosis — the pipeline circuit breaker
#
# ARCHITECTURAL NOTE:
# In a production pipeline (Airflow, Dagster, Prefect), high Kurtosis
# (|k| > 3, leptokurtic) signals extreme outliers in the tails.
# The pipeline's branching logic should AUTOMATICALLY switch the
# imputation strategy from Mean to Median to prevent outlier
# contamination across imputed cells.
# =====================================================================
att_kurtosis = df["attendance_pct"].kurtosis()
att_mean = df["attendance_pct"].mean()
att_median = df["attendance_pct"].median()

print("\n── Kurtosis Analysis: attendance_pct ──")
print(f"   Kurtosis : {att_kurtosis:.4f}")
print(f"   Mean     : {att_mean:.2f}")
print(f"   Median   : {att_median:.2f}")
print(f"   Delta    : {abs(att_mean - att_median):.2f} (Mean − Median gap)")

if abs(att_kurtosis) > 3:
    print(
        "\n⚠️  CIRCUIT BREAKER TRIGGERED: Kurtosis > 3"
        "\n   The distribution is leptokurtic — extreme outliers detected."
        "\n   Pipeline decision: ABANDON Mean → FORCE Median imputation."
    )
else:
    print(
        "\n✅ Kurtosis ≤ 3 — distribution tails are manageable."
        f"\n   However, the Mean/Median gap of {abs(att_mean - att_median):.2f}"
        "\n   still suggests skew. Median remains the safer imputation choice."
    )

print(
    "\n🔀 In production, this Kurtosis check would be an Airflow BranchPythonOperator"
    "\n   that routes to 'task_impute_median' or 'task_impute_mean' automatically."
)

# --- Reusable profiling summary ---
def profile_dataset(data: pd.DataFrame) -> pd.DataFrame:
    """One-shot profiling summary reusable on any DataFrame."""
    return pd.DataFrame({
        "dtype": data.dtypes,
        "missing_count": data.isnull().sum(),
        "missing_pct": (data.isnull().mean() * 100).round(1),
        "unique_values": data.nunique(),
    })


profile = profile_dataset(df)
print("\n── Profiling Summary ──")
print(profile.to_string())

# --- Export ---
output_file = os.path.join(DATA_DIR, "profiled_data.xlsx")
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="raw_data", index=False)
    profile.to_excel(writer, sheet_name="profile_summary")

print(f"\n✅ Saved: {output_file}")
print("   Sheets: raw_data, profile_summary")
