from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    アプリケーション全体の設定管理。
    環境変数 (.env) からの読み込みをサポートする。
    """
    # API Settings
    NDL_API_BASE_URL: str = "https://kokkai.ndl.go.jp/api/meeting"
    
    # ターゲットの会議ID (デフォルト)
    TARGET_ISSUE_ID: str = "122104339X00320260312"

    # Embedding Settings
    EMBEDDING_MODEL_NAME: str = "intfloat/multilingual-e5-small"
    
    # Data Path Settings
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    RAW_DATA_DIR: Path = DATA_DIR / "raw"
    PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
    VECTOR_DATA_DIR: Path = DATA_DIR / "vector"

    # Pipeline Settings
    BATCH_SIZE: int = 64
    CHUNK_SIZE: int = 2000
    CHUNK_OVERLAP: int = 200

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# グローバルな設定インスタンス
settings = Settings()


def setup_directories():
    """必要なディレクトリを自動生成する。"""
    settings.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.VECTOR_DATA_DIR.mkdir(parents=True, exist_ok=True)
