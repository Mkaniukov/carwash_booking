import smtplib
from email.message import EmailMessage
import os

def send_email(to, subject, body):
    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(os.getenv("SMTP_HOST"), 587) as s:
        s.starttls()
        s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        s.send_message(msg)
