"""
Sales Funnel Email Notifications
HTML email templates for key milestones in the sales funnel
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

# Base HTML template with DVBC branding
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" style="width: 100%; max-width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px 40px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">
                                DVBC - NETRA
                            </h1>
                            <p style="margin: 8px 0 0 0; color: #a0a0a0; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;">
                                Sales Funnel Update
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Status Badge -->
                    <tr>
                        <td style="padding: 30px 40px 0 40px; text-align: center;">
                            <span style="display: inline-block; background-color: {badge_color}; color: white; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: 600;">
                                {badge_text}
                            </span>
                        </td>
                    </tr>
                    
                    <!-- Title -->
                    <tr>
                        <td style="padding: 20px 40px 10px 40px; text-align: center;">
                            <h2 style="margin: 0; color: #1a1a2e; font-size: 22px; font-weight: 600;">
                                {headline}
                            </h2>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 10px 40px 30px 40px;">
                            {content}
                        </td>
                    </tr>
                    
                    <!-- Details Table -->
                    {details_section}
                    
                    <!-- Action Button -->
                    {action_section}
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 25px 40px; border-top: 1px solid #e9ecef;">
                            <table role="presentation" style="width: 100%;">
                                <tr>
                                    <td style="text-align: center;">
                                        <p style="margin: 0 0 10px 0; color: #6c757d; font-size: 12px;">
                                            This is an automated notification from NETRA ERP
                                        </p>
                                        <p style="margin: 0; color: #adb5bd; font-size: 11px;">
                                            © {year} DVBC Consulting. All rights reserved.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def _build_details_table(details: List[Dict[str, str]]) -> str:
    """Build HTML details table from key-value pairs"""
    if not details:
        return ""
    
    rows = ""
    for item in details:
        rows += f"""
            <tr>
                <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; color: #6c757d; font-size: 13px; width: 40%;">
                    {item.get('label', '')}
                </td>
                <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; color: #1a1a2e; font-size: 13px; font-weight: 500;">
                    {item.get('value', '')}
                </td>
            </tr>
        """
    
    return f"""
        <tr>
            <td style="padding: 0 40px 30px 40px;">
                <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #f8f9fa; border-radius: 8px; overflow: hidden;">
                    {rows}
                </table>
            </td>
        </tr>
    """


def _build_action_button(text: str, url: str, color: str = "#3b82f6") -> str:
    """Build action button HTML"""
    return f"""
        <tr>
            <td style="padding: 0 40px 30px 40px; text-align: center;">
                <a href="{url}" style="display: inline-block; background-color: {color}; color: white; text-decoration: none; padding: 14px 30px; border-radius: 8px; font-size: 14px; font-weight: 600;">
                    {text}
                </a>
            </td>
        </tr>
    """


def _build_list_section(title: str, items: List[str], icon: str = "•") -> str:
    """Build bulleted list section"""
    if not items:
        return ""
    
    list_items = "".join([f"<li style='margin-bottom: 8px; color: #374151;'>{item}</li>" for item in items if item])
    
    return f"""
        <div style="margin-top: 20px;">
            <h4 style="margin: 0 0 10px 0; color: #1a1a2e; font-size: 14px; font-weight: 600;">{title}</h4>
            <ul style="margin: 0; padding-left: 20px; font-size: 13px;">
                {list_items}
            </ul>
        </div>
    """


# ============== Email Templates ==============

def meeting_mom_filled_email(
    lead_name: str,
    company: str,
    meeting_title: str,
    meeting_date: str,
    meeting_type: str,
    attendees: List[str],
    mom_summary: str,
    client_expectations: List[str],
    key_commitments: List[str],
    salesperson_name: str,
    app_url: str
) -> Dict[str, str]:
    """
    Email template for when MOM is filled after a meeting
    """
    details = [
        {"label": "Lead", "value": f"{lead_name} ({company})"},
        {"label": "Meeting", "value": meeting_title},
        {"label": "Date", "value": meeting_date},
        {"label": "Type", "value": meeting_type},
        {"label": "Attendees", "value": ", ".join(attendees) if attendees else "N/A"},
        {"label": "Recorded By", "value": salesperson_name}
    ]
    
    content = f"""
        <p style="margin: 0; color: #4b5563; font-size: 15px; line-height: 1.6;">
            A new meeting has been recorded with Minutes of Meeting (MOM) for <strong>{company}</strong>.
        </p>
        
        <div style="margin-top: 20px; padding: 15px; background-color: #eff6ff; border-left: 4px solid #3b82f6; border-radius: 4px;">
            <h4 style="margin: 0 0 8px 0; color: #1e40af; font-size: 13px;">MOM Summary</h4>
            <p style="margin: 0; color: #1e3a5f; font-size: 13px; line-height: 1.5;">{mom_summary}</p>
        </div>
        
        {_build_list_section("Client Expectations", client_expectations)}
        {_build_list_section("Key Commitments", key_commitments)}
    """
    
    html = BASE_TEMPLATE.format(
        title="Meeting MOM Recorded - NETRA",
        badge_color="#10b981",
        badge_text="MOM RECORDED",
        headline=f"Meeting Completed: {company}",
        content=content,
        details_section=_build_details_table(details),
        action_section=_build_action_button("View in Sales Funnel", f"{app_url}/leads", "#3b82f6"),
        year=datetime.now().year
    )
    
    return {
        "subject": f"📋 MOM Recorded: {meeting_title} - {company}",
        "html": html,
        "plain": f"Meeting MOM recorded for {company}.\n\nMOM Summary: {mom_summary}\n\nRecorded by: {salesperson_name}"
    }


def proforma_generated_email(
    lead_name: str,
    company: str,
    quotation_number: str,
    quotation_id: str,
    total_amount: float,
    currency: str,
    valid_until: str,
    items_count: int,
    payment_terms: str,
    salesperson_name: str,
    client_email: str,
    app_url: str
) -> Dict[str, str]:
    """
    Email template for when proforma/quotation is generated.
    Includes view/download links for client.
    """
    formatted_amount = f"{currency} {total_amount:,.2f}"
    view_url = f"{app_url}/quotations/{quotation_id}"
    download_url = f"{app_url}/api/quotations/{quotation_id}/download"
    
    details = [
        {"label": "Lead", "value": f"{lead_name} ({company})"},
        {"label": "Quotation No.", "value": quotation_number},
        {"label": "Total Amount", "value": formatted_amount},
        {"label": "Items", "value": f"{items_count} line item(s)"},
        {"label": "Valid Until", "value": valid_until},
        {"label": "Payment Terms", "value": payment_terms or "As per agreement"},
        {"label": "Created By", "value": salesperson_name},
        {"label": "Client Email", "value": client_email or "N/A"}
    ]
    
    content = f"""
        <p style="margin: 0; color: #4b5563; font-size: 15px; line-height: 1.6;">
            A new proforma invoice has been generated for <strong>{company}</strong>.
        </p>
        
        <div style="margin-top: 20px; padding: 20px; background-color: #fef3c7; border-radius: 8px; text-align: center;">
            <p style="margin: 0 0 5px 0; color: #92400e; font-size: 12px; text-transform: uppercase;">Total Value</p>
            <p style="margin: 0; color: #78350f; font-size: 28px; font-weight: 700;">{formatted_amount}</p>
        </div>
        
        <!-- Action Links -->
        <div style="margin-top: 20px; padding: 15px; background-color: #f0f9ff; border-radius: 8px;">
            <p style="margin: 0 0 10px 0; color: #0369a1; font-size: 13px; font-weight: 600;">Quick Actions</p>
            <table role="presentation" style="width: 100%;">
                <tr>
                    <td style="padding: 5px 0;">
                        <a href="{view_url}" style="color: #0284c7; text-decoration: none; font-size: 13px;">📄 View Quotation</a>
                    </td>
                    <td style="padding: 5px 0;">
                        <a href="{download_url}" style="color: #0284c7; text-decoration: none; font-size: 13px;">⬇️ Download PDF</a>
                    </td>
                </tr>
            </table>
        </div>
    """
    
    html = BASE_TEMPLATE.format(
        title="Proforma Generated - NETRA",
        badge_color="#f59e0b",
        badge_text="QUOTATION READY",
        headline=f"Proforma Invoice: {quotation_number}",
        content=content,
        details_section=_build_details_table(details),
        action_section=_build_action_button("View Quotation", view_url, "#f59e0b"),
        year=datetime.now().year
    )
    
    return {
        "subject": f"📄 Proforma #{quotation_number} Generated - {company} ({formatted_amount})",
        "html": html,
        "plain": f"Proforma invoice generated for {company}.\n\nQuotation: {quotation_number}\nAmount: {formatted_amount}\nView: {view_url}\nDownload: {download_url}",
        "client_email": client_email  # Return for sending to client
    }


def agreement_created_email(
    lead_name: str,
    company: str,
    agreement_number: str,
    agreement_id: str,
    agreement_type: str,
    total_value: float,
    currency: str,
    start_date: str,
    end_date: str,
    status: str,
    salesperson_name: str,
    client_email: str,
    app_url: str
) -> Dict[str, str]:
    """
    Email template for when agreement is created.
    Sent to: Sales Manager + Sales Manager's Manager + Client
    Includes view/download/upload links.
    """
    formatted_value = f"{currency} {total_value:,.2f}"
    status_color = "#10b981" if status.lower() == "signed" else "#3b82f6"
    view_url = f"{app_url}/agreements/{agreement_id}"
    download_url = f"{app_url}/api/agreements/{agreement_id}/download"
    upload_url = f"{app_url}/agreements/{agreement_id}?action=upload"
    
    details = [
        {"label": "Client", "value": f"{lead_name} ({company})"},
        {"label": "Agreement No.", "value": agreement_number},
        {"label": "Type", "value": agreement_type},
        {"label": "Contract Value", "value": formatted_value},
        {"label": "Start Date", "value": start_date},
        {"label": "End Date", "value": end_date},
        {"label": "Status", "value": status.upper()},
        {"label": "Created By", "value": salesperson_name},
        {"label": "Client Email", "value": client_email or "N/A"}
    ]
    
    content = f"""
        <p style="margin: 0; color: #4b5563; font-size: 15px; line-height: 1.6;">
            A service agreement has been created for <strong>{company}</strong>.
        </p>
        
        <div style="margin-top: 20px; padding: 20px; background: linear-gradient(135deg, #dbeafe 0%, #ede9fe 100%); border-radius: 8px; text-align: center;">
            <p style="margin: 0 0 5px 0; color: #4338ca; font-size: 12px; text-transform: uppercase;">Contract Value</p>
            <p style="margin: 0; color: #312e81; font-size: 28px; font-weight: 700;">{formatted_value}</p>
            <span style="display: inline-block; margin-top: 10px; background-color: {status_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;">
                {status.upper()}
            </span>
        </div>
        
        <!-- Action Links -->
        <div style="margin-top: 20px; padding: 15px; background-color: #faf5ff; border-radius: 8px;">
            <p style="margin: 0 0 10px 0; color: #7c3aed; font-size: 13px; font-weight: 600;">Quick Actions</p>
            <table role="presentation" style="width: 100%;">
                <tr>
                    <td style="padding: 5px 0;">
                        <a href="{view_url}" style="color: #7c3aed; text-decoration: none; font-size: 13px;">📄 View Agreement</a>
                    </td>
                    <td style="padding: 5px 0;">
                        <a href="{download_url}" style="color: #7c3aed; text-decoration: none; font-size: 13px;">⬇️ Download PDF</a>
                    </td>
                    <td style="padding: 5px 0;">
                        <a href="{upload_url}" style="color: #7c3aed; text-decoration: none; font-size: 13px;">⬆️ Upload Signed Copy</a>
                    </td>
                </tr>
            </table>
        </div>
    """
    
    html = BASE_TEMPLATE.format(
        title="Agreement Created - NETRA",
        badge_color="#8b5cf6",
        badge_text="AGREEMENT READY",
        headline=f"Service Agreement: {agreement_number}",
        content=content,
        details_section=_build_details_table(details),
        action_section=_build_action_button("View Agreement", view_url, "#8b5cf6"),
        year=datetime.now().year
    )
    
    return {
        "subject": f"📝 Agreement #{agreement_number} Created - {company}",
        "html": html,
        "plain": f"Service agreement created for {company}.\n\nAgreement: {agreement_number}\nValue: {formatted_value}\nStatus: {status}\nView: {view_url}\nDownload: {download_url}",
        "client_email": client_email  # Return for sending to client
    }


def kickoff_sent_email(
    lead_name: str,
    company: str,
    project_name: str,
    project_type: str,
    start_date: str,
    assigned_pm: str,
    contract_value: float,
    currency: str,
    meetings_count: int,
    key_commitments: List[str],
    salesperson_name: str,
    approver_name: str,
    app_url: str
) -> Dict[str, str]:
    """
    Email template for when kickoff request is sent for approval
    """
    formatted_value = f"{currency} {contract_value:,.2f}"
    
    details = [
        {"label": "Client", "value": f"{lead_name} ({company})"},
        {"label": "Project Name", "value": project_name},
        {"label": "Project Type", "value": project_type},
        {"label": "Proposed Start", "value": start_date},
        {"label": "Assigned PM", "value": assigned_pm},
        {"label": "Contract Value", "value": formatted_value},
        {"label": "Meetings Held", "value": f"{meetings_count} meeting(s)"},
        {"label": "Requested By", "value": salesperson_name},
        {"label": "Pending Approval From", "value": approver_name}
    ]
    
    content = f"""
        <p style="margin: 0; color: #4b5563; font-size: 15px; line-height: 1.6;">
            A kickoff request has been submitted for <strong>{company}</strong> and is awaiting approval.
        </p>
        
        <div style="margin-top: 20px; padding: 15px; background-color: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
            <p style="margin: 0; color: #92400e; font-size: 13px;">
                <strong>Action Required:</strong> This request needs approval from {approver_name} to proceed with project creation.
            </p>
        </div>
        
        {_build_list_section("Key Commitments to Client", key_commitments)}
    """
    
    html = BASE_TEMPLATE.format(
        title="Kickoff Request Sent - NETRA",
        badge_color="#f59e0b",
        badge_text="PENDING APPROVAL",
        headline=f"Kickoff Request: {project_name}",
        content=content,
        details_section=_build_details_table(details),
        action_section=_build_action_button("Review Kickoff Request", f"{app_url}/kickoff-requests", "#f59e0b"),
        year=datetime.now().year
    )
    
    return {
        "subject": f"🚀 Kickoff Request Sent: {project_name} - {company} (Pending Approval)",
        "html": html,
        "plain": f"Kickoff request submitted for {company}.\n\nProject: {project_name}\nAwaiting approval from: {approver_name}"
    }


def kickoff_accepted_email(
    lead_name: str,
    company: str,
    project_name: str,
    project_id: str,
    project_type: str,
    start_date: str,
    assigned_pm: str,
    contract_value: float,
    currency: str,
    approved_by: str,
    approval_date: str,
    salesperson_name: str,
    app_url: str
) -> Dict[str, str]:
    """
    Email template for when kickoff is accepted/approved
    """
    formatted_value = f"{currency} {contract_value:,.2f}"
    
    details = [
        {"label": "Client", "value": f"{lead_name} ({company})"},
        {"label": "Project Name", "value": project_name},
        {"label": "Project ID", "value": project_id or "Pending"},
        {"label": "Project Type", "value": project_type},
        {"label": "Start Date", "value": start_date},
        {"label": "Project Manager", "value": assigned_pm},
        {"label": "Contract Value", "value": formatted_value},
        {"label": "Approved By", "value": approved_by},
        {"label": "Approval Date", "value": approval_date},
        {"label": "Sales Owner", "value": salesperson_name}
    ]
    
    content = f"""
        <p style="margin: 0; color: #4b5563; font-size: 15px; line-height: 1.6;">
            Great news! The kickoff request for <strong>{company}</strong> has been <strong style="color: #10b981;">approved</strong>!
        </p>
        
        <div style="margin-top: 20px; padding: 25px; background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); border-radius: 12px; text-align: center;">
            <div style="font-size: 40px; margin-bottom: 10px;">🎉</div>
            <p style="margin: 0; color: #065f46; font-size: 18px; font-weight: 700;">Project Approved!</p>
            <p style="margin: 8px 0 0 0; color: #047857; font-size: 14px;">
                The project has been created and the PM has been notified.
            </p>
        </div>
        
        <div style="margin-top: 20px; padding: 15px; background-color: #eff6ff; border-radius: 8px;">
            <h4 style="margin: 0 0 10px 0; color: #1e40af; font-size: 13px;">Next Steps</h4>
            <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #1e3a5f;">
                <li style="margin-bottom: 6px;">PM will schedule internal kickoff meeting</li>
                <li style="margin-bottom: 6px;">Client onboarding will begin</li>
                <li style="margin-bottom: 6px;">Project timeline will be shared</li>
            </ul>
        </div>
    """
    
    html = BASE_TEMPLATE.format(
        title="Kickoff Approved - NETRA",
        badge_color="#10b981",
        badge_text="APPROVED ✓",
        headline=f"🎉 Project Kickoff: {project_name}",
        content=content,
        details_section=_build_details_table(details),
        action_section=_build_action_button("View Project", f"{app_url}/projects/{project_id}" if project_id else f"{app_url}/projects", "#10b981"),
        year=datetime.now().year
    )
    
    return {
        "subject": f"✅ Kickoff Approved: {project_name} - {company} - Project Created!",
        "html": html,
        "plain": f"Kickoff approved for {company}!\n\nProject: {project_name}\nApproved by: {approved_by}\nPM: {assigned_pm}"
    }


# ============== Helper to get manager emails ==============

async def get_sales_manager_emails(db) -> List[str]:
    """
    Get email addresses for general sales funnel notifications.
    Recipients: HR, Sales Manager, Sales Head, Admin
    """
    recipients = await db.users.find(
        {"role": {"$in": [
            "hr_manager",           # HR
            "hr",                   # HR
            "sales_manager",        # Sales Manager
            "sales_head",           # Sales Manager's Manager
            "admin"                 # Admin (top level)
        ]}},
        {"_id": 0, "email": 1}
    ).to_list(50)
    
    return [r.get("email") for r in recipients if r.get("email")]


async def get_agreement_notification_emails(db) -> List[str]:
    """
    Get email addresses for AGREEMENT-specific notifications.
    Recipients: Sales Manager + Sales Manager's Manager ONLY
    """
    recipients = await db.users.find(
        {"role": {"$in": [
            "sales_manager",        # Sales Manager
            "sales_head",           # Sales Manager's Manager
            "admin"                 # Admin (as manager's manager)
        ]}},
        {"_id": 0, "email": 1}
    ).to_list(50)
    
    return [r.get("email") for r in recipients if r.get("email")]
