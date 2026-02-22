"""
Generate Hindi AI Sales Pitch Audio Sample
Demonstrates how Bland.ai style voice call would sound
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def generate_hindi_pitch():
    from emergentintegrations.llm.openai import OpenAITextToSpeech
    
    # Initialize TTS
    tts = OpenAITextToSpeech(api_key=os.getenv("EMERGENT_LLM_KEY"))
    
    # Hindi Sales Pitch Script (DVBC Consulting Style)
    hindi_pitch = """
नमस्ते! मैं DVBC Consulting से बोल रही हूं।

क्या मैं आपसे 2 मिनट बात कर सकती हूं?

हमने देखा कि आपकी कंपनी manufacturing sector में काम करती है। 
हम पिछले 10 सालों से businesses को operational efficiency improve करने में help कर रहे हैं।

हमारे clients को average 25% cost reduction और 40% productivity improvement मिला है।

क्या आप अभी अपनी company में कोई operational challenges face कर रहे हैं? 
जैसे कि inventory management, production planning, या quality control?

अगर आप interested हैं, तो मैं आपके लिए एक free consultation call schedule कर सकती हूं 
जहां हमारे expert आपके specific challenges को समझेंगे और solutions suggest करेंगे।

क्या आप इस week कोई time निकाल सकते हैं? 
मंगलवार या बुधवार को सुबह 11 बजे कैसा रहेगा?

बहुत बढ़िया! मैंने आपका appointment book कर दिया है। 
आपको email और WhatsApp पर confirmation मिल जाएगा।

धन्यवाद! आपका दिन शुभ हो!
"""

    # Generate audio with shimmer voice (friendly, bright - good for sales)
    print("Generating Hindi pitch audio...")
    
    audio_bytes = await tts.generate_speech(
        text=hindi_pitch,
        model="tts-1-hd",  # High quality for demo
        voice="shimmer",   # Bright, friendly voice
        speed=0.95,        # Slightly slower for clarity
        response_format="mp3"
    )
    
    # Save to file
    output_path = "/tmp/hindi_sales_pitch_sample.mp3"
    with open(output_path, "wb") as f:
        f.write(audio_bytes)
    
    print(f"Audio saved to: {output_path}")
    print(f"File size: {len(audio_bytes) / 1024:.1f} KB")
    
    return output_path

if __name__ == "__main__":
    asyncio.run(generate_hindi_pitch())
