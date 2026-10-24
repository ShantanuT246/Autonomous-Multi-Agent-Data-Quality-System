
import pandas as pd

from data_processing.preprocessing import clean_dataset


def test_clean_dataset():
    df = pd.DataFrame({
        "Age": [21, None, 25],
        "Gender": [" Female ", "female", "Male"],
    })

    cleaned, log = clean_dataset(df)

    assert cleaned["Age"].isna().sum() == 0
    assert cleaned["Age"].iloc[1] == 23.0
    assert cleaned["Gender"].tolist() == [
        "Female", "Female", "Male"
    ]
    assert df["Age"].isna().sum() == 1
    assert isinstance(log, list)
    assert len(log) > 0
