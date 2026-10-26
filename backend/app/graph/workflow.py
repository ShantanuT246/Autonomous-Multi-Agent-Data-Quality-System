import logging
from typing import Any, Callable, Dict, Optional
from langgraph.graph import END, StateGraph
import pandas as pd
from backend.app.agents.cleaner_agent import cleaner_node
from backend.app.agents.detector_agent import detector_node
from backend.app.agents.planner_agent import planner_node
from backend.app.agents.profiler_agent import profiler_node
from backend.app.agents.reporter_agent import reporter_node
from backend.app.agents.validator_agent import validator_node
from backend.app.db.repository import repo
from backend.app.graph.state import CleaningState, save_dataframe_ref

logger = logging.getLogger(__name__)


def route_after_validation(state: CleaningState) -> str:
    """
    Self-correction loop router:
    - If validation passed -> done
    - If max_iterations reached -> done (give up gracefully)
    - Else -> replan (feed remaining issues and failed strategies to Planner)
    """
    val = state.get("validation_result", {})
    passed = val.get("passed", False)
    iteration = state.get("iteration", 1)
    max_iter = state.get("max_iterations", 3)

    if passed:
        logger.info(f"Validation PASSED on iteration {iteration}. Routing to reporter.")
        return "done"

    if iteration >= max_iter:
        logger.info(f"Max iterations ({max_iter}) reached. Routing to reporter.")
        return "done"

    logger.info(f"Validation remaining issues present on iteration {iteration}. Re-planning...")
    return "replan"


def build_cleaning_graph():
    """Build and compile the LangGraph StateGraph workflow."""
    workflow = StateGraph(CleaningState)

    workflow.add_node("profiler", profiler_node)
    workflow.add_node("detector", detector_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("cleaner", cleaner_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("reporter", reporter_node)

    workflow.set_entry_point("profiler")
    workflow.add_edge("profiler", "detector")
    workflow.add_edge("detector", "planner")
    workflow.add_edge("planner", "cleaner")
    workflow.add_edge("cleaner", "validator")

    workflow.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "replan": "planner",
            "done": "reporter",
        },
    )
    workflow.add_edge("reporter", END)

    return workflow.compile()


cleaning_graph = build_cleaning_graph()


def run_cleaning_pipeline(
    df: pd.DataFrame,
    run_id: str,
    max_iterations: int = 3,
    progress_callback: Optional[Callable[[str, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    High-level entry point to execute the multi-agent cleaning graph:
    1. Persists original DataFrame snapshot
    2. Initializes state and database run record
    3. Streams/observes each node's execution and saves state snapshots to MongoDB
    4. Triggers progress_callback for SSE stream / UI events
    """
    original_ref = save_dataframe_ref(df, run_id, "original")

    initial_state: CleaningState = {
        "run_id": run_id,
        "original_df_ref": original_ref,
        "current_df_ref": original_ref,
        "best_df_ref": original_ref,
        "iteration": 0,
        "max_iterations": max_iterations,
        "failed_strategies": [],
        "execution_log": [],
        "status": "queued",
    }

    current_state = initial_state

    # Execute graph while observing progress and persisting agent snapshots
    for output in cleaning_graph.stream(initial_state):
        for node_name, state_update in output.items():
            current_state.update(state_update)

            # Persist timeline checkpoint in MongoDB
            repo.save_agent_state(
                run_id=run_id,
                node=node_name,
                iteration=current_state.get("iteration", 0),
                state_snapshot={
                    "status": current_state.get("status"),
                    "score": current_state.get("current_score"),
                    "plan_count": len(current_state.get("cleaning_plan", [])),
                    "issues_count": len(current_state.get("detected_issues", [])),
                },
            )

            # Update run status
            repo.update_run(run_id, {
                "status": current_state.get("status", node_name),
                "current_stage": node_name,
                "iteration": current_state.get("iteration", 0),
                "initial_score": current_state.get("initial_score"),
                "final_score": current_state.get("final_score"),
            })

            repo.add_pipeline_log(
                run_id=run_id,
                stage=node_name,
                level="INFO",
                message=f"Agent '{node_name.capitalize()}' node execution finished (Iteration {current_state.get('iteration', 0)}).",
            )

            # Notify UI subscriber if callback given
            if progress_callback:
                msg = f"Agent '{node_name}' finished step."
                progress_callback(node_name, current_state.get("iteration", 0), msg)

    return current_state
