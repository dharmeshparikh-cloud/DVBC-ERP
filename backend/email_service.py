import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional
import os
from pathlib import Path

class EmailService:
    """Email service using SMTP/Gmail"""
    
    def __init__(self, sender_email: str, sender_password: Optional[str] = None):
        self.sender_email = sender_email
        self.sender_password = sender_password or os.environ.get('SMTP_PASSWORD')
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        cc_emails: Optional[List[str]] = None,
        attachment_path: Optional[str] = None,
        attachment_name: Optional[str] = None
    ) -> dict:
        """
        Send email via SMTP
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body (HTML supported)
            cc_emails: List of CC email addresses
            attachment_path: Path to attachment file
            attachment_name: Name for the attachment
            
        Returns:
            dict with success status and message
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Add body
            # Convert plain text to HTML if not already HTML
            if '<html>' not in body.lower():
                html_body = body.replace('\n', '<br>').replace('**', '<strong>').replace('**', '</strong>')
                html_body = f"<html><body style='font-family: Arial, sans-serif;'><pre style='font-family: Arial, sans-serif; white-space: pre-wrap;'>{html_body}</pre></body></html>"
            else:
                html_body = body
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Add attachment if provided
            if attachment_path and Path(attachment_path).exists():
                with open(attachment_path, 'rb') as f:
                    attach = MIMEApplication(f.read(), _subtype='pdf')
                    attach.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=attachment_name or Path(attachment_path).name
                    )
                    msg.attach(attach)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                
                # If password is not provided, try without authentication (for development)
                if self.sender_password:
                    server.login(self.sender_email, self.sender_password)
                
                recipients = [to_email]
                if cc_emails:
                    recipients.extend(cc_emails)
                
                server.send_message(msg)
            
            return {
                'success': True,
                'message': f'Email sent successfully to {to_email}',
                'recipient': to_email
            }
            
        except smtplib.SMTPAuthenticationError:
            return {
                'success': False,
                'message': 'SMTP authentication failed. Please check email credentials.',
                'error': 'authentication_failed'
            }
        except smtplib.SMTPException as e:
            return {
                'success': False,
                'message': f'SMTP error: {str(e)}',
                'error': 'smtp_error'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to send email: {str(e)}',
                'error': 'general_error'
            }

def create_mock_email_service():
    """Create a mock email service for testing (logs to console)"""
    class MockEmailService:
        def __init__(self, sender_email: str, sender_password: Optional[str] = None):
            self.sender_email = sender_email
        
        def send_email(self, to_email: str, subject: str, body: str, 
                      cc_emails: Optional[List[str]] = None,
                      attachment_path: Optional[str] = None,
                      attachment_name: Optional[str] = None) -> dict:
            print(f"\n{'='*60}")
            print(f"📧 MOCK EMAIL SENT")
            print(f"{'='*60}")
            print(f"From: {self.sender_email}")
            print(f"To: {to_email}")
            if cc_emails:
                print(f"CC: {', '.join(cc_emails)}")
            print(f"Subject: {subject}")
            print(f"\nBody:\n{body}")
            if attachment_path:
                print(f"\nAttachment: {attachment_name or attachment_path}")
            print(f"{'='*60}\n")
            
            return {
                'success': True,
                'message': f'Mock email logged to console',
                'recipient': to_email,
                'mock': True
            }
    
    return MockEmailService