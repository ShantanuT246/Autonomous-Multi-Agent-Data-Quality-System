
from pathlib import Path

import pandas as pd

from data_processing.profiler import profile_dataset
from data_processing.preprocessing import clean_dataset
from data_processing.visualizer import generate_quality_report


def run_pipeline(
    df: pd.DataFrame,
    output_dir: str = "reports",
) -> dict:
    """
    Run the complete data-quality workflow:
    1. Profile the original dataset.
    2. Clean the dataset.
    3. Profile the cleaned dataset.
    4. Generate before-and-after charts.
    5. Save the cleaned dataset.
    """

    # Step 1: Analyze the original dataset.
    before_profile = profile_dataset(df)

    # Step 2: Clean a copy of the dataset.
    cleaned_df, cleaning_log = clean_dataset(df)

    # Step 3: Analyze the cleaned dataset.
    after_profile = profile_dataset(cleaned_df)

    # Step 4: Generate visualizations.
    quality_report = generate_quality_report(
        original=df,
        cleaned=cleaned_df,
        output_dir=output_dir,
    )

    # Step 5: Save the cleaned dataset.
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    cleaned_file = output_path / "cleaned_dataset.csv"
    cleaned_df.to_csv(cleaned_file, index=False)

    # Return all results together.
    return {
        "before": before_profile,
        "after": after_profile,
        "cleaning_log": cleaning_log,
        "quality_report": quality_report,
        "cleaned_dataset_path": str(cleaned_file),
    }
