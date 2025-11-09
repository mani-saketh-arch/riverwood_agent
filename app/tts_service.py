import os
import requests
from typing import Optional

class TTSService:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID")
        self.base_url = "https://api.elevenlabs.io/v1"
    
    def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech using ElevenLabs"""
        try:
            url = f"{self.base_url}/text-to-speech/{self.voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_turbo_v2_5",  # Updated to free tier model
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "use_speaker_boost": True
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"TTS Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error in text_to_speech: {e}")
            return None
    
    def save_audio(self, audio_data: bytes, filename: str = "temp_audio.mp3") -> str:
        """Save audio data to file"""
        try:
            filepath = f"data/{filename}"
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'wb') as f:
                f.write(audio_data)
            
            return filepath
        except Exception as e:
            print(f"Error saving audio: {e}")
            return None