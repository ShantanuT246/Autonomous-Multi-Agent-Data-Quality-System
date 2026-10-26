# Data Processing Module

## Overview

The `data_processing` module is responsible for analyzing dataset quality, preprocessing data, and generating visualizations for the Autonomous Multi-Agent Data Quality System.

It uses NumPy, Pandas, Scikit-learn, and Matplotlib to support dataset profiling, missing-value handling, transformation logging, and before-and-after quality comparisons.

## Module Structure

```text
data_processing/
├── __init__.py
├── profiler.py
├── preprocessing.py
├── visualizer.py
├── pipeline.py
└── tests/
    ├── test_profiler.py
    ├── test_preprocessing.py
    └── test_visualizer.py
```

## Components

### 1. `profiler.py`

Analyzes a tabular dataset and generates a data-quality profile.

**Responsibilities:**
- Identify the number of rows and columns.
- Report column names and data types.
- Calculate missing-value counts and percentages.
- Count duplicate rows and unique values.
- Calculate numerical statistics, including mean, median, and standard deviation.
- Identify non-finite numerical values.

**Main function:** `profile_dataset(df)`

### 2. `preprocessing.py`

Applies predefined preprocessing operations to a copy of the input dataset.

**Responsibilities:**
- Impute missing numerical values using the median.
- Impute missing categorical values using the most frequent value.
- Normalize whitespace and capitalization in supported text columns.
- Record the transformations performed in a cleaning log.
- Preserve the original DataFrame.

**Main function:** `clean_dataset(df)`

### 3. `visualizer.py`

Generates visual comparisons of dataset quality before and after preprocessing.

**Responsibilities:**
- Compare missing-value counts.
- Compare duplicate-row counts.
- Generate and save Matplotlib charts.
- Return quality metrics and chart file paths.

**Main function:** `generate_quality_report(original, cleaned, output_dir)`

### 4. `pipeline.py`

Coordinates the data-processing workflow.

**Responsibilities:**
- Profile the original dataset.
- Execute preprocessing.
- Profile the cleaned dataset.
- Generate quality-comparison charts.
- Save the cleaned dataset as a CSV file.
- Return profiles, transformation logs, and output paths.

**Main function:** `run_pipeline(df, output_dir)`

## Technology Stack

- **Python:** Core implementation.
- **Pandas:** Tabular data manipulation and profiling.
- **NumPy:** Numerical statistics and non-finite value detection.
- **Scikit-learn:** Missing-value imputation.
- **Matplotlib:** Before-and-after quality visualizations.
- **pytest:** Automated testing.

## Setup

From the repository root, activate your existing virtual environment and install the required packages if they are not already installed:

```bash
python -m pip install numpy pandas scikit-learn matplotlib pytest
```

## Running the Tests

Execute the following command from the repository root:

```bash
python -m pytest data_processing/tests -v
```

The tests cover dataset profiling, preprocessing, and visualization.

## Workflow

1. Receive a Pandas DataFrame.
2. Analyze the original dataset.
3. Apply the configured preprocessing strategies.
4. Analyze the cleaned dataset.
5. Generate before-and-after quality charts.
6. Save the cleaned dataset and return the results.

## Current Limitations (and Backend Agent System Resolution)

- Baseline `data_processing` uses predefined, linear strategies.
- **Resolved in Backend Agent System (`backend/`):**
  - **Duplicate removal:** Handled via deterministic `drop_duplicates` with subset configuration and audit logging.
  - **Outlier handling:** Detected via IQR/Z-score and safely winsorized via `clip_outliers`.
  - **Granular per-column control:** Imputation (median, mean, mode, constant, KNN) and casing are applied per column on demand.
  - **Type casting & Unit normalization:** Strings like `$1,200` and units like `0.88 lbs` are dynamically normalized.
  - **Closed-vocabulary LangGraph self-correction loop:** Enforces Pydantic safety guardrails, row-loss bounds, and rollback protection.

## Output Artifacts

The pipeline can generate:

- `cleaned_dataset.csv`
- `missing_values.png`
- `duplicate_rows.png`

These artifacts are saved in the configured output directory, which defaults to `reports/`.

## Testing Status

The three module tests have passed in the current development environment. Run the test command above to verify the latest code.
