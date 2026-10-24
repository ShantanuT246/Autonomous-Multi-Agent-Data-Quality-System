
import pandas as pd

from data_processing.visualizer import generate_quality_report


def test_generate_quality_report(tmp_path):
    original = pd.DataFrame({
        "Age": [21, None, 25, 21],
        "Gender": ["Female", "Male", "female", "Female"],
    })

    cleaned = pd.DataFrame({
        "Age": [21, 23, 25, 21],
        "Gender": ["Female", "Male", "Female", "Female"],
    })

    report = generate_quality_report(
        original,
        cleaned,
        output_dir=str(tmp_path),
    )

    assert report["original_missing"] == 1
    assert report["cleaned_missing"] == 0
    assert report["original_duplicates"] == 1
    assert report["cleaned_duplicates"] == 1

    assert (tmp_path / "missing_values.png").exists()
    assert (tmp_path / "duplicate_rows.png").exists()
