from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
import uuid

class EmailTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = uuid.uuid4().__str__()
    name: str
    subject: str
    body: str
    template_type: str  # 'proposal', 'demo_request', 'follow_up', 'thank_you'
    variables: Optional[List[str]] = []  # e.g., ['first_name', 'company', 'job_title']
    created_by: str
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

class EmailTemplateCreate(BaseModel):
    name: str
    subject: str
    body: str
    template_type: str
    variables: Optional[List[str]] = []

class FollowUpReminder(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = uuid.uuid4().__str__()
    lead_id: str
    reminder_type: str  # 'send_proposal', 'schedule_demo', 'follow_up_call'
    message: str
    priority: str  # 'high', 'medium', 'low'
    due_date: Optional[datetime] = None
    is_completed: bool = False
    created_by: str
    created_at: datetime = datetime.now(timezone.utc)
    completed_at: Optional[datetime] = None

class FollowUpReminderCreate(BaseModel):
    lead_id: str
    reminder_type: str
    message: str
    priority: str = 'medium'
    due_date: Optional[datetime] = None

class AutomatedSuggestion(BaseModel):
    lead_id: str
    lead_name: str
    lead_score: int
    suggestion_type: str
    suggestion_message: str
    template_id: Optional[str] = None
    created_at: datetime = datetime.now(timezone.utc)

def generate_email_from_template(template: EmailTemplate, lead_data: dict) -> dict:
    """Replace template variables with actual lead data"""
    subject = template.subject
    body = template.body
    
    # Replace variables
    for var in template.variables:
        if var in lead_data:
            placeholder = f"{{{var}}}"
            value = lead_data.get(var, '')
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
    
    return {
        'subject': subject,
        'body': body,
        'template_name': template.name
    }

def check_lead_for_suggestions(lead_data: dict) -> List[AutomatedSuggestion]:
    """Generate automated suggestions based on lead score and status"""
    suggestions = []
    lead_score = lead_data.get('lead_score', 0)
    status = lead_data.get('status', 'new')
    lead_id = lead_data.get('id')
    lead_name = f"{lead_data.get('first_name', '')} {lead_data.get('last_name', '')}"
    
    # High-scoring leads (70+) should get proposal/demo suggestions
    if lead_score >= 70:
        if status in ['new', 'contacted']:
            suggestions.append(AutomatedSuggestion(
                lead_id=lead_id,
                lead_name=lead_name,
                lead_score=lead_score,
                suggestion_type='send_proposal',
                suggestion_message=f"🔥 Hot Lead Alert! {lead_name} has a score of {lead_score}. Consider sending a proposal or scheduling a demo call."
            ))
    
    # Medium-scoring leads (60-69) need nurturing
    elif lead_score >= 60:
        if status == 'contacted':
            suggestions.append(AutomatedSuggestion(
                lead_id=lead_id,
                lead_name=lead_name,
                lead_score=lead_score,
                suggestion_type='follow_up',
                suggestion_message=f"💡 Warm Lead: {lead_name} (score: {lead_score}) should receive a follow-up within 3 days."
            ))
    
    # Qualified leads should move to proposal
    if status == 'qualified' and lead_score >= 50:
        suggestions.append(AutomatedSuggestion(
            lead_id=lead_id,
            lead_name=lead_name,
            lead_score=lead_score,
            suggestion_type='send_proposal',
            suggestion_message=f"✅ Qualified Lead: {lead_name} is ready for a proposal. Strike while the iron is hot!"
        ))
    
    return suggestions