# notifications.py
import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_message(message: str):
    """
    Sends a message to the pre-configured Telegram chat using urllib (standard library).
    This approach avoids any third-party library issues.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram environment variables (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) not set. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Prepare the data as JSON
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    # Convert to JSON and encode to bytes
    json_data = json.dumps(data)
    data_bytes = json_data.encode('utf-8')
    
    # Create the request
    request = urllib.request.Request(
        url,
        data=data_bytes,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(request) as response:
            result = response.read().decode('utf-8')
            print("Successfully sent Telegram notification.")
    except urllib.error.HTTPError as e:
        error_content = e.read().decode('utf-8')
        print(f"Error sending Telegram notification: HTTP Status {e.code} - {error_content}")
    except Exception as e:
        print(f"An unexpected error occurred sending Telegram notification: {e}") 