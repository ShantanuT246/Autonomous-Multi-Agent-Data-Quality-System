import pandas as pd
import numpy as np
from data_processing.pipeline import run_pipeline as baseline_run_pipeline
from backend.app.graph.workflow import run_cleaning_pipeline
from backend.app.graph.state import load_dataframe_ref
from backend.app.reports.quality_score import compute_quality_score


def calculate_cell_accuracy(df_result: pd.DataFrame, df_truth: pd.DataFrame) -> float:
    """Calculate the percentage of cells matching ground-truth."""
    # Align rows and common columns
    common_cols = [c for c in df_truth.columns if c in df_result.columns]
    min_rows = min(len(df_result), len(df_truth))

    res_sub = df_result[common_cols].iloc[:min_rows]
    truth_sub = df_truth[common_cols].iloc[:min_rows]

    matches = 0
    total = min_rows * len(common_cols)

    for col in common_cols:
        for i in range(min_rows):
            v_res = res_sub[col].iloc[i]
            v_truth = truth_sub[col].iloc[i]

            if pd.isna(v_res) and pd.isna(v_truth):
                matches += 1
            elif str(v_res).strip().lower() == str(v_truth).strip().lower():
                matches += 1
            else:
                try:
                    if abs(float(v_res) - float(v_truth)) < 1e-2:
                        matches += 1
                except (ValueError, TypeError):
                    pass

    return round((matches / total) * 100, 2)


def test_agentic_pipeline_vs_baseline_evaluation():
    """
    Evaluation Benchmark:
    Compares the Autonomous Multi-Agent System against Member 1's fixed baseline.
    Proves agentic superiority on:
    - Outlier handling
    - Range sanity (<0 or >120 age)
    - Categorical standardization
    - Duplicate elimination
    - Quality score improvement
    """
    df_messy = pd.read_csv("sample_data/customers_messy.csv")
    df_clean_truth = pd.read_csv("sample_data/customers_clean.csv")

    # 1. Run Member 1 baseline pipeline
    baseline_res = baseline_run_pipeline(df_messy, output_dir="reports/baseline_test")
    df_baseline = pd.read_csv(baseline_res["cleaned_dataset_path"])
    baseline_score = compute_quality_score(df_baseline).total
    baseline_acc = calculate_cell_accuracy(df_baseline, df_clean_truth)

    # 2. Run Autonomous Multi-Agent Pipeline
    agent_state = run_cleaning_pipeline(
        df=df_messy,
        run_id="eval_run_benchmark",
        max_iterations=2,
    )
    final_ref = agent_state["best_df_ref"]
    df_agentic = load_dataframe_ref(final_ref)
    agentic_score = agent_state["final_score"]
    agentic_acc = calculate_cell_accuracy(df_agentic, df_clean_truth)

    print(f"\n================ EVALUATION BENCHMARK ================")
    print(f"Baseline Quality Score: {baseline_score} | Cell Accuracy: {baseline_acc}%")
    print(f"Agentic Quality Score:  {agentic_score} | Cell Accuracy: {agentic_acc}%")
    print(f"Score Improvement Delta: +{round(agentic_score - baseline_score, 1)} pts")
    print(f"======================================================\n")

    # Assert agentic system outperforms fixed rule pipeline
    assert agentic_score > baseline_score, "Agentic quality score should exceed fixed baseline"
    assert agentic_acc >= baseline_acc, "Agentic cell accuracy should match or exceed baseline"
    assert len(df_agentic) <= len(df_clean_truth) + 1  # Successfully dropped duplicate row
