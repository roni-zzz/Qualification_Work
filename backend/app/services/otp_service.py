import random
import time
import smtplib
from email.mime.text import MIMEText
from app.config import settings

# In-memory store: { email: { "code": "123456", "expires": timestamp } }
_otp_store: dict = {}

OTP_EXPIRY_SECONDS = 300  # 5 minutes


def generate_otp(email: str) -> str:
    code = str(random.randint(100000, 999999))
    _otp_store[email] = {
        "code": code,
        "expires": time.time() + OTP_EXPIRY_SECONDS
    }
    return code


def verify_otp(email: str, code: str) -> bool:
    entry = _otp_store.get(email)
    if not entry:
        return False
    if time.time() > entry["expires"]:
        del _otp_store[email]
        return False
    if entry["code"] != code:
        return False
    del _otp_store[email]  # one-time use
    return True


def send_otp_email(email: str, code: str):
    sender = (settings.smtp_sender or "").strip()
    password = (settings.smtp_password or "").strip()
    if not sender or not password:
        raise RuntimeError(
            "SMTP is not configured: set SMTP_SENDER and SMTP_PASSWORD in backend .env "
            "(Gmail: use an app password for the sender account)."
        )

    msg = MIMEText(
        f"Your Guidewire Warehouse Security verification code is: {code}\n\n"
        f"This code expires in 5 minutes. Do not share it with anyone."
    )
    msg["Subject"] = "Your Login Verification Code"
    msg["From"] = sender
    msg["To"] = email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, email, msg.as_string())