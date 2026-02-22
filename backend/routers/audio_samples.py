"""
Audio Samples Router - AI Voice Sales Pitch Samples with Objection Handling
Professional, Friendly, Enthusiastic Hindi (Hinglish) Conversations
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/audio-samples", tags=["Audio Samples"])


# ============== FULL CONVERSATION ==============

@router.get("/conversation/full")
async def download_full_conversation():
    """Download complete 2-way conversation with objection handling (~2 min)"""
    file_path = "/tmp/hindi_conversation_full.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_AI_Full_Conversation.mp3",
        media_type="audio/mpeg"
    )


# ============== OPENING ==============

@router.get("/conversation/opening")
async def download_opening():
    """Download enthusiastic professional opening"""
    file_path = "/tmp/hindi_objection_opening_enthusiastic.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_AI_Opening_Enthusiastic.mp3",
        media_type="audio/mpeg"
    )


# ============== OBJECTION HANDLING ==============

@router.get("/objection/busy")
async def download_objection_busy():
    """Handling: 'I'm busy right now'"""
    file_path = "/tmp/hindi_objection_objection_busy.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_AI_Objection_Busy.mp3",
        media_type="audio/mpeg"
    )


@router.get("/objection/not-interested")
async def download_objection_not_interested():
    """Handling: 'I'm not interested'"""
    file_path = "/tmp/hindi_objection_objection_not_interested.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_AI_Objection_NotInterested.mp3",
        media_type="audio/mpeg"
    )


@router.get("/objection/send-email")
async def download_objection_send_email():
    """Handling: 'Just send me an email'"""
    file_path = "/tmp/hindi_objection_objection_send_email.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_AI_Objection_SendEmail.mp3",
        media_type="audio/mpeg"
    )


@router.get("/objection/have-consultant")
async def download_objection_have_consultant():
    """Handling: 'We already have a consultant'"""
    file_path = "/tmp/hindi_objection_objection_have_consultant.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_AI_Objection_HaveConsultant.mp3",
        media_type="audio/mpeg"
    )


@router.get("/objection/too-expensive")
async def download_objection_too_expensive():
    """Handling: 'It's too expensive / Budget issues'"""
    file_path = "/tmp/hindi_objection_objection_too_expensive.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_AI_Objection_TooExpensive.mp3",
        media_type="audio/mpeg"
    )


@router.get("/objection/call-later")
async def download_objection_call_later():
    """Handling: 'Call me later / Not now'"""
    file_path = "/tmp/hindi_objection_objection_call_later.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_AI_Objection_CallLater.mp3",
        media_type="audio/mpeg"
    )


# ============== CLOSING ==============

@router.get("/conversation/closing")
async def download_closing():
    """Download meeting booking confirmation and closing"""
    file_path = "/tmp/hindi_objection_closing_meeting_booked.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_AI_Closing_MeetingBooked.mp3",
        media_type="audio/mpeg"
    )


# ============== LEGACY ENDPOINTS (Basic Pitch) ==============

@router.get("/hindi-pitch/full")
async def download_full_hindi_pitch():
    """Download full Hindi sales pitch MP3 (basic version)"""
    file_path = "/tmp/hindi_sales_pitch_sample.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_Hindi_Sales_Pitch_Basic.mp3",
        media_type="audio/mpeg"
    )


@router.get("/hindi-pitch/opening")
async def download_opening_hook():
    """Download opening hook sample (basic version)"""
    file_path = "/tmp/hindi_pitch_opening_hook.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_Hindi_Opening_Hook.mp3",
        media_type="audio/mpeg"
    )


# ============== LIST ALL SAMPLES ==============

@router.get("/list")
async def list_available_samples():
    """List all available audio samples with download URLs"""
    
    base_url = "/api/audio-samples"
    
    samples = {
        "professional_conversation": {
            "title": "🎯 Professional 2-Way Conversation (NEW)",
            "description": "Complete conversation flow with prospect responses simulation",
            "samples": [
                {
                    "name": "Full Conversation",
                    "description": "Complete 2-min conversation with objection handling",
                    "duration": "~2 min",
                    "url": f"{base_url}/conversation/full"
                },
                {
                    "name": "Opening (Enthusiastic)",
                    "description": "Professional + friendly greeting",
                    "duration": "~25 sec",
                    "url": f"{base_url}/conversation/opening"
                },
                {
                    "name": "Closing (Meeting Booked)",
                    "description": "Confirmation and professional goodbye",
                    "duration": "~40 sec",
                    "url": f"{base_url}/conversation/closing"
                }
            ]
        },
        "objection_handling": {
            "title": "🛡️ Objection Handling Responses",
            "description": "How AI handles common objections professionally",
            "samples": [
                {
                    "name": "I'm Busy",
                    "objection": "मैं अभी busy हूं",
                    "duration": "~35 sec",
                    "url": f"{base_url}/objection/busy"
                },
                {
                    "name": "Not Interested",
                    "objection": "मुझे interest नहीं है",
                    "duration": "~35 sec",
                    "url": f"{base_url}/objection/not-interested"
                },
                {
                    "name": "Send Email",
                    "objection": "Email भेज दो",
                    "duration": "~35 sec",
                    "url": f"{base_url}/objection/send-email"
                },
                {
                    "name": "Have Consultant",
                    "objection": "हमारे पास पहले से consultant है",
                    "duration": "~40 sec",
                    "url": f"{base_url}/objection/have-consultant"
                },
                {
                    "name": "Too Expensive",
                    "objection": "बहुत expensive है",
                    "duration": "~35 sec",
                    "url": f"{base_url}/objection/too-expensive"
                },
                {
                    "name": "Call Later",
                    "objection": "बाद में call करो",
                    "duration": "~40 sec",
                    "url": f"{base_url}/objection/call-later"
                }
            ]
        },
        "basic_pitch": {
            "title": "📢 Basic Pitch (Original)",
            "description": "Simple one-way pitch samples",
            "samples": [
                {
                    "name": "Full Basic Pitch",
                    "duration": "~2 min",
                    "url": f"{base_url}/hindi-pitch/full"
                },
                {
                    "name": "Opening Hook",
                    "duration": "~20 sec",
                    "url": f"{base_url}/hindi-pitch/opening"
                }
            ]
        }
    }
    
    return {
        "voice": "OpenAI TTS HD - Nova (Warm, Professional, Enthusiastic)",
        "language": "Hindi (Hinglish - Mixed Hindi/English)",
        "total_samples": 11,
        "categories": samples
    }
