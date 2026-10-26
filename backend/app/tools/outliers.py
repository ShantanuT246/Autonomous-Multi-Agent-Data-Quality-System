from typing import Tuple
import numpy as np
import pandas as pd
from backend.app.schemas.models import LogEntry


def clip_outliers(
    df: pd.DataFrame,
    column: str,
    method: str = "iqr",
    factor: float = 1.5,
    **kwargs,
) -> Tuple[pd.DataFrame, LogEntry]:
    """
    Clip / winsorize extreme numeric outliers using IQR or Z-score thresholds.
    Does not drop rows; keeps data bounded.
    """
    df_copy = df.copy(deep=True)
    if column not in df_copy.columns:
        return df_copy, LogEntry(column=column, issue="outlier", action="clip_outliers", records_changed=0, status="skipped", details="Column not found")

    series = pd.to_numeric(df_copy[column], errors="coerce")
    valid_mask = series.notna()
    if valid_mask.sum() == 0:
        return df_copy, LogEntry(column=column, issue="outlier", action="clip_outliers", records_changed=0, status="skipped", details="No numeric values")

    vals = series[valid_mask]

    if method == "zscore":
        mean_val = vals.mean()
        std_val = vals.std()
        if std_val == 0 or np.isnan(std_val):
            return df_copy, LogEntry(column=column, issue="outlier", action="clip_outliers", records_changed=0, status="skipped", details="Zero standard deviation")
        lower_bound = mean_val - factor * std_val
        upper_bound = mean_val + factor * std_val
    else:  # IQR default
        q25 = vals.quantile(0.25)
        q75 = vals.quantile(0.75)
        iqr = q75 - q25
        lower_bound = q25 - factor * iqr
        upper_bound = q75 + factor * iqr

    outlier_mask = valid_mask & ((series < lower_bound) | (series > upper_bound))
    changed_count = int(outlier_mask.sum())

    sample_before = None
    sample_after = None
    if changed_count > 0:
        sample_before = str(series[outlier_mask].iloc[0])
        # Clip
        series_clipped = series.clip(lower=lower_bound, upper=upper_bound)
        sample_after = str(series_clipped[outlier_mask].iloc[0])
        df_copy[column] = series_clipped
    else:
        sample_before = None
        sample_after = None

    return df_copy, LogEntry(
        column=column,
        issue="outlier",
        action="clip_outliers",
        records_changed=changed_count,
        before_sample=sample_before,
        after_sample=sample_after,
        status="success" if changed_count > 0 else "skipped",
        details=f"Clipped {changed_count} values using {method.upper()} bounds [{round(lower_bound, 2)}, {round(upper_bound, 2)}]",
    )
