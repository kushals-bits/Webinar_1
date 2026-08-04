# pip install pandas numpy scikit-learn  (if not already installed)

import os
import pandas as pd
import numpy as np

# Resolve the data directory relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

np.random.seed(42)
n = 40
 
data = {
    "student_id": range(1, n + 1),
    "name": [f"Student_{i}" for i in range(1, n + 1)],
    "class": np.random.choice(["6A", "6B", "7A", "7B"], n),
    "gender": np.random.choice(["M", "F"], n),
    "attendance_pct": np.random.randint(55, 100, n).astype(float),
    "marks_math": np.random.randint(30, 100, n).astype(float),
    "marks_science": np.random.randint(30, 100, n).astype(float),
    "marks_english": np.random.randint(30, 100, n).astype(float),
    "city": np.random.choice(
        ["Delhi", "delhi ", "New Delhi", "Mumbai", "mumbai", "Jaipur"], n),
    "admission_date": pd.date_range("2021-04-01", periods=n, freq="9D"),
}
df = pd.DataFrame(data)
 
# --- inject realistic problems, on purpose, so we have something to find ---
missing_idx = np.random.choice(df.index, 6, replace=False)
df.loc[missing_idx[:3], "marks_math"] = np.nan          # missing marks
df.loc[missing_idx[3:], "attendance_pct"] = np.nan       # missing attendance
df.loc[2, "attendance_pct"] = 141                        # impossible value (>100%)
df.loc[5, "marks_science"] = -10                         # impossible value (<0)
df = pd.concat([df, df.iloc[[7]]], ignore_index=True)    # duplicate row
 
output_file = os.path.join(DATA_DIR, "student_data.xlsx")
df.to_excel(output_file, index=False, engine="openpyxl")

print(f"Shape : {df.shape}")
print(f"Saved : {output_file}")
print(df.head(10))
