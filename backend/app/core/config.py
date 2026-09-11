"""
Application configuration, loaded from environment variables.
Keeps all tunables (limits, provider selection, DB URL) in one place
so services never read os.environ directly.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./document_intelligence.db"

    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-oss-120b"
    llm_base_url: str = "https://api.groq.com/openai/v1"

    ocr_provider: str = "tesseract"
    ocr_api_key: str = ""
    tesseract_cmd: str = ""  # e.g. C:\Program Files\Tesseract-OCR\tesseract.exe on Windows
    # leave blank on Linux/Mac if tesseract is already on PATH

    max_page_count: int = 3
    allowed_file_types: str = "application/pdf,image/jpeg,image/png"

    # Comma-separated frontend origin(s) allowed to call this API, e.g.
    # "https://your-frontend.onrender.com". Defaults to "*" for local
    # dev -- MUST be narrowed to the real deployed frontend origin(s)
    # before going live, or any site can call this API on a user's behalf.
    allowed_origins: str = "*"

    class Config:
        env_file = ".env"

    @property
    def allowed_file_types_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_file_types.split(",")]

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()