
import pandas as pd

from data_processing.profiler import profile_dataset


def test_profile_dataset():
    df = pd.DataFrame({
        "Age": [21, -5, 25, 21],
        "Gender": ["Female", "Male", "female", "Female"],
        "Salary": [30000, None, 40000, 30000],
    })

    result = profile_dataset(df)

    assert result["rows"] == 4
    assert result["columns"] == 3
    assert result["total_missing"] == 1
    assert result["duplicate_rows"] == 1
    assert result["numeric_summary"]["Age"]["median"] == 21.0
