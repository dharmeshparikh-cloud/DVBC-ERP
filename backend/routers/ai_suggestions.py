"""AI-powered text suggestion endpoint for polished business communication."""
import os
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage
from .deps import get_current_user
from .models import User

router = APIRouter(prefix="/ai", tags=["AI Suggestions"])

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

SYSTEM_PROMPT = """You are a professional business writing assistant for D&V Business Consulting, a consulting firm.
Your role is to take rough notes or context and produce polished, professional text.

Rules:
- Keep the tone professional yet warm and approachable
- Be concise — no unnecessary padding or filler
- Use active voice and clear structure
- For MOM (Minutes of Meeting): use simple bullet points with dashes (-)
- For follow-up notes: be action-oriented
- For emails: maintain a formal business tone
- For discussion points: be specific and actionable
- Output ONLY the polished text, no explanations or preambles
- Do NOT add greetings or signatures unless specifically asked
- Match the length to the input — short input = short output
- NEVER use markdown formatting like **bold**, *italic*, ##headings, or any other markup
- Use plain text only — no asterisks, no hashes, no underscores for emphasis
- Use CAPS or simple dashes for structure if needed"""


class SuggestionRequest(BaseModel):
    context_type: str  # 'mom', 'notes', 'follow_up', 'discussion_points', 'next_steps', 'email_body', 'action_items', 'client_expectations', 'key_commitments'
    rough_text: Optional[str] = ""
    client_name: Optional[str] = ""
    company: Optional[str] = ""
    meeting_type: Optional[str] = ""
    additional_context: Optional[str] = ""


CONTEXT_PROMPTS = {
    "mom": "Polish the following into a professional Minutes of Meeting (MOM) summary. Use bullet points for key topics discussed:",
    "notes": "Rewrite the following notes in clear, professional business language:",
    "follow_up": "Transform this into a polished follow-up note that's action-oriented and professional:",
    "discussion_points": "Rewrite these discussion points to be clear, structured, and professional:",
    "next_steps": "Polish these next steps into clear, actionable items with professional language:",
    "email_body": "Rewrite this email body to be professional, engaging, and concise:",
    "action_items": "Transform these into clear, assignable action items with professional language:",
    "client_expectations": "Polish these client expectations into clear, well-articulated points:",
    "key_commitments": "Rewrite these commitments in clear, professional language that shows accountability:",
}


@router.post("/suggest")
async def get_ai_suggestion(data: SuggestionRequest, current_user: User = Depends(get_current_user)):
    """Generate polished text suggestion based on rough input and context."""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="AI service not configured")

    if not data.rough_text and not data.additional_context:
        raise HTTPException(status_code=400, detail="Please provide some text or context to work with")

    context_prompt = CONTEXT_PROMPTS.get(data.context_type, CONTEXT_PROMPTS["notes"])

    # Build the full prompt
    parts = [context_prompt]
    if data.client_name:
        parts.append(f"Client: {data.client_name}")
    if data.company:
        parts.append(f"Company: {data.company}")
    if data.meeting_type:
        parts.append(f"Meeting type: {data.meeting_type}")
    if data.additional_context:
        parts.append(f"Context: {data.additional_context}")

    if data.rough_text:
        parts.append(f"\nText to polish:\n{data.rough_text}")
    else:
        parts.append(f"\nGenerate a professional {data.context_type.replace('_', ' ')} based on the context above.")

    full_prompt = "\n".join(parts)

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"ai-suggest-{uuid.uuid4().hex[:8]}",
            system_message=SYSTEM_PROMPT,
        )
        chat.with_model("openai", "gpt-5.2")

        response = await chat.send_message(UserMessage(text=full_prompt))
        # Strip any markdown formatting the model might still produce
        clean = response.strip()
        clean = clean.replace('**', '').replace('##', '').replace('__', '')
        clean = clean.replace('# ', '').replace('### ', '').replace('#### ', '')
        return {"suggestion": clean}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI suggestion failed: {str(e)}")
