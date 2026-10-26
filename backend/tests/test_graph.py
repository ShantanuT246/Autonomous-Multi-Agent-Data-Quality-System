import pandas as pd
from backend.app.graph.workflow import run_cleaning_pipeline


def test_end_to_end_graph_execution():
    df_messy = pd.read_csv("sample_data/customers_messy.csv")
    events = []

    def on_progress(stage, iteration, message):
        events.append((stage, iteration, message))

    run_id = "test_run_e2e_1"
    result_state = run_cleaning_pipeline(
        df=df_messy,
        run_id=run_id,
        max_iterations=2,
        progress_callback=on_progress,
    )

    assert result_state["status"] == "completed"
    assert result_state["final_score"] > result_state["initial_score"]
    assert "report" in result_state
    assert len(result_state["execution_log"]) > 0
    assert len(events) >= 5  # profiler, detector, planner, cleaner, validator, reporter

    report = result_state["report"]
    assert "charts" in report
    assert "missing_values" in report["charts"]
    assert "executive_summary" in report
