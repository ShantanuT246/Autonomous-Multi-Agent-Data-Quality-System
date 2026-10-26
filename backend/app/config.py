from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini LLM Settings
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"
    LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT_SECONDS: int = 45

    # MongoDB Settings
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "autonomous_data_quality"

    # Storage Paths
    OUTPUT_DIR: Path = Path("reports")
    STORAGE_DIR: Path = Path("backend/storage")

    # API Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Pipeline & Guardrail Settings
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_ITERATIONS: int = 3
    MAX_ROW_LOSS_RATIO: float = 0.20

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("OUTPUT_DIR", "STORAGE_DIR", mode="after")
    @classmethod
    def ensure_directories_exist(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v


settings = Settings()
