import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configure standardized structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gh-pr-agent")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BOT_HANDLE = os.getenv("BOT_HANDLE", "@pr-bot")
