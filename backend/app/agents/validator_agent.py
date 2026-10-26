import logging
from typing import Any, Dict, List
import pandas as pd
from backend.app.db.repository import repo
from backend.app.graph.state import CleaningState, load_dataframe_ref
from backend.app.reports.quality_score import compute_quality_score
from backend.app.schemas.enums import RunStatus
from backend.app.schemas.models import IntegrityChecks, Issue, ValidationResult
from backend.app.tools.detectors import run_all_statistical_detectors

logger = logging.getLogger(__name__)


def validator_node(state: CleaningState) -> Dict[str, Any]:
    """
    Validation Agent:
    - Performs deterministic integrity checks (row loss within bounds, columns preserved).
    - Checks for regression: scores must improve or at least stay stable.
    - Re-runs detectors on the cleaned DataFrame to identify remaining defects.
    - Automatic Rollback: if an iteration made things worse, reverts current_df_ref to best_df_ref
      and logs the strategy into failed_strategies so Planner chooses an alternative.
    """
    run_id = state.get("run_id", "default_run")
    iteration = state.get("iteration", 1)
    original_ref = state.get("original_df_ref")
    current_ref = state.get("current_df_ref")
    best_ref = state.get("best_df_ref", current_ref)
    best_score = state.get("best_score", state.get("initial_score", 0.0))
    failed_strategies = list(state.get("failed_strategies", []))

    df_original = load_dataframe_ref(original_ref)
    df_cleaned = load_dataframe_ref(current_ref)

    repo.add_pipeline_log(
        run_id=run_id,
        stage="validator",
        level="INFO",
        message=f"[Iteration {iteration}] Running integrity guard checks and regression analysis...",
    )

    # 1. Integrity checks
    row_count_before = len(df_original)
    row_count_after = len(df_cleaned)
    row_loss_ratio = (
        (row_count_before - row_count_after) / row_count_before
        if row_count_before > 0 else 0.0
    )
    columns_preserved = set(df_original.columns) == set(df_cleaned.columns)

    # Check for unexpected new NaNs in originally complete columns
    orig_nulls = df_original.isna().sum()
    clean_nulls = df_cleaned.isna().sum()
    new_nulls = 0
    for col in df_original.columns:
        if col in df_cleaned.columns and orig_nulls[col] == 0 and clean_nulls[col] > 0:
            new_nulls += int(clean_nulls[col])

    integrity_passed = (row_loss_ratio <= 0.20) and (new_nulls == 0) and columns_preserved

    repo.add_pipeline_log(
        run_id=run_id,
        stage="validator",
        level="SUCCESS" if integrity_passed else "WARN",
        message=f"Integrity check {'PASSED' if integrity_passed else 'FAILED'}: rows {row_count_before} -> {row_count_after} (loss: {row_loss_ratio:.1%}, limit: 20%), new nulls: {new_nulls}, columns preserved: {columns_preserved}.",
    )

    integrity_checks = IntegrityChecks(
        row_count_before=row_count_before,
        row_count_after=row_count_after,
        row_loss_ratio=round(row_loss_ratio, 4),
        columns_preserved=columns_preserved,
        unexpected_nulls_introduced=new_nulls,
        passed=integrity_passed,
    )

    # 2. Re-run detectors on cleaned DataFrame
    remaining_issues: List[Issue] = run_all_statistical_detectors(df_cleaned)

    # 3. Compute new quality score
    new_score_obj = compute_quality_score(df_cleaned, remaining_issues)
    new_score = new_score_obj.total

    repo.add_pipeline_log(
        run_id=run_id,
        stage="validator",
        level="INFO",
        message=f"Re-scored Quality: {best_score:.1f} -> {new_score:.1f} ({new_score - best_score:+.1f} pts). Remaining defects: {len(remaining_issues)}.",
    )

    regressions: List[str] = []
    effective_current_ref = current_ref

    # 4. Check for Regression & Trigger Rollback if worse
    if new_score < best_score:
        reason = f"Quality score regressed from {best_score} to {new_score}."
        regressions.append(reason)
        logger.warning(f"[{run_id}] Regression detected! {reason} Rolling back to {best_ref}...")

        repo.add_pipeline_log(
            run_id=run_id,
            stage="validator",
            level="WARN",
            message=f"REGRESSION DETECTED: Score dropped from {best_score} to {new_score}. Reverting to previous best snapshot {best_ref}.",
        )

        # Record failed strategy
        plan = state.get("cleaning_plan", [])
        failed_strategies.append({
            "iteration": iteration,
            "actions_attempted": plan,
            "regressed_from": best_score,
            "regressed_to": new_score,
        })

        # Roll back reference
        effective_current_ref = best_ref
        new_score = best_score
    else:
        # Score improved or held steady: update best snapshot
        best_score = new_score
        best_ref = current_ref

    # 5. Judge overall pass condition
    has_critical = any(i.severity.value == "critical" for i in remaining_issues)
    passed = (len(remaining_issues) == 0 or (new_score >= 92.0 and not has_critical)) and integrity_passed

    verdict_text = "PASSED: Target quality threshold met without critical defects" if passed else f"IN PROGRESS: {len(remaining_issues)} defects remain"

    repo.add_pipeline_log(
        run_id=run_id,
        stage="validator",
        level="SUCCESS" if passed else "INFO",
        message=f"Validator Verdict: {verdict_text}. Final Score: {new_score:.1f}/100.0.",
    )

    message = (
        f"Validation passed with score {new_score}."
        if passed
        else f"Remaining issues detected ({len(remaining_issues)}). Iteration {iteration}."
    )

    validation_result = ValidationResult(
        passed=passed,
        remaining_issues=remaining_issues,
        regressions=regressions,
        integrity_checks=integrity_checks,
        score=new_score,
        message=message,
    )

    logger.info(f"[{run_id}] Validator Node complete: passed={passed}, score={new_score}")

    return {
        "validation_result": validation_result.model_dump(),
        "current_df_ref": effective_current_ref,
        "best_df_ref": best_ref,
        "best_score": best_score,
        "current_score": new_score,
        "final_score": new_score,
        "failed_strategies": failed_strategies,
        "status": RunStatus.VALIDATING.value,
    }
