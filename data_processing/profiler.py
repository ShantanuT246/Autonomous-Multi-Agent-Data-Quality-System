
import numpy as np
import pandas as pd


def profile_dataset(df: pd.DataFrame) -> dict:
    """
    Analyze a dataset and return a structured data-quality profile.
    The input DataFrame is not modified.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    if df.empty:
        raise ValueError("The dataset is empty.")

    total_cells = df.shape[0] * df.shape[1]
    missing_by_column = df.isna().sum()

    numeric_df = df.select_dtypes(include=np.number)
    numeric_summary = {}

    for column in numeric_df.columns:
        values = numeric_df[column].dropna().to_numpy(dtype=float)
        finite_values = values[np.isfinite(values)]

        numeric_summary[column] = {
            "mean": (
                float(np.mean(finite_values))
                if len(finite_values) else None
            ),
            "median": (
                float(np.median(finite_values))
                if len(finite_values) else None
            ),
            "std": (
                float(np.std(finite_values))
                if len(finite_values) else None
            ),
            "non_finite_values": int(
                np.sum(~np.isfinite(values))
            ),
        }

    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": df.columns.tolist(),
        "data_types": {
            col: str(dtype)
            for col, dtype in df.dtypes.items()
        },
        "missing_values": {
            col: int(count)
            for col, count in missing_by_column.items()
        },
        "total_missing": int(missing_by_column.sum()),
        "missing_percentage": (
            round(100 * int(missing_by_column.sum()) / total_cells, 2)
        ),
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_summary": numeric_summary,
        "unique_values": {
            col: int(df[col].nunique(dropna=True))
            for col in df.columns
        },
    }
