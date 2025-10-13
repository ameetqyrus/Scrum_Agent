"""Email service for sending reports and notifications."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime

from .config import config

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""
    
    def __init__(self):
        self.smtp_host = config.email_smtp_host
        self.smtp_port = config.email_smtp_port
        self.from_address = config.email_from_address
        self.password = config.email_password
        self.enabled = config.get('email.enabled', True)
    
    def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """Send an email."""
        if not self.enabled:
            logger.info(f"Email sending disabled. Would have sent: {subject}")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_address
            msg['To'] = ', '.join(to_addresses)
            
            if reply_to:
                msg['Reply-To'] = reply_to
            elif config.get('email.reply_to'):
                msg['Reply-To'] = config.get('email.reply_to')
            
            # Attach parts
            part1 = MIMEText(body_text, 'plain')
            msg.attach(part1)
            
            if body_html and config.get('email.use_html', True):
                part2 = MIMEText(body_html, 'html')
                msg.attach(part2)
            
            # Send email
            logger.info(f"Sending email to {to_addresses}: {subject}")
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_address, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_daily_report(self, report_html: str, report_text: str, report_date: datetime) -> bool:
        """Send daily report email."""
        subject = f"📊 Daily Scrum Report - {report_date.strftime('%B %d, %Y')}"
        to_addresses = [config.user_email]
        
        return self.send_email(
            to_addresses=to_addresses,
            subject=subject,
            body_text=report_text,
            body_html=report_html
        )
    
    def send_follow_up_notification(
        self,
        issue_key: str,
        issue_summary: str,
        assignee_email: str,
        reason: str
    ) -> bool:
        """Send follow-up notification email."""
        subject = f"⏰ Follow-up needed: {issue_key} - {issue_summary}"
        
        body_text = f"""
Hello,

This is a friendly reminder that the following issue needs attention:

Issue: {issue_key}
Summary: {issue_summary}

Reason: {reason}

Please provide an update or let us know if you're blocked.

View issue: {config.jira_url}browse/{issue_key}

Thanks!
Your Scrum Master Agent 🤖
"""
        
        body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #0052CC;">⏰ Follow-up Needed</h2>
        
        <div style="background-color: #f4f5f7; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p><strong>Issue:</strong> <a href="{config.jira_url}browse/{issue_key}" style="color: #0052CC;">{issue_key}</a></p>
            <p><strong>Summary:</strong> {issue_summary}</p>
        </div>
        
        <p><strong>Reason:</strong> {reason}</p>
        
        <p>Please provide an update or let us know if you're blocked.</p>
        
        <a href="{config.jira_url}browse/{issue_key}" 
           style="display: inline-block; background-color: #0052CC; color: white; padding: 10px 20px; 
                  text-decoration: none; border-radius: 5px; margin-top: 20px;">
            View Issue
        </a>
        
        <p style="margin-top: 30px; color: #666; font-size: 12px;">
            This is an automated message from your Scrum Master Agent 🤖
        </p>
    </div>
</body>
</html>
"""
        
        return self.send_email(
            to_addresses=[assignee_email],
            subject=subject,
            body_text=body_text,
            body_html=body_html
        )


# Global email service instance
email_service = EmailService()


