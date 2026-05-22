import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM = os.getenv("MAIL_FROM", "noreply@mendora.ai")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

VERIFY_EMAIL_TEMPLATE = """<!DOCTYPE html>
<html>
<body style="font-family:Inter,sans-serif;background:#0A0A14;color:#F1F0FF;padding:40px;">
  <div style="max-width:480px;margin:0 auto;background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.3);border-radius:20px;padding:40px;">
    <div style="text-align:center;margin-bottom:32px;">
      <div style="width:60px;height:60px;background:linear-gradient(135deg,#7C3AED,#4F46E5);border-radius:16px;display:inline-flex;align-items:center;justify-content:center;font-size:28px;">✦</div>
      <h1 style="color:#A78BFA;margin:16px 0 4px;">Mendora AI</h1>
      <p style="color:#9CA3AF;font-size:14px;">University Wellness Platform</p>
    </div>
    <h2 style="color:#F1F0FF;text-align:center;margin-bottom:12px;">Verify Your Email</h2>
    <p style="color:#9CA3AF;text-align:center;line-height:1.6;margin-bottom:32px;">
      Click the button below to verify your email and activate your Mendora account.
      This link expires in <strong style="color:#A78BFA;">24 hours</strong>.
    </p>
    <div style="text-align:center;">
      <a href="{verification_link}" style="background:linear-gradient(135deg,#7C3AED,#4F46E5);color:white;padding:14px 32px;border-radius:12px;text-decoration:none;font-weight:700;font-size:15px;display:inline-block;">
        ✦ Verify Email →
      </a>
    </div>
    <p style="color:#6B7280;text-align:center;font-size:12px;margin-top:32px;">
      If you didn't create a Mendora account, you can safely ignore this email.
    </p>
  </div>
</body>
</html>"""

RESET_EMAIL_TEMPLATE = """<!DOCTYPE html>
<html>
<body style="font-family:Inter,sans-serif;background:#0A0A14;color:#F1F0FF;padding:40px;">
  <div style="max-width:480px;margin:0 auto;background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.3);border-radius:20px;padding:40px;">
    <div style="text-align:center;margin-bottom:32px;">
      <div style="width:60px;height:60px;background:linear-gradient(135deg,#7C3AED,#4F46E5);border-radius:16px;display:inline-flex;align-items:center;justify-content:center;font-size:28px;">✦</div>
      <h1 style="color:#A78BFA;margin:16px 0 4px;">Mendora AI</h1>
      <p style="color:#9CA3AF;font-size:14px;">University Wellness Platform</p>
    </div>
    <h2 style="color:#F1F0FF;text-align:center;margin-bottom:12px;">Reset Your Password</h2>
    <p style="color:#9CA3AF;text-align:center;line-height:1.6;margin-bottom:32px;">
      Someone requested a password reset for your account. Click below to set a new password.
      This link expires in <strong style="color:#A78BFA;">1 hour</strong>.
    </p>
    <div style="text-align:center;">
      <a href="{reset_link}" style="background:linear-gradient(135deg,#7C3AED,#4F46E5);color:white;padding:14px 32px;border-radius:12px;text-decoration:none;font-weight:700;font-size:15px;display:inline-block;">
        ✦ Reset Password →
      </a>
    </div>
    <p style="color:#6B7280;text-align:center;font-size:12px;margin-top:32px;">
      If you didn't request this, you can safely ignore this email. Your password won't change.
    </p>
  </div>
</body>
</html>"""


async def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send HTML email via Gmail SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = MAIL_FROM
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_FROM, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[Email Error] {e}")
        return False


async def send_verification_email(to_email: str, token: str) -> bool:
    link = f"{FRONTEND_URL}/verify-email?token={token}"
    html = VERIFY_EMAIL_TEMPLATE.replace("{verification_link}", link)
    return await send_email(to_email, "Verify your Mendora AI account", html)


async def send_password_reset_email(to_email: str, token: str) -> bool:
    link = f"{FRONTEND_URL}/reset-password?token={token}"
    html = RESET_EMAIL_TEMPLATE.replace("{reset_link}", link)
    return await send_email(to_email, "Reset your Mendora AI password", html)
