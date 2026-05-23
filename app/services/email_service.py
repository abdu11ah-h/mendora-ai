import os
import resend
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
MAIL_FROM = os.getenv("MAIL_FROM", "onboarding@resend.dev")


def mail_configured() -> bool:
    return bool(os.getenv("RESEND_API_KEY", "").strip())


async def send_email(to_email: str, subject: str, html_content: str) -> bool:
    try:
        resend.Emails.send({
            "from": MAIL_FROM,
            "to": to_email,
            "subject": subject,
            "html": html_content,
        })
        return True
    except Exception as e:
        print(f"[Email Error] {e}")
        return False

async def send_verification_email(to_email: str, token: str) -> bool:
    link = f"{FRONTEND_URL}/verify-email?token={token}"
    html = f"""<div style="font-family:sans-serif;padding:40px;background:#0A0A14;color:#F1F0FF;">
    <h2 style="color:#A78BFA;">Verify your Mendora AI account</h2>
    <p>Click the button below to verify your email. Link expires in 24 hours.</p>
    <a href="{link}" style="background:#7C3AED;color:white;padding:14px 32px;border-radius:12px;text-decoration:none;font-weight:700;display:inline-block;margin:20px 0;">Verify Email →</a>
    <p style="color:#6B7280;font-size:12px;">If you didn't create a Mendora account, ignore this email.</p>
    </div>"""
    return await send_email(to_email, "Verify your Mendora AI account", html)

async def send_password_reset_email(to_email: str, token: str) -> bool:
    link = f"{FRONTEND_URL}/reset-password?token={token}"
    html = f"""<div style="font-family:sans-serif;padding:40px;background:#0A0A14;color:#F1F0FF;">
    <h2 style="color:#A78BFA;">Reset your Mendora AI password</h2>
    <p>Click the button below to reset your password. Link expires in 1 hour.</p>
    <a href="{link}" style="background:#7C3AED;color:white;padding:14px 32px;border-radius:12px;text-decoration:none;font-weight:700;display:inline-block;margin:20px 0;">Reset Password →</a>
    <p style="color:#6B7280;font-size:12px;">If you didn't request this, ignore this email.</p>
    </div>"""
    return await send_email(to_email, "Reset your Mendora AI password", html)