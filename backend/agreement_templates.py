from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import re

class AgreementTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    template_content: str  # HTML/Markdown content
    variables: List[str] = []  # List of variables like {company_name}, {total_amount}, etc.
    is_default: bool = False
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgreementTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    template_content: str
    variables: Optional[List[str]] = []
    is_default: Optional[bool] = False

class EmailNotificationTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    subject: str
    body: str
    template_type: str = 'agreement_notification'  # 'agreement_notification', 'quotation_notification', etc.
    variables: List[str] = []
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmailNotificationTemplateCreate(BaseModel):
    name: str
    subject: str
    body: str
    template_type: Optional[str] = 'agreement_notification'
    variables: Optional[List[str]] = []

class AgreementEmailData(BaseModel):
    agreement_id: str
    email_template_id: str
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None
    recipient_email: str
    cc_emails: Optional[List[str]] = []
    attachment_url: Optional[str] = None

def extract_variables_from_template(template_content: str) -> List[str]:
    """Extract all variables from template content in format {variable_name}"""
    pattern = r'\{([^}]+)\}'
    variables = re.findall(pattern, template_content)
    return list(set(variables))  # Remove duplicates

def substitute_variables(template: str, data: dict) -> str:
    """Replace variables in template with actual data"""
    result = template
    for key, value in data.items():
        placeholder = f"{{{key}}}"
        result = result.replace(placeholder, str(value) if value else '')
    return result

def prepare_agreement_email_data(agreement_data: dict, lead_data: dict, quotation_data: dict, user_data: dict) -> dict:
    """Prepare data dictionary for email template substitution"""
    return {
        'client_name': f"{lead_data.get('first_name', '')} {lead_data.get('last_name', '')}",
        'client_first_name': lead_data.get('first_name', ''),
        'client_last_name': lead_data.get('last_name', ''),
        'company_name': lead_data.get('company', ''),
        'client_email': lead_data.get('email', ''),
        'client_phone': lead_data.get('phone', ''),
        'agreement_number': agreement_data.get('agreement_number', ''),
        'quotation_number': quotation_data.get('quotation_number', ''),
        'total_amount': f"₹{quotation_data.get('grand_total', 0):,.2f}",
        'total_amount_words': number_to_words_indian(quotation_data.get('grand_total', 0)),
        'start_date': agreement_data.get('start_date', ''),
        'end_date': agreement_data.get('end_date', ''),
        'project_duration': 'As per agreement',
        'salesperson_name': user_data.get('full_name', ''),
        'salesperson_email': user_data.get('email', ''),
        'salesperson_phone': user_data.get('phone', 'N/A'),
        'today_date': datetime.now().strftime('%d %B %Y'),
    }

def number_to_words_indian(num: float) -> str:
    """Convert number to Indian rupees words"""
    if num == 0:
        return "Zero Rupees Only"
    
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", 
             "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def convert_hundreds(n):
        if n == 0:
            return ""
        elif n < 10:
            return units[n]
        elif n < 20:
            return teens[n - 10]
        elif n < 100:
            return tens[n // 10] + (" " + units[n % 10] if n % 10 != 0 else "")
        else:
            return units[n // 100] + " Hundred" + (" " + convert_hundreds(n % 100) if n % 100 != 0 else "")
    
    crores = int(num // 10000000)
    lakhs = int((num % 10000000) // 100000)
    thousands = int((num % 100000) // 1000)
    hundreds = int(num % 1000)
    paise = int(round((num - int(num)) * 100))
    
    words = []
    if crores > 0:
        words.append(convert_hundreds(crores) + " Crore")
    if lakhs > 0:
        words.append(convert_hundreds(lakhs) + " Lakh")
    if thousands > 0:
        words.append(convert_hundreds(thousands) + " Thousand")
    if hundreds > 0:
        words.append(convert_hundreds(hundreds))
    
    result = " ".join(words) + " Rupees"
    if paise > 0:
        result += " and " + convert_hundreds(paise) + " Paise"
    result += " Only"
    
    return result

# Default email templates
DEFAULT_AGREEMENT_EMAIL_TEMPLATES = [
    {
        "name": "Professional Agreement Notification",
        "subject": "Agreement for Consulting Services - {agreement_number}",
        "body": """Dear {client_first_name},

Thank you for choosing our consulting services. We are pleased to share the agreement for your upcoming project.

**Agreement Details:**
- Agreement Number: {agreement_number}
- Company: {company_name}
- Total Amount: {total_amount}
- Project Start Date: {start_date}

Please review the attached agreement document. If you have any questions or need clarification, feel free to reach out.

To proceed, kindly review and sign the agreement at your earliest convenience.

Looking forward to a successful partnership!

Best regards,
{salesperson_name}
{salesperson_email}
""",
        "template_type": "agreement_notification"
    },
    {
        "name": "Formal Agreement with Terms",
        "subject": "Consulting Services Agreement - {company_name}",
        "body": """Dear {client_name},

Greetings from DVBC Consulting!

We are delighted to formalize our partnership through this consulting services agreement.

**Project Overview:**
- Agreement Reference: {agreement_number}
- Quotation Reference: {quotation_number}
- Total Project Value: {total_amount} ({total_amount_words})
- Engagement Period: {start_date} to {end_date}

The attached agreement outlines:
• Scope of work and deliverables
• Team deployment details
• Payment schedule and terms
• Project milestones

Please take a moment to review the agreement. Should you have any questions or require modifications, I'm here to assist.

Once you're satisfied, we request you to sign and return the agreement to initiate the project.

We're excited to contribute to {company_name}'s growth journey!

Warm regards,

{salesperson_name}
Consulting Services Team
{salesperson_email}
""",
        "template_type": "agreement_notification"
    },
    {
        "name": "Quick Agreement Notification",
        "subject": "Your Agreement is Ready - {agreement_number}",
        "body": """Hi {client_first_name},

Your consulting services agreement ({agreement_number}) is ready!

📄 Agreement Amount: {total_amount}
📅 Start Date: {start_date}

Please find the agreement attached. Review and let me know if you have any questions.

Thanks!
{salesperson_name}
""",
        "template_type": "agreement_notification"
    }
]