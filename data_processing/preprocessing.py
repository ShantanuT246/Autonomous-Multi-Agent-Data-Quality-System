
import pandas as pd
from sklearn.impute import SimpleImputer


def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Clean missing values and normalize categorical text.

    Returns:
        cleaned_df: A cleaned copy of the input DataFrame.
        log: A record of the transformations applied.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    if df.empty:
        raise ValueError("The dataset is empty.")

    cleaned_df = df.copy(deep=True)
    log = []

    # Normalize whitespace and capitalization in text columns.
    for column in cleaned_df.select_dtypes(
        include=["object", "string"]
    ).columns:
        original = cleaned_df[column].copy()

        cleaned_df[column] = cleaned_df[column].map(
            lambda value: (
                value.strip().title()
                if isinstance(value, str) and value.strip()
                else value
            )
        )

        changed = int(
            (original.fillna("<NA>") !=
             cleaned_df[column].fillna("<NA>")).sum()
        )

        if changed:
            log.append({
                "column": column,
                "issue": "Inconsistent text formatting",
                "action": "Trim whitespace and normalize capitalization",
                "changed_records": changed,
            })

    # Impute missing numeric values with the median.
    numeric_columns = cleaned_df.select_dtypes(
        include=["number"]
    ).columns.tolist()

    if numeric_columns:
        before = cleaned_df[numeric_columns].isna().sum()
        imputer = SimpleImputer(strategy="median")
        cleaned_df[numeric_columns] = imputer.fit_transform(
            cleaned_df[numeric_columns]
        )

        for column in numeric_columns:
            changed = int(before[column])
            if changed:
                log.append({
                    "column": column,
                    "issue": "Missing numeric values",
                    "action": "Median imputation",
                    "changed_records": changed,
                })

    # Impute missing categorical values with the most frequent value.
    categorical_columns = cleaned_df.select_dtypes(
        include=["object", "string", "category"]
    ).columns.tolist()

    if categorical_columns:
        before = cleaned_df[categorical_columns].isna().sum()
        imputer = SimpleImputer(strategy="most_frequent")

        cleaned_df[categorical_columns] = imputer.fit_transform(
            cleaned_df[categorical_columns]
        )

        for column in categorical_columns:
            changed = int(before[column])
            if changed:
                log.append({
                    "column": column,
                    "issue": "Missing categorical values",
                    "action": "Most-frequent-value imputation",
                    "changed_records": changed,
                })

    return cleaned_df, log
