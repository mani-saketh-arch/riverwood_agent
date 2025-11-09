# Riverwood Voice Agent

An AI-powered voice interaction system using:
- **FastAPI** for the backend server
- **Groq Llama 4 Scout** for conversational AI
- **ElevenLabs** for text-to-speech
- **Twilio** for phone call webhooks

## Setup

1. Clone the repo:
   git clone <repo-url>
   cd riverwood-voice-agent

2. Create a virtual environment and install dependencies:
   pip install -r requirements.txt

3. Set your environment variables in `.env`.

4. Run the app:
   uvicorn app.main:app --reload

## Folder Structure

riverwood-voice-agent/
├── app/
│   ├── main.py
│   ├── llm_service.py
│   ├── tts_service.py
│   └── memory_service.py
├── data/
│   └── conversations.json
├── requirements.txt
├── .env
└── README.md
