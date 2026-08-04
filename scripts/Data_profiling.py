import os
import pandas as pd

# Resolve the data directory relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

# --- Read input file from previous stage ---
input_file = os.path.join(DATA_DIR, "student_data.xlsx")
df = pd.read_excel(input_file, engine="openpyxl")
print(f"Loaded : {input_file}  ({df.shape[0]} rows, {df.shape[1]} cols)")

# --- Shape and structure ---
print("\nRows, Columns:", df.shape)
print()
print(df.dtypes)
 
# --- Statistical summary of numeric columns ---
print(df.describe())
 
# --- Missing values per column ---
print(df.isnull().sum())
 
# --- Unique values per column (useful for spotting messy text like 'city') ---
for col in df.select_dtypes(include="object").columns:
    print(f"\n{col} -> {df[col].nunique()} unique values")
    print(df[col].unique())
 
# --- One-shot profiling summary function students can reuse on any dataset ---
def profile_dataset(data: pd.DataFrame) -> pd.DataFrame:
    summary = pd.DataFrame({
        "dtype": data.dtypes,
        "missing_count": data.isnull().sum(),
        "missing_pct": (data.isnull().mean() * 100).round(1),
        "unique_values": data.nunique(),
    })
    return summary
 
profile = profile_dataset(df)
print("\n--- Profiling Summary ---")
print(profile)

# --- Save profiled data and summary to Excel for next stage ---
output_file = os.path.join(DATA_DIR, "profiled_data.xlsx")
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="raw_data", index=False)
    profile.to_excel(writer, sheet_name="profile_summary")

print(f"\nSaved : {output_file}")
