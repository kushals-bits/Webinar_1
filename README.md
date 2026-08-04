# Webinar 1 — Data Quality Pipeline

A hands-on data quality pipeline that walks through the full lifecycle of creating, profiling, validating, and cleaning a student dataset using Python and Pandas.

## Project Structure

```
Data_creation/
├── README.md
├── session_notes_4th_August.md
├── .gitignore
├── data/                         # All Excel data files
│   ├── student_data.xlsx         # Raw generated data (Stage 1 output)
│   ├── profiled_data.xlsx        # Profiled data + summary (Stage 2 output)
│   ├── qa_checked_data.xlsx      # QA scorecard + flagged issues (Stage 3 output)
│   └── imputed_data.xlsx         # Cleaned & imputed data (Stage 4 output)
└── scripts/                      # All Python scripts
    ├── data_create.py            # Stage 1: Generate synthetic student data
    ├── Data_profiling.py         # Stage 2: Profile and summarise the dataset
    ├── QA_check.py               # Stage 3: Quality assessment (5 dimensions)
    └── imputation_data.py        # Stage 4: Clean, impute, and compare scores
```

## Pipeline Stages

| Stage | Script | Input | Output | Description |
|-------|--------|-------|--------|-------------|
| 1 | `data_create.py` | — | `student_data.xlsx` | Generates 40 student records with intentional data quality issues (missing values, duplicates, invalid entries, inconsistent city names) |
| 2 | `Data_profiling.py` | `student_data.xlsx` | `profiled_data.xlsx` | Profiles the dataset — data types, missing values, unique value counts, and statistical summaries |
| 3 | `QA_check.py` | `profiled_data.xlsx` | `qa_checked_data.xlsx` | Scores the dataset on 5 quality dimensions: Completeness, Validity, Uniqueness, Consistency, and Accuracy |
| 4 | `imputation_data.py` | `qa_checked_data.xlsx` | `imputed_data.xlsx` | Cleans and imputes using 3 methods (Median, Mode, KNN) and produces before/after quality comparison |

## Quality Dimensions Assessed

- **Completeness** — % of non-missing values
- **Validity** — values within allowed ranges (e.g., marks 0–100)
- **Uniqueness** — no unwarranted duplicate rows
- **Consistency** — uniform representation (e.g., "delhi", "Delhi", "delhi " → "Delhi")
- **Accuracy** — qualitative flags for suspicious values

## Prerequisites

```bash
pip install pandas numpy scikit-learn openpyxl
```

## How to Run

Run the scripts in order from the project root:

```bash
python scripts/data_create.py
python scripts/Data_profiling.py
python scripts/QA_check.py
python scripts/imputation_data.py
```

Each script reads from `data/` and writes its output back to `data/`, so the pipeline is fully self-contained.

## Tech Stack

- **Python 3**
- **Pandas** — data manipulation and profiling
- **NumPy** — random data generation and numeric operations
- **scikit-learn** — KNN imputation
- **openpyxl** — Excel read/write