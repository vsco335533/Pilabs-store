import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

async def send_otp_email(to_email: str, otp_code: str, otp_type: str = "email_verification") -> bool:
    """
    Sends an OTP email using Brevo HTTP API.
    """
    if not settings.BREVO_API_KEY:
        logger.warning(f"BREVO_API_KEY not configured. Mocking email send of {otp_type} OTP {otp_code} to {to_email}")
        return True

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
        "accept": "application/json"
    }

    if otp_type == "email_verification":
        subject = f"Verify Your Account - {settings.PROJECT_NAME}"
        title = "Account Verification"
        message_body = "Thank you for registering. Use the following verification code to verify your account:"
    elif otp_type == "password_reset":
        subject = f"Reset Your Password - {settings.PROJECT_NAME}"
        title = "Password Reset Request"
        message_body = "We received a request to reset your password. Use the following code to reset it:"
    else:
        subject = f"Verification Code - {settings.PROJECT_NAME}"
        title = "Verification Code"
        message_body = "Your verification code is:"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{subject}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background-color: #f8fafc;
                margin: 0;
                padding: 0;
            }}
            .wrapper {{
                width: 100%;
                table-layout: fixed;
                background-color: #f8fafc;
                padding: 40px 0;
            }}
            .container {{
                max-width: 500px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 4px 25px rgba(0, 0, 0, 0.05);
                border: 1px solid #e2e8f0;
            }}
            .header {{
                background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                padding: 35px 30px;
                text-align: center;
            }}
            .logo {{
                font-size: 26px;
                font-weight: 800;
                color: #ffffff;
                letter-spacing: -0.5px;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            .content {{
                padding: 40px 35px;
                text-align: center;
            }}
            h2 {{
                font-size: 22px;
                font-weight: 700;
                color: #0f172a;
                margin-top: 0;
                margin-bottom: 12px;
            }}
            p {{
                font-size: 15px;
                line-height: 24px;
                color: #475569;
                margin: 0 0 24px 0;
            }}
            .otp-box {{
                display: inline-block;
                margin: 10px auto 30px auto;
                background-color: #f8fafc;
                border: 2px solid #e2e8f0;
                color: #4f46e5;
                font-size: 36px;
                font-weight: 800;
                letter-spacing: 6px;
                padding: 16px 36px;
                border-radius: 12px;
                box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.02);
            }}
            .footer {{
                background-color: #f8fafc;
                padding: 24px 30px;
                text-align: center;
                border-top: 1px solid #f1f5f9;
            }}
            .footer p {{
                font-size: 12px;
                color: #94a3b8;
                margin: 0;
                line-height: 18px;
            }}
        </style>
    </head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="header">
                    <span class="logo">π Labs Store</span>
                </div>
                <div class="content">
                    <h2>{title}</h2>
                    <p>{message_body}</p>
                    <div class="otp-box">{otp_code}</div>
                    <p style="font-size: 13px; color: #94a3b8; margin-bottom: 0;">This code is valid for 15 minutes. If you did not request this verification, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; {settings.PROJECT_NAME}. All rights reserved.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    payload = {
        "sender": {
            "name": settings.BREVO_SENDER_NAME,
            "email": settings.BREVO_SENDER_EMAIL
        },
        "to": [
            {
                "email": to_email
            }
        ],
        "subject": subject,
        "htmlContent": html_content
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code in [200, 201, 202]:
                logger.info(f"Successfully sent {otp_type} email to {to_email}")
                return True
            else:
                logger.error(f"Failed to send Brevo email. Status: {response.status_code}, Response: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Exception raised while sending email to {to_email}: {str(e)}")
        return False
