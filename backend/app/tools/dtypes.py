import re
from typing import Optional, Tuple
import numpy as np
import pandas as pd
from backend.app.schemas.models import LogEntry


def cast_dtype(
    df: pd.DataFrame,
    column: str,
    target_dtype: str = "float",
    **kwargs,
) -> Tuple[pd.DataFrame, LogEntry]:
    """
    Safely cast column to target dtype:
    - For numeric (float/int): cleans currency symbols ('$', '€', '£', 'USD'), commas,
      parentheses negatives, and sets sentinel strings ('N/A', 'nan', 'null', '-') to NaN.
    - For boolean: maps 'true'/'false', 'yes'/'no', '1'/'0', 't'/'f'.
    - For string: casts to string format.
    """
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="wrong_dtype", action="cast_dtype", records_changed=0, status="skipped", details="Column not found")

    original = df_copy[column].copy()
    target = target_dtype.lower()

    if target in ["float", "float64", "number", "numeric"]:
        def clean_num(val):
            if pd.isna(val):
                return np.nan
            if isinstance(val, (int, float)):
                return float(val)
            s = str(val).strip()
            if s.lower() in ["n/a", "na", "nan", "null", "none", "", "-", "unknown"]:
                return np.nan
            # Check for negative in parens e.g. (100) -> -100
            is_negative = False
            if s.startswith("(") and s.endswith(")"):
                is_negative = True
                s = s[1:-1]
            # Strip currency symbols and letters like USD
            s = re.sub(r"[^\d.-]", "", s)
            try:
                num = float(s)
                return -num if is_negative else num
            except ValueError:
                return np.nan

        df_copy[column] = df_copy[column].map(clean_num)

    elif target in ["int", "int64", "integer"]:
        def clean_int(val):
            if pd.isna(val):
                return np.nan
            try:
                num = float(re.sub(r"[^\d.-]", "", str(val).strip()))
                return int(num)
            except (ValueError, TypeError):
                return np.nan

        df_copy[column] = df_copy[column].map(clean_int)

    elif target in ["bool", "boolean"]:
        def clean_bool(val):
            if pd.isna(val):
                return np.nan
            s = str(val).strip().lower()
            if s in ["true", "1", "yes", "y", "t"]:
                return True
            if s in ["false", "0", "no", "n", "f"]:
                return False
            return np.nan

        df_copy[column] = df_copy[column].map(clean_bool)

    elif target in ["str", "string"]:
        df_copy[column] = df_copy[column].astype(str)

    # Count how many changed
    changed = int((original.fillna("<NA>") != df_copy[column].fillna("<NA>")).sum())
    sample_before = None
    sample_after = None
    if changed > 0:
        mask = original.fillna("<NA>") != df_copy[column].fillna("<NA>")
        sample_before = str(original[mask].iloc[0])
        sample_after = str(df_copy[column][mask].iloc[0])

    return df_copy, LogEntry(
        column=column,
        issue="wrong_dtype",
        action="cast_dtype",
        records_changed=changed,
        before_sample=sample_before,
        after_sample=sample_after,
        status="success",
        details=f"Safely converted column to {target_dtype} ({changed} records formatted)",
    )


def parse_dates(
    df: pd.DataFrame,
    column: str,
    target_format: str = "%Y-%m-%d",
    **kwargs,
) -> Tuple[pd.DataFrame, LogEntry]:
    """
    Parse mixed date formats into standardized ISO date strings.
    """
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="invalid_format", action="parse_dates", records_changed=0, status="skipped", details="Column not found")

    original = df_copy[column].copy()

    # Use pandas to_datetime with flexible parsing
    parsed_series = pd.to_datetime(df_copy[column], errors="coerce", format="mixed")
    df_copy[column] = parsed_series.dt.strftime(target_format)

    changed = int((original.fillna("<NA>") != df_copy[column].fillna("<NA>")).sum())
    sample_before = None
    sample_after = None
    if changed > 0:
        mask = original.fillna("<NA>") != df_copy[column].fillna("<NA>")
        sample_before = str(original[mask].iloc[0])
        sample_after = str(df_copy[column][mask].iloc[0])

    return df_copy, LogEntry(
        column=column,
        issue="invalid_format",
        action="parse_dates",
        records_changed=changed,
        before_sample=sample_before,
        after_sample=sample_after,
        status="success",
        details=f"Standardized mixed date strings to {target_format} for {changed} records",
    )
