import pandas as pd
from backend.app.reports.quality_score import compute_quality_score


def test_quality_score_messy_vs_clean():
    df_messy = pd.read_csv("sample_data/customers_messy.csv")
    df_clean = pd.read_csv("sample_data/customers_clean.csv")

    score_messy = compute_quality_score(df_messy)
    score_clean = compute_quality_score(df_clean)

    assert score_messy.total < 80.0, f"Expected messy score to be < 80, got {score_messy.total}"
    assert score_clean.total >= 95.0, f"Expected clean score to be >= 95, got {score_clean.total}"
    assert score_clean.total > score_messy.total
    assert score_clean.components.completeness == 100.0
    assert score_clean.components.uniqueness == 100.0


def test_employees_quality_score():
    df_messy = pd.read_csv("sample_data/employees_messy.csv")
    df_clean = pd.read_csv("sample_data/employees_clean.csv")

    score_messy = compute_quality_score(df_messy)
    score_clean = compute_quality_score(df_clean)

    assert score_clean.total > score_messy.total
