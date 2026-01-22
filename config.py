import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DISCUSSION_CHAT_ID = int(os.getenv("DISCUSSION_CHAT_ID", "0"))
SPAM_THRESHOLD = int(os.getenv("SPAM_THRESHOLD", "5"))
VOTE_TTL_SECONDS = int(os.getenv("VOTE_TTL_SECONDS", "600"))
DATABASE_URL = os.getenv("DATABASE_URL", "")

PROFANITY_WORDS_PATH = os.getenv("PROFANITY_WORDS_PATH", "profanity_words.txt")
