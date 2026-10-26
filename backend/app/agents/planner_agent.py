import json
import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from backend.app.graph.state import CleaningState
from backend.app.llm.client import call_llm
from backend.app.schemas.enums import ActionType, IssueType, RiskLevel, RunStatus
from backend.app.schemas.models import Issue, PlannedAction

logger = logging.getLogger(__name__)

# Canonical ordering of operations
CANONICAL_ACTION_ORDER = [
    ActionType.CAST_DTYPE.value,
    ActionType.PARSE_DATES.value,
    ActionType.SET_NULL_INVALID.value,
    ActionType.CONVERT_UNITS.value,
    ActionType.STRIP_WHITESPACE.value,
    ActionType.NORMALIZE_CASE.value,
    ActionType.STANDARDIZE_CATEGORIES.value,
    ActionType.DROP_DUPLICATES.value,
    ActionType.IMPUTE_MEDIAN.value,
    ActionType.IMPUTE_MEAN.value,
    ActionType.IMPUTE_MODE.value,
    ActionType.IMPUTE_CONSTANT.value,
    ActionType.IMPUTE_KNN.value,
    ActionType.FILL_UNKNOWN.value,
    ActionType.CLIP_OUTLIERS.value,
    ActionType.DROP_ROWS.value,
    ActionType.FLAG_FOR_REVIEW.value,
    ActionType.NO_ACTION.value,
]


class LLMPlan(BaseModel):
    actions: List[PlannedAction] = Field(default_factory=list, description="Ordered list of cleaning decisions")
    overall_reasoning: str = Field(default="", description="High-level strategy summary")


def planner_node(state: CleaningState) -> Dict[str, Any]:
    """
    Cleaning Planner Agent:
    - Analyzes detected issues, profile, and failed_strategies from previous iterations.
    - Decides optimal deterministic tool parameters and strategies.
    - Adapts if earlier attempts regressed or failed.
    - Post-processes and sorts into canonical execution order.
    """
    run_id = state.get("run_id", "default_run")
    issues_data = state.get("detected_issues", [])
    issues = [Issue.model_validate(i) for i in issues_data]
    failed_strategies = state.get("failed_strategies", [])
    profile = state.get("current_profile", {})
    iteration = state.get("iteration", 0)

    if not issues:
        logger.info(f"[{run_id}] Planner Node: No issues detected. Plan is empty.")
        return {
            "cleaning_plan": [],
            "status": RunStatus.PLANNING.value,
        }

    issues_summary = [
        {
            "id": i.id,
            "column": i.column,
            "issue_type": i.issue_type.value,
            "severity": i.severity.value,
            "affected_count": i.affected_count,
            "examples": i.examples[:5],
        }
        for i in issues
    ]

    planner_prompt = f"""
You are the Cleaning Planner Agent. Formulate an actionable, deterministic data cleaning plan for these detected issues:
Issues to Address:
{json.dumps(issues_summary, indent=2)}

Failed Strategies from Previous Iterations (DO NOT REPEAT THESE):
{json.dumps(failed_strategies, indent=2)}

Column Data Types and Missing Info:
{json.dumps(profile.get("data_types", {}), indent=2)}

CRITICAL PLANNING RULES:
1. ONLY use actions from the allowed ActionType enum:
   impute_median, impute_mean, impute_mode, impute_constant, impute_knn, fill_unknown,
   drop_duplicates, standardize_categories, cast_dtype, parse_dates, clip_outliers,
   set_null_invalid, drop_rows, strip_whitespace, normalize_case, convert_units,
   flag_for_review, no_action.
2. For numeric columns with missing values:
   - If distribution is skewed or has outliers, select 'impute_median'.
   - If categorical or text, select 'impute_mode' or 'fill_unknown'.
3. For inconsistent categories:
   - Use 'standardize_categories' and provide a concrete 'mapping' in params, e.g. {{"M": "Male", "male": "Male"}}.
4. For impossible values (e.g. negative age):
   - Use 'set_null_invalid' with min_val/max_val so it can be cleanly imputed.
5. For unit inconsistencies (e.g. lbs to kg):
   - Use 'convert_units' with factor and unit_suffix.
6. Provide a concise, professional rationale for every planned action.
"""

    planned_actions: List[PlannedAction] = []

    try:
        res: LLMPlan = call_llm(
            prompt=planner_prompt,
            response_schema=LLMPlan,
            system_prompt=(
                "You are an expert Data Cleaning Planner. Propose precise, safe transformations. "
                "Never output actions outside the authorized action enum."
            ),
            run_id=run_id,
            temperature=0.1,
        )
        planned_actions = res.actions
    except Exception as e:
        logger.warning(f"[{run_id}] LLM planner fallback: {e}")

    # Fallback heuristic planning if LLM produces empty actions
    if not planned_actions:
        planned_actions = _generate_heuristic_plan(issues)

    # Post-process, validate columns exist, and sort by canonical order
    valid_actions = []
    col_names = set(profile.get("column_names", []))

    for act in planned_actions:
        # Check column existence (allow None for dataset-level actions like drop_duplicates)
        if act.column and col_names and act.column not in col_names:
            logger.warning(f"Planner proposed non-existent column '{act.column}'. Skipping.")
            continue
        valid_actions.append(act)

    # Sort actions by canonical dependency order
    def action_priority(action_obj: PlannedAction) -> int:
        act_val = action_obj.action.value if hasattr(action_obj.action, "value") else str(action_obj.action)
        try:
            return CANONICAL_ACTION_ORDER.index(act_val)
        except ValueError:
            return 999

    valid_actions.sort(key=action_priority)

    logger.info(f"[{run_id}] Planner Node complete. Created {len(valid_actions)} planned actions.")

    return {
        "cleaning_plan": [a.model_dump() for a in valid_actions],
        "status": RunStatus.PLANNING.value,
    }


def _generate_heuristic_plan(issues: List[Issue]) -> List[PlannedAction]:
    """Deterministic fallback planner if LLM is unavailable."""
    plan = []
    idx = 1
    for i in issues:
        act_type = ActionType.NO_ACTION
        params = {}
        risk = RiskLevel.LOW
        rationale = f"Heuristic resolution for {i.issue_type.value}"

        if i.issue_type == IssueType.DUPLICATE_ROWS:
            act_type = ActionType.DROP_DUPLICATES
            rationale = "Remove exact duplicate rows across all columns."
        elif i.issue_type == IssueType.MISSING_VALUES:
            act_type = ActionType.IMPUTE_MEDIAN
            rationale = "Impute missing numeric values with median."
        elif i.issue_type == IssueType.INVALID_VALUE:
            if i.column and "age" in i.column.lower():
                act_type = ActionType.SET_NULL_INVALID
                params = {"min_val": 0, "max_val": 120}
                rationale = "Nullify impossible age values (<0 or >120)."
            else:
                act_type = ActionType.FLAG_FOR_REVIEW
                rationale = "Flag impossible value for human inspection."
        elif i.issue_type == IssueType.WRONG_DTYPE:
            act_type = ActionType.CAST_DTYPE
            params = {"target_dtype": "float"}
            rationale = "Cast formatted currency/numeric string to float."
        elif i.issue_type == IssueType.INVALID_FORMAT:
            act_type = ActionType.PARSE_DATES
            params = {"target_format": "%Y-%m-%d"}
            rationale = "Standardize dates to ISO YYYY-MM-DD."
        elif i.issue_type == IssueType.INCONSISTENT_CATEGORY:
            if i.column and "gender" in i.column.lower():
                act_type = ActionType.STANDARDIZE_CATEGORIES
                params = {"mapping": {"m": "Male", "male": "Male", "f": "Female", "female": "Female"}}
                rationale = "Standardize gender labels to 'Male' and 'Female'."
            else:
                act_type = ActionType.STRIP_WHITESPACE
                rationale = "Strip whitespace and normalize text."
        elif i.issue_type == IssueType.OUTLIER:
            act_type = ActionType.CLIP_OUTLIERS
            params = {"method": "iqr", "factor": 1.5}
            rationale = "Winsorize extreme outliers using IQR bounds."
        elif i.issue_type == IssueType.UNIT_INCONSISTENCY:
            act_type = ActionType.CONVERT_UNITS
            params = {"factor": 0.453592, "unit_suffix": "lbs"}
            rationale = "Convert lbs to kg (factor 0.453592)."

        plan.append(
            PlannedAction(
                id=f"ACT-{idx}",
                issue_id=i.id,
                column=i.column,
                action=act_type,
                params=params,
                rationale=rationale,
                risk_level=risk,
            )
        )
        idx += 1

    return plan
