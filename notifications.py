# notifications.py
import os
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_message(message: str):
    """
    Sends a message to the pre-configured Telegram chat using a direct HTTP request.
    This method is more robust for handling special characters in the message.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram environment variables (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) not set. Skipping notification.")
        return

    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Let the httpx library handle URL encoding by passing parameters as a dictionary
    params = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()  # Will raise an exception for 4xx/5xx responses
        print("Successfully sent Telegram notification.")
    except httpx.HTTPStatusError as e:
        print(f"Error sending Telegram notification: HTTP Status {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"An unexpected error occurred sending Telegram notification: {e}") 