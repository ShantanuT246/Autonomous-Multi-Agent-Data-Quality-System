from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.app.db.mongo import get_sync_db


def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


class DBRepository:
    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_sync_db()
        return self._db

    # --- Datasets ---
    def save_dataset(self, data: Dict[str, Any]) -> str:
        record = {
            **data,
            "created_at": data.get("created_at", datetime.utcnow().isoformat()),
        }
        self.db.datasets.update_one(
            {"dataset_id": record["dataset_id"]},
            {"$set": record},
            upsert=True,
        )
        return record["dataset_id"]

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.datasets.find_one({"dataset_id": dataset_id})
        return serialize_doc(doc)

    # --- Runs ---
    def create_run(self, run_id: str, dataset_id: str, max_iterations: int = 3) -> Dict[str, Any]:
        record = {
            "run_id": run_id,
            "dataset_id": dataset_id,
            "status": "queued",
            "current_stage": "queued",
            "iteration": 0,
            "max_iterations": max_iterations,
            "initial_score": None,
            "final_score": None,
            "score_improvement": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "error": None,
        }
        self.db.runs.insert_one(record)
        return record

    def update_run(self, run_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        updates["updated_at"] = datetime.utcnow().isoformat()
        self.db.runs.update_one({"run_id": run_id}, {"$set": updates})
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.runs.find_one({"run_id": run_id})
        return serialize_doc(doc)

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self.db.runs.find().sort("created_at", -1).limit(limit)
        return [serialize_doc(doc) for doc in cursor]

    # --- Agent States Timeline ---
    def save_agent_state(self, run_id: str, node: str, iteration: int, state_snapshot: Dict[str, Any]) -> str:
        record = {
            "run_id": run_id,
            "node": node,
            "iteration": iteration,
            "state": state_snapshot,
            "timestamp": datetime.utcnow().isoformat(),
        }
        res = self.db.agent_states.insert_one(record)
        return str(res.inserted_id)

    def get_agent_states(self, run_id: str) -> List[Dict[str, Any]]:
        cursor = self.db.agent_states.find({"run_id": run_id}).sort("timestamp", 1)
        return [serialize_doc(doc) for doc in cursor]

    # --- Cleaning Logs ---
    def save_cleaning_logs(self, run_id: str, logs: List[Dict[str, Any]]):
        if not logs:
            return
        records = [
            {
                "run_id": run_id,
                **entry,
                "recorded_at": datetime.utcnow().isoformat(),
            }
            for entry in logs
        ]
        self.db.cleaning_logs.insert_many(records)

    def get_cleaning_logs(self, run_id: str) -> List[Dict[str, Any]]:
        cursor = self.db.cleaning_logs.find({"run_id": run_id}).sort("timestamp", 1)
        return [serialize_doc(doc) for doc in cursor]

    # --- LLM Calls ---
    def log_llm_call(
        self,
        prompt: str,
        response_raw: str,
        parsed_data: Optional[Dict[str, Any]] = None,
        latency_ms: float = 0.0,
        model: str = "",
        run_id: Optional[str] = None,
        error: Optional[str] = None,
    ):
        record = {
            "run_id": run_id,
            "model": model,
            "prompt": prompt,
            "response_raw": response_raw,
            "parsed_data": parsed_data,
            "latency_ms": latency_ms,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        }
        try:
            self.db.llm_calls.insert_one(record)
        except Exception:
            pass

    # --- Reports ---
    def save_report(self, run_id: str, report_data: Dict[str, Any]):
        record = {
            "run_id": run_id,
            **report_data,
            "generated_at": datetime.utcnow().isoformat(),
        }
        self.db.reports.update_one(
            {"run_id": run_id},
            {"$set": record},
            upsert=True,
        )

    def get_report(self, run_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.reports.find_one({"run_id": run_id})
        return serialize_doc(doc)


repo = DBRepository()
