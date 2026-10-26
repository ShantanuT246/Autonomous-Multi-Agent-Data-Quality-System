from pathlib import Path
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
import pandas as pd
from backend.app.config import settings
from backend.app.schemas.models import Issue, LogEntry, PlannedAction, ValidationResult


class CleaningState(TypedDict, total=False):
    run_id: str
    original_df_ref: str           # storage path/ID for original DataFrame
    current_df_ref: str            # storage path/ID for current working copy
    best_df_ref: str               # snapshot of highest scoring DataFrame for rollback
    initial_profile: Dict[str, Any]
    current_profile: Dict[str, Any]
    detected_issues: List[Dict[str, Any]]
    cleaning_plan: List[Dict[str, Any]]
    execution_log: List[Dict[str, Any]]
    validation_result: Dict[str, Any]
    iteration: int
    max_iterations: int
    failed_strategies: List[Dict[str, Any]]
    initial_score: float
    current_score: float
    best_score: float
    final_score: float
    status: str
    report: Dict[str, Any]
    error: Optional[str]


def get_df_storage_path(run_id: str, tag: str, extension: str = "parquet") -> Path:
    """Generate a deterministic storage path for a DataFrame snapshot."""
    run_dir = settings.STORAGE_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir / f"{tag}.{extension}"


def save_dataframe_ref(df: pd.DataFrame, run_id: str, tag: str) -> str:
    """
    Persist a DataFrame to disk and return its relative reference string.
    Uses Parquet format for fast I/O and type preservation, with CSV fallback.
    """
    path = get_df_storage_path(run_id, tag)
    try:
        df.to_parquet(path, index=False)
    except Exception:
        # Fallback to CSV if parquet engine isn't available or fails
        csv_path = path.with_suffix(".csv")
        df.to_csv(csv_path, index=False)
        return str(csv_path.relative_to(settings.STORAGE_DIR.parent))

    return str(path.relative_to(settings.STORAGE_DIR.parent))


def load_dataframe_ref(ref: str) -> pd.DataFrame:
    """
    Load a DataFrame from a stored reference.
    """
    file_path = Path(ref)
    if not file_path.exists():
        # Check relative to base directory
        file_path = settings.STORAGE_DIR.parent / ref

    if not file_path.exists():
        raise FileNotFoundError(f"DataFrame storage file not found: {ref}")

    if file_path.suffix == ".parquet":
        return pd.read_parquet(file_path)
    elif file_path.suffix in [".csv", ".txt"]:
        return pd.read_csv(file_path)
    elif file_path.suffix in [".xlsx", ".xls"]:
        return pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format for DataFrame storage: {file_path.suffix}")
