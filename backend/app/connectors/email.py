import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from app.config import settings
from app.connectors.base import ExternalRef

logger = logging.getLogger(__name__)

class EmailConnector:
    type: str = "email"

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL

    def notify(self, user_email: str, summary: str, link: str) -> None:
        """Sends an HTML notification email with summary and issue report link."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Pipeline Triage] Action Required: Build Failure"
        msg["From"] = self.from_email
        msg["To"] = user_email

        plain_text = f"Build failure alert:\n\n{summary}\n\nView the full triage report and fix steps: {link}\n"
        html_text = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; padding: 24px;">
              <h2 style="color: #0f172a; margin-top: 0;">Build Failure Detected</h2>
              <p style="color: #334155; line-height: 1.5;">{summary}</p>
              <div style="margin: 24px 0;">
                <a href="{link}" style="background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: bold; display: inline-block;">
                  View Triage Report &amp; Fix Steps
                </a>
              </div>
              <p style="font-size: 12px; color: #64748b; margin-bottom: 0;">
                Sent automatically by Pipeline Triage within the 2-minute SLA.
              </p>
            </div>
          </body>
        </html>
        """

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_text, "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, [user_email], msg.as_string())
            logger.info(f"Notification email sent to {user_email} via {self.smtp_host}:{self.smtp_port}")
        except Exception as e:
            logger.error(f"Failed to send email to {user_email}: {e}")
            raise e

    def create_task(self, issue: Any) -> ExternalRef:
        return ExternalRef(task_id="email_only")

    def assign(self, ref: ExternalRef, user_identifier: str) -> None:
        pass

    def update_status(self, ref: ExternalRef, status: str) -> None:
        pass

    def comment(self, ref: ExternalRef, text: str) -> None:
        pass
