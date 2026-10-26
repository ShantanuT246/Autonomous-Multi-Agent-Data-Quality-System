import difflib
import re
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from backend.app.schemas.enums import IssueType, Severity
from backend.app.schemas.models import Issue


def detect_outliers_statistical(df: pd.DataFrame, factor: float = 2.5) -> List[Issue]:
    """Detect numeric outliers using IQR and modified Z-score."""
    issues = []
    numeric_cols = df.select_dtypes(include=np.number).columns

    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) < 5:
            continue
        vals = series.to_numpy(dtype=float)
        finite = vals[np.isfinite(vals)]
        if len(finite) < 5:
            continue

        q25 = np.percentile(finite, 25)
        q75 = np.percentile(finite, 75)
        iqr = q75 - q25

        if iqr > 0:
            lower = q25 - factor * iqr
            upper = q75 + factor * iqr
            outlier_mask = (finite < lower) | (finite > upper)
            count = int(np.sum(outlier_mask))

            if count > 0:
                outlier_vals = finite[outlier_mask].tolist()[:5]
                issues.append(
                    Issue(
                        id=f"ISSUE-OUTLIER-{col}",
                        column=col,
                        issue_type=IssueType.OUTLIER,
                        severity=Severity.HIGH if count > 2 else Severity.MEDIUM,
                        description=f"Column '{col}' contains {count} extreme numeric outliers outside [{round(lower, 2)}, {round(upper, 2)}].",
                        affected_count=count,
                        examples=[round(v, 2) for v in outlier_vals],
                    )
                )

    return issues


def detect_category_inconsistencies(df: pd.DataFrame, min_similarity: float = 0.82) -> List[Issue]:
    """Detect casing variations, whitespace padding, and near-duplicate labels."""
    issues = []
    cat_cols = df.select_dtypes(include=["object", "string"]).columns

    for col in cat_cols:
        series = df[col].dropna().astype(str)
        if len(series) < 3:
            continue

        unique_vals = series.unique().tolist()
        if len(unique_vals) > 50:  # Skip high-cardinality columns like free text/IDs
            continue

        # Check for whitespace padding & case duplicates
        norm_map: Dict[str, List[str]] = {}
        for val in unique_vals:
            norm = val.strip().lower()
            norm_map.setdefault(norm, []).append(val)

        variations = [group for group in norm_map.values() if len(group) > 1]

        # Fuzzy matching for near-identical labels (e.g. typos)
        fuzzy_pairs = []
        for i in range(len(unique_vals)):
            for j in range(i + 1, len(unique_vals)):
                v1, v2 = unique_vals[i], unique_vals[j]
                if v1.strip().lower() != v2.strip().lower():
                    sim = difflib.SequenceMatcher(None, v1.lower(), v2.lower()).ratio()
                    if sim >= min_similarity:
                        fuzzy_pairs.append((v1, v2))

        total_examples = []
        for g in variations:
            total_examples.extend(g)
        for p in fuzzy_pairs:
            total_examples.extend(p)

        if total_examples:
            unique_examples = list(dict.fromkeys(total_examples))
            count = int(series.isin(unique_examples).sum())
            issues.append(
                Issue(
                    id=f"ISSUE-CAT-{col}",
                    column=col,
                    issue_type=IssueType.INCONSISTENT_CATEGORY,
                    severity=Severity.MEDIUM,
                    description=f"Inconsistent categorical representations and casing in column '{col}'.",
                    affected_count=count,
                    examples=unique_examples[:6],
                )
            )

    return issues


def detect_dtype_mismatches(df: pd.DataFrame) -> List[Issue]:
    """Detect object columns where >80% of values are parseable numbers or dates."""
    issues = []
    obj_cols = df.select_dtypes(include=["object", "string"]).columns

    for col in obj_cols:
        series = df[col].dropna().astype(str)
        if len(series) < 3:
            continue

        # Check if contains currency or formatted numbers
        num_pattern = re.compile(r"^[\$€£]?\s*-?[\d,]+(\.\d+)?\s*(USD|EUR|GBP|%)?$")
        matches = series.map(lambda s: bool(num_pattern.match(s.strip())))
        match_ratio = matches.sum() / len(series)

        if match_ratio >= 0.70:
            examples = series[matches].head(4).tolist()
            issues.append(
                Issue(
                    id=f"ISSUE-DTYPE-NUM-{col}",
                    column=col,
                    issue_type=IssueType.WRONG_DTYPE,
                    severity=Severity.HIGH,
                    description=f"Column '{col}' is stored as object/string, but {int(match_ratio*100)}% of values are numeric/currency.",
                    affected_count=int(matches.sum()),
                    examples=examples,
                )
            )
            continue

        # Check for mixed date formats
        iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        other_date_pattern = re.compile(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}")
        
        iso_count = series.map(lambda s: bool(iso_pattern.match(s.strip()))).sum()
        other_count = series.map(lambda s: bool(other_date_pattern.search(s.strip()))).sum()
        
        # If there are non-ISO dates or mixed styles, flag for standardized ISO parsing
        if other_count > 0 and (iso_count > 0 or other_count >= 2):
            examples = series[series.map(lambda s: bool(other_date_pattern.search(s.strip())))].head(4).tolist()
            issues.append(
                Issue(
                    id=f"ISSUE-DTYPE-DATE-{col}",
                    column=col,
                    issue_type=IssueType.INVALID_FORMAT,
                    severity=Severity.MEDIUM,
                    description=f"Column '{col}' contains mixed/non-standard date strings requiring ISO normalization.",
                    affected_count=int(other_count),
                    examples=examples,
                )
            )

    return issues


def detect_range_sanity(df: pd.DataFrame) -> List[Issue]:
    """Detect impossible values based on column-name semantic hints."""
    issues = []

    for col in df.columns:
        col_lower = col.lower()
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) == 0:
            continue

        # Age sanity: 0 to 120
        if "age" in col_lower:
            invalid_age = series[(series < 0) | (series > 120)]
            if len(invalid_age) > 0:
                issues.append(
                    Issue(
                        id=f"ISSUE-SANITY-AGE-{col}",
                        column=col,
                        issue_type=IssueType.INVALID_VALUE,
                        severity=Severity.CRITICAL,
                        description=f"Column '{col}' has {len(invalid_age)} biologically impossible values (< 0 or > 120).",
                        affected_count=len(invalid_age),
                        examples=invalid_age.tolist()[:5],
                    )
                )

        # Experience sanity: >= 0 and <= 70
        if "experience" in col_lower or "exp" in col_lower:
            invalid_exp = series[(series < 0) | (series > 70)]
            if len(invalid_exp) > 0:
                issues.append(
                    Issue(
                        id=f"ISSUE-SANITY-EXP-{col}",
                        column=col,
                        issue_type=IssueType.INVALID_VALUE,
                        severity=Severity.HIGH,
                        description=f"Column '{col}' has {len(invalid_exp)} invalid negative/extreme experience values.",
                        affected_count=len(invalid_exp),
                        examples=invalid_exp.tolist()[:5],
                    )
                )

        # Price / Spend sanity: >= 0
        if any(term in col_lower for term in ["price", "spend", "cost", "salary", "fee"]):
            negative_vals = series[series < 0]
            if len(negative_vals) > 0:
                issues.append(
                    Issue(
                        id=f"ISSUE-SANITY-PRICE-{col}",
                        column=col,
                        issue_type=IssueType.INVALID_VALUE,
                        severity=Severity.HIGH,
                        description=f"Column '{col}' contains {len(negative_vals)} negative values where only non-negative amounts are allowed.",
                        affected_count=len(negative_vals),
                        examples=negative_vals.tolist()[:5],
                    )
                )

    return issues


def detect_unit_inconsistencies(df: pd.DataFrame) -> List[Issue]:
    """Detect mixed unit representations in strings (e.g. lbs vs kg, cm vs inches)."""
    issues = []
    str_cols = df.select_dtypes(include=["object", "string"]).columns

    for col in str_cols:
        series = df[col].dropna().astype(str)
        has_kg = series.str.contains(r"\bkg\b", case=False, regex=True).sum()
        has_lbs = series.str.contains(r"\blbs?\b", case=False, regex=True).sum()

        if has_kg > 0 and has_lbs > 0:
            examples = series[series.str.contains(r"\b(kg|lbs?)\b", case=False, regex=True)].head(4).tolist()
            issues.append(
                Issue(
                    id=f"ISSUE-UNIT-{col}",
                    column=col,
                    issue_type=IssueType.UNIT_INCONSISTENCY,
                    severity=Severity.HIGH,
                    description=f"Column '{col}' has conflicting weight units ('kg' and 'lbs').",
                    affected_count=int(has_lbs),
                    examples=examples,
                )
            )

    return issues


def run_all_statistical_detectors(df: pd.DataFrame) -> List[Issue]:
    """Execute all rule-based and statistical quality detectors."""
    all_issues: List[Issue] = []

    # 1. Missing values
    missing_by_col = df.isna().sum()
    for col, count in missing_by_col.items():
        if count > 0:
            all_issues.append(
                Issue(
                    id=f"ISSUE-MISSING-{col}",
                    column=col,
                    issue_type=IssueType.MISSING_VALUES,
                    severity=Severity.HIGH if count / len(df) > 0.25 else Severity.MEDIUM,
                    description=f"Column '{col}' has {count} missing values ({round(100 * count / len(df), 1)}%).",
                    affected_count=int(count),
                    examples=["NaN"],
                )
            )

    # 2. Duplicate rows
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        all_issues.append(
            Issue(
                id="ISSUE-DUPLICATES",
                column=None,
                issue_type=IssueType.DUPLICATE_ROWS,
                severity=Severity.HIGH if dup_count / len(df) > 0.1 else Severity.MEDIUM,
                description=f"Dataset contains {dup_count} exact duplicate rows.",
                affected_count=dup_count,
                examples=[],
            )
        )

    # 3. Statistical and format checks
    all_issues.extend(detect_range_sanity(df))
    all_issues.extend(detect_dtype_mismatches(df))
    all_issues.extend(detect_unit_inconsistencies(df))
    all_issues.extend(detect_category_inconsistencies(df))
    all_issues.extend(detect_outliers_statistical(df))

    return all_issues
