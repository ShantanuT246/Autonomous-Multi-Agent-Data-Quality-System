import pandas as pd
import numpy as np
import pytest
from backend.app.schemas.enums import ActionType
from backend.app.tools.registry import execute_tool_safely, TOOL_REGISTRY
from backend.app.tools.detectors import run_all_statistical_detectors


@pytest.fixture
def sample_test_df():
    return pd.DataFrame({
        "age": [25, -5, 30, 150, 28, 28],
        "gender": ["Male", "M", "female", "F ", "Male", "Male"],
        "salary": ["$50,000", "$60,000", "N/A", "$55,000", "$10,000,000", "$10,000,000"],
        "date": ["2023-01-01", "01/02/2023", "2023-01-03", "Jan 4, 2023", "2023-01-05", "2023-01-05"],
    })


def test_drop_duplicates(sample_test_df):
    cleaned, log = execute_tool_safely(ActionType.DROP_DUPLICATES.value, sample_test_df)
    assert len(cleaned) == 5
    assert log.records_changed == 1
    assert log.status == "success"


def test_standardize_categories(sample_test_df):
    mapping = {"m": "Male", "male": "Male", "f": "Female", "female": "Female"}
    cleaned, log = execute_tool_safely(
        ActionType.STANDARDIZE_CATEGORIES.value,
        sample_test_df,
        column="gender",
        params={"mapping": mapping},
    )
    assert set(cleaned["gender"].tolist()) == {"Male", "Female"}
    assert log.records_changed >= 2


def test_cast_dtype_numeric(sample_test_df):
    cleaned, log = execute_tool_safely(
        ActionType.CAST_DTYPE.value,
        sample_test_df,
        column="salary",
        params={"target_dtype": "float"},
    )
    assert np.isnan(cleaned["salary"].iloc[2])  # 'N/A' becomes NaN
    assert cleaned["salary"].iloc[0] == 50000.0
    assert cleaned["salary"].iloc[1] == 60000.0


def test_set_null_invalid(sample_test_df):
    cleaned, log = execute_tool_safely(
        ActionType.SET_NULL_INVALID.value,
        sample_test_df,
        column="age",
        params={"min_val": 0, "max_val": 120},
    )
    assert np.isnan(cleaned["age"].iloc[1])  # -5 was replaced by NaN
    assert np.isnan(cleaned["age"].iloc[3])  # 150 was replaced by NaN
    assert log.records_changed == 2


def test_impute_median():
    df = pd.DataFrame({"score": [10.0, np.nan, 20.0, 30.0]})
    cleaned, log = execute_tool_safely(
        ActionType.IMPUTE_MEDIAN.value,
        df,
        column="score",
    )
    assert cleaned["score"].iloc[1] == 20.0
    assert log.records_changed == 1


def test_clip_outliers():
    df = pd.DataFrame({"val": [10.0, 12.0, 11.0, 13.0, 10.0, 11.0, 1000.0]})
    cleaned, log = execute_tool_safely(
        ActionType.CLIP_OUTLIERS.value,
        df,
        column="val",
        params={"method": "iqr", "factor": 1.5},
    )
    assert cleaned["val"].max() < 1000.0
    assert log.records_changed == 1


def test_row_loss_guard():
    df = pd.DataFrame({"id": list(range(100))})
    # Attempt to drop 50% of rows
    cleaned, log = execute_tool_safely(
        ActionType.DROP_ROWS.value,
        df,
        column="id",
        params={"operator": ">", "value": 50},
        max_row_loss_ratio=0.20,
    )
    assert log.status == "blocked"
    assert len(cleaned) == 100  # DataFrame preserved intact


def test_statistical_detectors(sample_test_df):
    issues = run_all_statistical_detectors(sample_test_df)
    issue_types = [i.issue_type for i in issues]
    assert any("duplicate" in t.value for t in issue_types)
    assert any("sanity" in i.id.lower() or "invalid" in t.value for i, t in zip(issues, issue_types))
