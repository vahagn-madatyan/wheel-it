from dotenv import load_dotenv
import os

load_dotenv(override=True)  # Load from .env file in root

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
IS_PAPER = os.getenv("IS_PAPER", "true").lower() == "true"

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")


def require_finnhub_key() -> str:
    """Return Finnhub API key or raise with actionable message."""
    if not FINNHUB_API_KEY:
        raise EnvironmentError(
            "FINNHUB_API_KEY not found in .env. "
            "Get a free key at https://finnhub.io/register"
        )
    return FINNHUB_API_KEY
