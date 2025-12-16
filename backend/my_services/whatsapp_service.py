from twilio.rest import Client
import os

def send_whatsapp(message: str):
    account_sid = os.getenv("TWILIO_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_whatsapp = os.getenv("TWILIO_WHATSAPP_FROM")
    to_whatsapp = os.getenv("ADMIN_WHATSAPP_TO")

    client = Client(account_sid, auth_token)
    client.messages.create(
        body=message,
        from_=f'whatsapp:{from_whatsapp}',
        to=f'whatsapp:{to_whatsapp}'
    )
