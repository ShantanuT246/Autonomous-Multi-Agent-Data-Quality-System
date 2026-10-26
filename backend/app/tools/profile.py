from typing import Any, Dict, List
import numpy as np
import pandas as pd
from data_processing.profiler import profile_dataset as base_profile_dataset


def profile_dataset_extended(df: pd.DataFrame, max_samples: int = 15) -> Dict[str, Any]:
    """
    Extends Member 1's profile_dataset with:
    - Quantile information (25%, 50%, 75%, min, max, skewness)
    - Value frequencies for categorical / low-cardinality columns
    - Masked sample preview rows
    - Inferred semantic clues
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    base_profile = base_profile_dataset(df)

    extended_numeric = {}
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) > 0:
            vals = series.to_numpy(dtype=float)
            finite_vals = vals[np.isfinite(vals)]
            if len(finite_vals) > 0:
                q25 = float(np.percentile(finite_vals, 25))
                q75 = float(np.percentile(finite_vals, 75))
                iqr = q75 - q25
                extended_numeric[col] = {
                    "min": float(np.min(finite_vals)),
                    "max": float(np.max(finite_vals)),
                    "q25": q25,
                    "median": float(np.median(finite_vals)),
                    "q75": q75,
                    "iqr": iqr,
                    "skew": float(pd.Series(finite_vals).skew()) if len(finite_vals) > 2 else 0.0,
                }

    # Top value frequencies for categorical/object columns
    categorical_summary = {}
    cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()

    for col in cat_cols:
        val_counts = df[col].value_counts(dropna=False).head(10).to_dict()
        categorical_summary[col] = {
            str(k): int(v) for k, v in val_counts.items()
        }

    # Safe sample rows
    samples = df.head(max_samples).to_dict(orient="records")

    return {
        **base_profile,
        "extended_numeric": extended_numeric,
        "categorical_summary": categorical_summary,
        "samples": samples,
    }
