from typing import Any, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer, SimpleImputer
from backend.app.schemas.models import LogEntry


def impute_median(df: pd.DataFrame, column: str, **kwargs) -> Tuple[pd.DataFrame, LogEntry]:
    """Impute missing numeric values in a single column using the median."""
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="missing_values", action="impute_median", records_changed=0, status="skipped", details="Column not found")

    missing_count = int(df_copy[column].isna().sum())
    if missing_count == 0:
        return df_copy, LogEntry(column=column, issue="missing_values", action="impute_median", records_changed=0, status="skipped", details="No missing values")

    # Check if column is numeric; if not, fallback to mode imputation
    if not np.issubdtype(df_copy[column].dtype, np.number):
        # Attempt conversion
        numeric_test = pd.to_numeric(df_copy[column], errors="coerce")
        if numeric_test.notna().sum() > 0:
            df_copy[column] = numeric_test
        else:
            return impute_mode(df, column, **kwargs)

    median_val = df_copy[column].median()
    df_copy[column] = df_copy[column].fillna(median_val)

    return df_copy, LogEntry(
        column=column,
        issue="missing_values",
        action="impute_median",
        records_changed=missing_count,
        before_sample="NaN",
        after_sample=str(median_val),
        status="success",
        details=f"Imputed {missing_count} values with median ({median_val})",
    )


def impute_mean(df: pd.DataFrame, column: str, **kwargs) -> Tuple[pd.DataFrame, LogEntry]:
    """Impute missing numeric values in a single column using the mean."""
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="missing_values", action="impute_mean", records_changed=0, status="skipped", details="Column not found")

    missing_count = int(df_copy[column].isna().sum())
    if missing_count == 0:
        return df_copy, LogEntry(column=column, issue="missing_values", action="impute_mean", records_changed=0, status="skipped", details="No missing values")

    mean_val = float(df_copy[column].mean())
    df_copy[column] = df_copy[column].fillna(mean_val)

    return df_copy, LogEntry(
        column=column,
        issue="missing_values",
        action="impute_mean",
        records_changed=missing_count,
        before_sample="NaN",
        after_sample=str(round(mean_val, 2)),
        status="success",
        details=f"Imputed {missing_count} values with mean ({round(mean_val, 2)})",
    )


def impute_mode(df: pd.DataFrame, column: str, **kwargs) -> Tuple[pd.DataFrame, LogEntry]:
    """Impute missing values using the most frequent value (mode)."""
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="missing_values", action="impute_mode", records_changed=0, status="skipped", details="Column not found")

    missing_count = int(df_copy[column].isna().sum())
    if missing_count == 0:
        return df_copy, LogEntry(column=column, issue="missing_values", action="impute_mode", records_changed=0, status="skipped", details="No missing values")

    modes = df_copy[column].mode(dropna=True)
    mode_val = modes.iloc[0] if len(modes) > 0 else "Unknown"
    df_copy[column] = df_copy[column].fillna(mode_val)

    return df_copy, LogEntry(
        column=column,
        issue="missing_values",
        action="impute_mode",
        records_changed=missing_count,
        before_sample="NaN",
        after_sample=str(mode_val),
        status="success",
        details=f"Imputed {missing_count} values with mode ({mode_val})",
    )


def impute_constant(df: pd.DataFrame, column: str, fill_value: Any = 0, **kwargs) -> Tuple[pd.DataFrame, LogEntry]:
    """Impute missing values with a designated constant value."""
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="missing_values", action="impute_constant", records_changed=0, status="skipped", details="Column not found")

    missing_count = int(df_copy[column].isna().sum())
    if missing_count == 0:
        return df_copy, LogEntry(column=column, issue="missing_values", action="impute_constant", records_changed=0, status="skipped", details="No missing values")

    df_copy[column] = df_copy[column].fillna(fill_value)

    return df_copy, LogEntry(
        column=column,
        issue="missing_values",
        action="impute_constant",
        records_changed=missing_count,
        before_sample="NaN",
        after_sample=str(fill_value),
        status="success",
        details=f"Imputed {missing_count} values with constant ({fill_value})",
    )


def fill_unknown(df: pd.DataFrame, column: str, fill_value: str = "Unknown", **kwargs) -> Tuple[pd.DataFrame, LogEntry]:
    """Fill missing categorical values with 'Unknown' or designated label."""
    return impute_constant(df, column, fill_value=fill_value, **kwargs)


def impute_knn(df: pd.DataFrame, column: str, n_neighbors: int = 5, **kwargs) -> Tuple[pd.DataFrame, LogEntry]:
    """Impute missing numeric values using KNNImputer across all numeric columns."""
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="missing_values", action="impute_knn", records_changed=0, status="skipped", details="Column not found")

    missing_count = int(df_copy[column].isna().sum())
    if missing_count == 0:
        return df_copy, LogEntry(column=column, issue="missing_values", action="impute_knn", records_changed=0, status="skipped", details="No missing values")

    numeric_cols = df_copy.select_dtypes(include=np.number).columns.tolist()
    if not numeric_cols:
        return impute_median(df, column)

    imputer = KNNImputer(n_neighbors=min(n_neighbors, max(1, len(df_copy) - 1)))
    imputed_data = imputer.fit_transform(df_copy[numeric_cols])
    df_copy[numeric_cols] = imputed_data

    return df_copy, LogEntry(
        column=column,
        issue="missing_values",
        action="impute_knn",
        records_changed=missing_count,
        before_sample="NaN",
        after_sample=str(round(float(df_copy[column].mean()), 2)),
        status="success",
        details=f"KNN imputation applied using {min(n_neighbors, len(df_copy)-1)} neighbors",
    )
