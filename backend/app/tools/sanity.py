import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from backend.app.schemas.models import LogEntry


def set_null_invalid(
    df: pd.DataFrame,
    column: str,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    allowed_values: Optional[List[Any]] = None,
    regex: Optional[str] = None,
    **kwargs,
) -> Tuple[pd.DataFrame, LogEntry]:
    """
    Replace impossible or invalid values (such as age < 0 or age > 120) with NaN
    so they can be cleanly handled by downstream imputation tools.
    """
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="invalid_value", action="set_null_invalid", records_changed=0, status="skipped", details="Column not found")

    original = df_copy[column].copy()
    invalid_mask = pd.Series(False, index=df_copy.index)

    # Range check
    if min_val is not None or max_val is not None:
        numeric_series = pd.to_numeric(df_copy[column], errors="coerce")
        if min_val is not None:
            invalid_mask |= numeric_series.notna() & (numeric_series < min_val)
        if max_val is not None:
            invalid_mask |= numeric_series.notna() & (numeric_series > max_val)

    # Allowed set check
    if allowed_values is not None:
        allowed_set = set(allowed_values)
        invalid_mask |= df_copy[column].notna() & ~df_copy[column].isin(allowed_set)

    # Regex format check
    if regex is not None:
        pattern = re.compile(regex)
        invalid_mask |= df_copy[column].notna() & ~df_copy[column].astype(str).map(lambda s: bool(pattern.match(s)))

    changed_count = int(invalid_mask.sum())
    sample_before = None
    if changed_count > 0:
        sample_before = str(original[invalid_mask].iloc[0])
        df_copy.loc[invalid_mask, column] = np.nan

    return df_copy, LogEntry(
        column=column,
        issue="invalid_value",
        action="set_null_invalid",
        records_changed=changed_count,
        before_sample=sample_before,
        after_sample="NaN",
        status="success" if changed_count > 0 else "skipped",
        details=f"Replaced {changed_count} invalid values with NaN (min={min_val}, max={max_val})",
    )


def convert_units(
    df: pd.DataFrame,
    column: str,
    factor: float = 1.0,
    unit_suffix: Optional[str] = None,
    **kwargs,
) -> Tuple[pd.DataFrame, LogEntry]:
    """
    Standardize unit inconsistencies:
    - If values contain unit labels like 'lbs' or 'kg', parses the number and applies factor
    - e.g., '0.88 lbs' -> 0.88 * 0.453592 = 0.40 kg
    """
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="unit_inconsistency", action="convert_units", records_changed=0, status="skipped", details="Column not found")

    original = df_copy[column].copy()
    changed_count = 0
    sample_before = None
    sample_after = None

    def transform_unit(val):
        nonlocal changed_count, sample_before, sample_after
        if pd.isna(val):
            return val
        s = str(val).strip().lower()
        if unit_suffix and unit_suffix.lower() in s:
            num_part = re.sub(r"[^\d.-]", "", s)
            try:
                num = float(num_part) * factor
                changed_count += 1
                if sample_before is None:
                    sample_before = str(val)
                    sample_after = str(round(num, 3))
                return round(num, 3)
            except ValueError:
                return val
        elif not unit_suffix:
            # Direct numeric scaling
            try:
                num = float(re.sub(r"[^\d.-]", "", s)) * factor
                changed_count += 1
                return round(num, 3)
            except ValueError:
                return val
        else:
            # Strip other unit letters if already in base unit
            try:
                clean_num = float(re.sub(r"[^\d.-]", "", s))
                return clean_num
            except ValueError:
                return val

    df_copy[column] = df_copy[column].map(transform_unit)

    return df_copy, LogEntry(
        column=column,
        issue="unit_inconsistency",
        action="convert_units",
        records_changed=changed_count,
        before_sample=sample_before,
        after_sample=sample_after,
        status="success" if changed_count > 0 else "skipped",
        details=f"Converted units for {changed_count} values with factor {factor} and suffix {unit_suffix}",
    )


def drop_rows(
    df: pd.DataFrame,
    column: str,
    operator: str = "isna",
    value: Any = None,
    **kwargs,
) -> Tuple[pd.DataFrame, LogEntry]:
    """
    Drop rows matching an explicit condition (guarded by row-loss limit).
    """
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="invalid_value", action="drop_rows", records_changed=0, status="skipped", details="Column not found")

    initial_len = len(df_copy)
    if operator == "isna":
        mask = df_copy[column].isna()
    elif operator == "==":
        mask = df_copy[column] == value
    elif operator == ">":
        mask = pd.to_numeric(df_copy[column], errors="coerce") > float(value)
    elif operator == "<":
        mask = pd.to_numeric(df_copy[column], errors="coerce") < float(value)
    else:
        mask = pd.Series(False, index=df_copy.index)

    dropped = int(mask.sum())
    df_result = df_copy[~mask]

    return df_result, LogEntry(
        column=column,
        issue="invalid_value",
        action="drop_rows",
        records_changed=dropped,
        before_sample=f"{initial_len} rows",
        after_sample=f"{len(df_result)} rows",
        status="success" if dropped > 0 else "skipped",
        details=f"Dropped {dropped} rows where {column} {operator} {value}",
    )
