from typing import Dict, Tuple
import pandas as pd
from backend.app.schemas.models import LogEntry


def standardize_categories(
    df: pd.DataFrame,
    column: str,
    mapping: Dict[str, str],
    **kwargs,
) -> Tuple[pd.DataFrame, LogEntry]:
    """
    Standardize inconsistent categorical values in a column using a value mapping dictionary.
    Keys can match case-insensitively / with stripped whitespace.
    """
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="inconsistent_category", action="standardize_categories", records_changed=0, status="skipped", details="Column not found")

    if not mapping:
        return df_copy, LogEntry(column=column, issue="inconsistent_category", action="standardize_categories", records_changed=0, status="skipped", details="Empty mapping")

    original = df_copy[column].copy()

    # Build a lookup normalized by strip and lower for flexible matching
    norm_mapping = {str(k).strip().lower(): v for k, v in mapping.items()}

    def map_val(val):
        if pd.isna(val):
            return val
        s_val = str(val).strip()
        lower_val = s_val.lower()
        if lower_val in norm_mapping:
            return norm_mapping[lower_val]
        if s_val in mapping:
            return mapping[s_val]
        return val

    df_copy[column] = df_copy[column].map(map_val)

    changed = int((original.fillna("<NA>") != df_copy[column].fillna("<NA>")).sum())
    sample_before = None
    sample_after = None
    if changed > 0:
        mask = original.fillna("<NA>") != df_copy[column].fillna("<NA>")
        sample_before = str(original[mask].iloc[0])
        sample_after = str(df_copy[column][mask].iloc[0])

    return df_copy, LogEntry(
        column=column,
        issue="inconsistent_category",
        action="standardize_categories",
        records_changed=changed,
        before_sample=sample_before,
        after_sample=sample_after,
        status="success",
        details=f"Standardized {changed} records using category mapping ({mapping})",
    )
