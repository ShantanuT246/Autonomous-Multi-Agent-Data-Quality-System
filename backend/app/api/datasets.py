import io
import uuid
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel
import pandas as pd
from backend.app.config import settings
from backend.app.db.repository import repo

router = APIRouter(prefix="/datasets", tags=["datasets"])

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class DatasetUploadResponse(BaseModel):
    dataset_id: str
    filename: str
    file_size_bytes: int
    rows: int
    columns: int
    column_names: List[str]
    preview: List[Dict[str, Any]]


@router.post("/upload", response_model=DatasetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Upload CSV or Excel dataset file:
    - Enforces file extension validation (.csv, .xlsx, .xls)
    - Enforces 50 MB file size limit
    - Generates preview rows and saves to persistent storage & MongoDB
    """
    filename = file.filename or "uploaded_data.csv"
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    file_size = len(content)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    # Read dataframe with encoding fallbacks
    try:
        if ext == ".csv":
            try:
                df = pd.read_csv(io.BytesIO(content), encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(content), encoding="latin1")
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse tabular dataset: {str(e)}",
        )

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded dataset is empty.",
        )

    dataset_id = f"ds_{uuid.uuid4().hex[:10]}"
    storage_path = settings.STORAGE_DIR / "datasets" / f"{dataset_id}{ext}"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    with open(storage_path, "wb") as f:
        f.write(content)

    # Convert preview NaN/NaT to None for valid JSON serialization
    preview = df.head(10).replace({float("nan"): None}).to_dict(orient="records")

    metadata = {
        "dataset_id": dataset_id,
        "filename": filename,
        "file_path": str(storage_path),
        "file_size_bytes": file_size,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": df.columns.tolist(),
        "preview": preview,
    }

    repo.save_dataset(metadata)

    return DatasetUploadResponse(**metadata)


@router.post("/load-sample", response_model=DatasetUploadResponse, status_code=status.HTTP_201_CREATED)
def load_sample_dataset(sample_name: str = "customers"):
    """Load one of the pre-built messy test datasets."""
    sample_files = {
        "customers": "sample_data/customers_messy.csv",
        "employees": "sample_data/employees_messy.csv",
        "products": "sample_data/products_messy.csv",
    }
    path_str = sample_files.get(sample_name.lower())
    if not path_str or not Path(path_str).exists():
        raise HTTPException(status_code=400, detail=f"Sample '{sample_name}' not found. Available: {list(sample_files.keys())}")

    path = Path(path_str)
    with open(path, "rb") as f:
        content = f.read()

    df = pd.read_csv(io.BytesIO(content))
    dataset_id = f"ds_{uuid.uuid4().hex[:10]}"
    storage_path = settings.STORAGE_DIR / "datasets" / f"{dataset_id}.csv"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    with open(storage_path, "wb") as f:
        f.write(content)

    preview = df.head(10).replace({float("nan"): None}).to_dict(orient="records")
    metadata = {
        "dataset_id": dataset_id,
        "filename": path.name,
        "file_path": str(storage_path),
        "file_size_bytes": len(content),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": df.columns.tolist(),
        "preview": preview,
    }
    repo.save_dataset(metadata)
    return DatasetUploadResponse(**metadata)


@router.get("/{dataset_id}", response_model=DatasetUploadResponse)
def get_dataset(dataset_id: str):
    """Retrieve uploaded dataset metadata and preview."""
    doc = repo.get_dataset(dataset_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )
    return DatasetUploadResponse(**doc)
