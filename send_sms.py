import os
import sys
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()  # Load environment variables from .env file

# Initialize Twilio client
account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
client = Client(account_sid, auth_token)
twilio_no = os.environ["TWILIO_FROM_NUMBER"]
my_no = os.environ["MY_NUMBER"]


def send(body: str) -> str:
    if len(body) > 1600:
        raise ValueError("Message body exceeds Twilio's 1600 character limit.")
    if len(body) > 320:
        print(
            f"Warning: Message body is {len(body)} characters long, which exceeds the 320 character limit for a single SMS. It may be split into multiple messages."
        )
    message = client.messages.create(
        body=body,
        from_=twilio_no,
        to=my_no,
    )
    return message.sid


if __name__ == "__main__":
    send(sys.argv[1] if len(sys.argv) > 1 else "Test message from sms-assistant")
