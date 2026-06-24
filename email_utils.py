import os
import smtplib
from email.mime.text import MIMEText


def send_email(subject: str, body: str) -> None:
    """環境変数の設定でメールを送信する(Gmailのアプリパスワード利用を想定)"""
    sender = os.environ["EMAIL_FROM"]
    receiver = os.environ["EMAIL_TO"]
    app_password = os.environ["EMAIL_APP_PASSWORD"]
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender, app_password)
        server.sendmail(sender, receiver, msg.as_string())
