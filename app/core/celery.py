import logging
from celery import Celery
from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "app_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Example background task
@celery_app.task(name="app.tasks.send_verification_email")
def send_verification_email(email: str, code: str):
    logger.info(f"Background task: Sending verification code {code} to {email}")
    # Simulating sending email via SMTP or third party provider
    return f"Verification sent to {email}"

@celery_app.task(name="app.tasks.scan_apk_file")
def scan_apk_file(file_path: str):
    logger.info(f"Background task: Initiating anti-virus scan on {file_path}")
    from app.utils.scanner import scan_file
    import os
    
    result = scan_file(file_path)
    if result.get("status") == "infected":
        logger.error(f"SECURITY ALERT: File {file_path} is infected! Threat: {result.get('message')}. Initiating immediate purge.")
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Infected file {file_path} has been purged successfully.")
        except Exception as e:
            logger.critical(f"Failed to purge infected file {file_path}: {str(e)}")
            
    return result

