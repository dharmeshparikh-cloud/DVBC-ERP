"""
Test Email Preview Endpoint
Generate HTML previews of sales funnel email templates
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from services.funnel_notifications import generate_test_email_previews

router = APIRouter(prefix="/test", tags=["Test"])


@router.get("/email-preview/{template_name}")
async def get_email_preview(template_name: str):
    """
    Generate preview of a specific email template.
    
    template_name options:
    - mom_filled
    - proforma
    - agreement
    - kickoff_sent
    - kickoff_accepted
    - all (returns list of all templates)
    """
    previews = generate_test_email_previews()
    
    if template_name == "all":
        # Return an index page with links to all templates
        links = ""
        for name in previews.keys():
            links += f'<li><a href="/api/test/email-preview/{name}" target="_blank">{name.replace("_", " ").title()}</a></li>'
        
        return HTMLResponse(content=f"""
            <html>
            <head><title>Email Template Previews</title></head>
            <body style="font-family: Arial, sans-serif; padding: 40px;">
                <h1>Sales Funnel Email Templates</h1>
                <p>Click on a template to preview:</p>
                <ul style="line-height: 2;">{links}</ul>
            </body>
            </html>
        """)
    
    if template_name not in previews:
        return HTMLResponse(
            content=f"<h1>Template not found</h1><p>Valid templates: {', '.join(previews.keys())}</p>",
            status_code=404
        )
    
    template = previews[template_name]
    return HTMLResponse(content=template["html"])


@router.get("/email-preview-json/{template_name}")
async def get_email_preview_json(template_name: str):
    """
    Get email preview as JSON including subject and plain text.
    """
    previews = generate_test_email_previews()
    
    if template_name == "all":
        # Return summary of all templates
        return {
            "templates": list(previews.keys()),
            "subjects": {name: data["subject"] for name, data in previews.items()}
        }
    
    if template_name not in previews:
        return {"error": f"Template not found. Valid: {', '.join(previews.keys())}"}
    
    template = previews[template_name]
    return {
        "template_name": template_name,
        "subject": template["subject"],
        "plain_text": template.get("plain", ""),
        "html_length": len(template["html"]),
        "client_email": template.get("client_email", "N/A")
    }
