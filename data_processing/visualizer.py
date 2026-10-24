
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path


def generate_quality_report(
    original: pd.DataFrame,
    cleaned: pd.DataFrame,
    output_dir: str = "reports",
) -> dict:
    """
    Generate before/after data-quality charts and save them as PNG files.
    Returns paths and basic quality metrics.
    """
    if not isinstance(original, pd.DataFrame):
        raise TypeError("original must be a pandas DataFrame.")

    if not isinstance(cleaned, pd.DataFrame):
        raise TypeError("cleaned must be a pandas DataFrame.")

    if original.empty or cleaned.empty:
        raise ValueError("Both datasets must be non-empty.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    original_missing = int(original.isna().sum().sum())
    cleaned_missing = int(cleaned.isna().sum().sum())

    original_duplicates = int(original.duplicated().sum())
    cleaned_duplicates = int(cleaned.duplicated().sum())

    # Chart 1: Missing values before and after cleaning.
    fig, ax = plt.subplots(figsize=(7, 4))

    ax.bar(
        ["Before cleaning", "After cleaning"],
        [original_missing, cleaned_missing],
    )

    ax.set_title("Missing Values Comparison")
    ax.set_ylabel("Number of missing cells")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    missing_chart = output_path / "missing_values.png"
    fig.savefig(missing_chart, dpi=150)
    plt.close(fig)

    # Chart 2: Duplicate rows before and after cleaning.
    fig, ax = plt.subplots(figsize=(7, 4))

    ax.bar(
        ["Before cleaning", "After cleaning"],
        [original_duplicates, cleaned_duplicates],
    )

    ax.set_title("Duplicate Rows Comparison")
    ax.set_ylabel("Number of duplicate rows")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    duplicate_chart = output_path / "duplicate_rows.png"
    fig.savefig(duplicate_chart, dpi=150)
    plt.close(fig)

    return {
        "original_missing": original_missing,
        "cleaned_missing": cleaned_missing,
        "original_duplicates": original_duplicates,
        "cleaned_duplicates": cleaned_duplicates,
        "charts": {
            "missing_values": str(missing_chart),
            "duplicate_rows": str(duplicate_chart),
        },
    }
