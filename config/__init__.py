import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

def get_data_dir() -> Path:
    """
    Resolves AGENTX_DATA_DIR per Rule 8.
    Checks the environment variable first, then falls back to ./data or project root.
    """
    env_dir = os.environ.get("AGENTX_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.exists():
            return p

    local_data = BASE_DIR / "data"
    if local_data.exists():
        return local_data

    return BASE_DIR

def resolve_data_file(filename: str) -> Path:
    """Finds a dataset file inside AGENTX_DATA_DIR or ./data fallback."""
    primary = get_data_dir() / filename
    if primary.exists():
        return primary
    fallback = BASE_DIR / "data" / filename
    if fallback.exists():
        return fallback
    return primary

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_ITERATIONS = 5
