"""
Audio Samples Router - Generate and download AI voice pitch samples
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/audio-samples", tags=["Audio Samples"])


@router.get("/hindi-pitch/full")
async def download_full_hindi_pitch():
    """Download full Hindi sales pitch MP3"""
    file_path = "/tmp/hindi_sales_pitch_sample.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found. Please regenerate.")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_Hindi_Sales_Pitch_Full.mp3",
        media_type="audio/mpeg"
    )


@router.get("/hindi-pitch/opening")
async def download_opening_hook():
    """Download opening hook sample"""
    file_path = "/tmp/hindi_pitch_opening_hook.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_Hindi_Opening_Hook.mp3",
        media_type="audio/mpeg"
    )


@router.get("/hindi-pitch/value-prop")
async def download_value_proposition():
    """Download value proposition sample"""
    file_path = "/tmp/hindi_pitch_value_proposition.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_Hindi_Value_Proposition.mp3",
        media_type="audio/mpeg"
    )


@router.get("/hindi-pitch/meeting-booking")
async def download_meeting_booking():
    """Download meeting booking sample"""
    file_path = "/tmp/hindi_pitch_meeting_booking.mp3"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=file_path,
        filename="DVBC_Hindi_Meeting_Booking.mp3",
        media_type="audio/mpeg"
    )


@router.get("/list")
async def list_available_samples():
    """List all available audio samples"""
    samples = [
        {
            "name": "Full Hindi Sales Pitch",
            "description": "Complete 2-minute sales pitch in Hindi (Hinglish)",
            "duration": "~2 min",
            "download_url": "/api/audio-samples/hindi-pitch/full"
        },
        {
            "name": "Opening Hook",
            "description": "Initial greeting and attention grab",
            "duration": "~20 sec",
            "download_url": "/api/audio-samples/hindi-pitch/opening"
        },
        {
            "name": "Value Proposition",
            "description": "Key benefits and results pitch",
            "duration": "~30 sec",
            "download_url": "/api/audio-samples/hindi-pitch/value-prop"
        },
        {
            "name": "Meeting Booking",
            "description": "Closing and appointment confirmation",
            "duration": "~30 sec",
            "download_url": "/api/audio-samples/hindi-pitch/meeting-booking"
        }
    ]
    return {"samples": samples}
