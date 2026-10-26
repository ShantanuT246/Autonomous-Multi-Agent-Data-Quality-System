import io
import time
import unittest.mock
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_and_frontend_endpoints():
    res = client.get("/")
    assert res.status_code == 200
    assert "DataQuality.ai" in res.text

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"


def test_load_sample_dataset():
    res = client.post("/api/datasets/load-sample?sample_name=customers")
    assert res.status_code == 201
    data = res.json()
    assert data["filename"] == "customers_messy.csv"
    assert data["rows"] == 11


def test_dataset_upload_and_run_flow():
    csv_content = b"name,age,salary\nAlice,25,$50000\nBob,-5,$60000\nAlice,25,$50000\n"
    files = {"file": ("test_data.csv", io.BytesIO(csv_content), "text/csv")}

    # 1. Upload
    upload_res = client.post("/api/datasets/upload", files=files)
    assert upload_res.status_code == 201
    data = upload_res.json()
    assert "dataset_id" in data
    dataset_id = data["dataset_id"]
    assert data["rows"] == 3
    assert "preview" in data

    # 2. Get dataset metadata
    get_ds = client.get(f"/api/datasets/{dataset_id}")
    assert get_ds.status_code == 200
    assert get_ds.json()["dataset_id"] == dataset_id

    # 3. Trigger cleaning run (mock pipeline to test endpoint contract instantly)
    with unittest.mock.patch("backend.app.api.runs.run_cleaning_pipeline") as mock_pipeline:
        run_res = client.post("/api/runs", json={"dataset_id": dataset_id, "max_iterations": 2})
        assert run_res.status_code == 202
        run_data = run_res.json()
        assert "run_id" in run_data
        run_id = run_data["run_id"]
        assert mock_pipeline.called

    # 4. Check run status
    check_run = client.get(f"/api/runs/{run_id}")
    assert check_run.status_code == 200
    assert check_run.json()["run_id"] == run_id


def test_upload_invalid_extension():
    fake_file = {"file": ("malicious.exe", io.BytesIO(b"binary data"), "application/octet-stream")}
    res = client.post("/api/datasets/upload", files=fake_file)
    assert res.status_code == 400
    assert "Unsupported file format" in res.json()["detail"]
