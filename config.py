from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Environment variable {name} must be an integer")


@dataclass
class Settings:
    bot_token: str
    discussion_chat_id: int
    spam_threshold: int = 5
    vote_ttl_seconds: int = 600
    database_url: str | None = None



def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN is required")

    discussion_chat_id = os.getenv("DISCUSSION_CHAT_ID")
    if not discussion_chat_id:
        raise ValueError("DISCUSSION_CHAT_ID is required")

    database_url = os.getenv("DATABASE_URL")

    return Settings(
        bot_token=bot_token,
        discussion_chat_id=int(discussion_chat_id),
        spam_threshold=_get_env_int("SPAM_THRESHOLD", 5),
        vote_ttl_seconds=_get_env_int("VOTE_TTL_SECONDS", 600),
        database_url=database_url,
    )
