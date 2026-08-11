# pip install pandas numpy scikit-learn openpyxl  (if not already installed)

import os
import pandas as pd
import numpy as np

# Resolve the data directory relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

np.random.seed(42)
n = 40

# ---------------------------------------------------------------------------
# Teacher notes — unstructured text that a downstream RAG pipeline would
# embed and index.  Varied in length, tone, and vocabulary to make future
# NLP exercises non-trivial.
# ---------------------------------------------------------------------------
TEACHER_NOTES_POOL = [
    "Excellent problem-solver. Consistently finishes assignments ahead of schedule and helps peers.",
    "Struggles with algebra but shows strong effort. Needs additional practice on quadratic equations.",
    "Frequently absent. When present, participates actively but misses too many foundational lessons.",
    "Top performer in science labs. Written exam scores do not reflect practical ability.",
    "Quiet in class but produces high-quality written work. May benefit from oral presentation practice.",
    "Disruptive behavior noted in Q2. Improvement observed after parent-teacher meeting in March.",
    "Strong in both math and science. Recommended for the advanced enrichment program next semester.",
    "Average performance across subjects. No major concerns but could be more engaged in group work.",
    "Exceptional creative writing skills. Below average in quantitative subjects — consider tutoring.",
    "Transferred mid-year from another school. Still adapting to the curriculum pace.",
    "Consistently late to morning classes. Academic performance drops in first-period subjects.",
    "Shows aptitude for data analysis projects. Completed the optional statistics module independently.",
    "Needs support with reading comprehension which impacts performance across all subjects.",
    "Highly motivated self-learner. Asks insightful questions that push classroom discussions forward.",
    "Performance declined after mid-term. Follow-up with school counselor recommended.",
]

data = {
    "student_id": range(1, n + 1),
    "marks_math": np.random.randint(30, 100, n).astype(float),
    "marks_science": np.random.randint(30, 100, n).astype(float),
    "attendance_pct": np.random.randint(55, 100, n).astype(float),
    "city": np.random.choice(
        ["Delhi", "delhi ", "Mumbai", "mumbai",
         "Bangalore", "Bengaluru", "bangalore ", "Jaipur"], n
    ),
    "teacher_notes": np.random.choice(TEACHER_NOTES_POOL, n),
}

df = pd.DataFrame(data)

# ---------------------------------------------------------------------------
# Inject realistic problems, on purpose, so we have something to find
# ---------------------------------------------------------------------------
missing_idx = np.random.choice(df.index, 6, replace=False)
df.loc[missing_idx[:3], "marks_math"] = np.nan           # missing marks
df.loc[missing_idx[3:], "attendance_pct"] = np.nan        # missing attendance
df.loc[5, "marks_science"] = -10                          # impossible value (<0)
df.loc[2, "attendance_pct"] = 141                         # impossible value (>100%)
df = pd.concat([df, df.iloc[[7, 23]]], ignore_index=True) # duplicate rows

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
output_file = os.path.join(DATA_DIR, "student_data.xlsx")
df.to_excel(output_file, index=False, engine="openpyxl")

print("=" * 60)
print("  NOTEBOOK 1 — THE GENERATOR")
print("=" * 60)
print(f"\n✅ Base dataset created: {df.shape[0]} rows × {df.shape[1]} columns")
print(f"   Columns: {list(df.columns)}")
print(f"\n── Injected Defects ──")
print(f"   Missing marks_math      : {df['marks_math'].isna().sum()}")
print(f"   Missing attendance_pct   : {df['attendance_pct'].isna().sum()}")
print(f"   marks_science < 0        : {(df['marks_science'] < 0).sum()}")
print(f"   attendance_pct > 100     : {(df['attendance_pct'] > 100).sum()}")
print(f"   Exact duplicate rows     : {df.duplicated().sum()}")
print(f"   Unique city spellings    : {df['city'].nunique()} → {sorted(df['city'].unique())}")
print(f"\n✅ Saved: {output_file}")
print(df.head(10))
