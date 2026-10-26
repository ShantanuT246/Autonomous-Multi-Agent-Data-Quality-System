from enum import Enum


class IssueType(str, Enum):
    MISSING_VALUES = "missing_values"
    DUPLICATE_ROWS = "duplicate_rows"
    INVALID_VALUE = "invalid_value"
    OUTLIER = "outlier"
    INCONSISTENT_CATEGORY = "inconsistent_category"
    WRONG_DTYPE = "wrong_dtype"
    INVALID_FORMAT = "invalid_format"
    CONTRADICTORY_VALUE = "contradictory_value"
    UNIT_INCONSISTENCY = "unit_inconsistency"


class ActionType(str, Enum):
    IMPUTE_MEDIAN = "impute_median"
    IMPUTE_MEAN = "impute_mean"
    IMPUTE_MODE = "impute_mode"
    IMPUTE_CONSTANT = "impute_constant"
    IMPUTE_KNN = "impute_knn"
    FILL_UNKNOWN = "fill_unknown"
    DROP_DUPLICATES = "drop_duplicates"
    STANDARDIZE_CATEGORIES = "standardize_categories"
    CAST_DTYPE = "cast_dtype"
    PARSE_DATES = "parse_dates"
    CLIP_OUTLIERS = "clip_outliers"
    SET_NULL_INVALID = "set_null_invalid"
    DROP_ROWS = "drop_rows"
    STRIP_WHITESPACE = "strip_whitespace"
    NORMALIZE_CASE = "normalize_case"
    CONVERT_UNITS = "convert_units"
    FLAG_FOR_REVIEW = "flag_for_review"
    NO_ACTION = "no_action"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RunStatus(str, Enum):
    QUEUED = "queued"
    PROFILING = "profiling"
    DETECTING = "detecting"
    PLANNING = "planning"
    CLEANING = "cleaning"
    VALIDATING = "validating"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"
