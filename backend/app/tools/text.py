from typing import Tuple
import pandas as pd
from backend.app.schemas.models import LogEntry


def strip_whitespace(df: pd.DataFrame, column: str, **kwargs) -> Tuple[pd.DataFrame, LogEntry]:
    """Strip leading and trailing whitespace from string/object columns."""
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="inconsistent_format", action="strip_whitespace", records_changed=0, status="skipped", details="Column not found")

    original = df_copy[column].copy()
    df_copy[column] = df_copy[column].map(
        lambda val: val.strip() if isinstance(val, str) else val
    )

    changed = int((original.fillna("<NA>") != df_copy[column].fillna("<NA>")).sum())
    sample_before = None
    sample_after = None
    if changed > 0:
        mask = original.fillna("<NA>") != df_copy[column].fillna("<NA>")
        sample_before = str(original[mask].iloc[0])
        sample_after = str(df_copy[column][mask].iloc[0])

    return df_copy, LogEntry(
        column=column,
        issue="inconsistent_format",
        action="strip_whitespace",
        records_changed=changed,
        before_sample=sample_before,
        after_sample=sample_after,
        status="success",
        details=f"Stripped leading/trailing whitespace across {changed} records",
    )


def normalize_case(df: pd.DataFrame, column: str, case_type: str = "title", **kwargs) -> Tuple[pd.DataFrame, LogEntry]:
    """Normalize casing (title, lower, upper) for string/object columns."""
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="inconsistent_format", action="normalize_case", records_changed=0, status="skipped", details="Column not found")

    original = df_copy[column].copy()

    def apply_case(val):
        if not isinstance(val, str):
            return val
        s = val.strip()
        if case_type == "lower":
            return s.lower()
        elif case_type == "upper":
            return s.upper()
        else:
            return s.title()

    df_copy[column] = df_copy[column].map(apply_case)

    changed = int((original.fillna("<NA>") != df_copy[column].fillna("<NA>")).sum())
    sample_before = None
    sample_after = None
    if changed > 0:
        mask = original.fillna("<NA>") != df_copy[column].fillna("<NA>")
        sample_before = str(original[mask].iloc[0])
        sample_after = str(df_copy[column][mask].iloc[0])

    return df_copy, LogEntry(
        column=column,
        issue="inconsistent_format",
        action="normalize_case",
        records_changed=changed,
        before_sample=sample_before,
        after_sample=sample_after,
        status="success",
        details=f"Normalized case ({case_type}) for {changed} records",
    )
