from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.enums import ActionType, IssueType, RiskLevel, Severity


class Issue(BaseModel):
    id: str = Field(description="Unique identifier for the issue (e.g. ISSUE-1)")
    column: Optional[str] = Field(default=None, description="Column name or None for dataset-level issues like duplicates")
    issue_type: IssueType = Field(description="Strict enum value for the problem detected")
    severity: Severity = Field(default=Severity.MEDIUM, description="Impact severity of the issue")
    description: str = Field(description="Clear explanation of the problem")
    affected_count: int = Field(default=0, description="Estimated or exact count of problematic rows/values")
    examples: List[Any] = Field(default_factory=list, description="Concrete examples of the dirty values")


class PlannedAction(BaseModel):
    id: str = Field(description="Unique identifier for the planned action (e.g. ACT-1)")
    issue_id: Optional[str] = Field(default=None, description="ID of the issue being addressed")
    column: Optional[str] = Field(default=None, description="Target column name")
    action: ActionType = Field(description="Strict allowed action enum")
    params: Dict[str, Any] = Field(default_factory=dict, description="Deterministic parameters for the tool")
    rationale: str = Field(description="Data-centric justification for why this strategy was chosen")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Assessed risk of the transformation")


class LogEntry(BaseModel):
    column: Optional[str] = None
    issue: str
    action: str
    records_changed: int = 0
    before_sample: Optional[Any] = None
    after_sample: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "success"  # success, failed, skipped
    details: Optional[str] = None


class QualityScoreComponents(BaseModel):
    completeness: float = Field(ge=0.0, le=100.0, description="Completeness score (missing values)")
    uniqueness: float = Field(ge=0.0, le=100.0, description="Uniqueness score (duplicate rows)")
    validity: float = Field(ge=0.0, le=100.0, description="Validity score (within bounds/regex)")
    consistency: float = Field(ge=0.0, le=100.0, description="Consistency score (categories & units)")
    type_correctness: float = Field(ge=0.0, le=100.0, description="Type correctness score")
    outlier_ratio: float = Field(ge=0.0, le=100.0, description="Outlier health score")


class QualityScore(BaseModel):
    total: float = Field(ge=0.0, le=100.0, description="Overall weighted score 0-100")
    components: QualityScoreComponents


class IntegrityChecks(BaseModel):
    row_count_before: int
    row_count_after: int
    row_loss_ratio: float
    columns_preserved: bool
    unexpected_nulls_introduced: int = 0
    passed: bool


class ValidationResult(BaseModel):
    passed: bool
    remaining_issues: List[Issue] = Field(default_factory=list)
    regressions: List[str] = Field(default_factory=list)
    integrity_checks: Optional[IntegrityChecks] = None
    score: float = 0.0
    message: str = ""
