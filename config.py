import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")


def has_youtube_api() -> bool:
    return bool(YOUTUBE_API_KEY)


def validate():
    if not OPENAI_API_KEY:
        raise SystemExit("OPENAI_API_KEY not set in .env")
