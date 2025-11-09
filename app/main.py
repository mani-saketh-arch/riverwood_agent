import os
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from dotenv import load_dotenv
import uvicorn
from datetime import datetime

from llm_service import LLMService
from database import db

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Riverwood Daily Greetings Agent")

# Initialize services
llm_service = LLMService()

# Twilio client
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

@app.get("/")
async def root():
    return {
        "message": "Riverwood Daily Greetings Agent is running!",
        "status": "active",
        "time": datetime.now().isoformat()
    }

@app.get("/verify-setup")
async def verify_setup():
    """Verify all configuration is correct"""
    base_url = os.getenv("BASE_URL", "NOT_SET")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER", "NOT_SET")
    
    # Test database connection
    db_status = "connected"
    try:
        customers = db.get_all_verified_customers()
        db_customer_count = len(customers)
    except Exception as e:
        db_status = f"error: {str(e)}"
        db_customer_count = 0
    
    # Check if BASE_URL is accessible (skip ngrok browser warning check)
    webhook_test = "⚠️ Cannot verify externally (ngrok free tier has browser warnings)"
    if "ngrok" in base_url.lower():
        webhook_test = "ℹ️ Using ngrok - Twilio will bypass the browser warning automatically"
    else:
        try:
            import requests
            headers = {
                'User-Agent': 'TwilioProxy/1.1',  # Mimic Twilio to bypass ngrok
                'ngrok-skip-browser-warning': 'true'
            }
            response = requests.get(f"{base_url}/", timeout=5, headers=headers)
            if response.status_code == 200:
                webhook_test = "✅ BASE_URL is accessible"
            else:
                webhook_test = f"⚠️ BASE_URL returned {response.status_code}"
        except Exception as e:
            webhook_test = f"❌ BASE_URL not accessible: {str(e)}"
    
    return {
        "status": "✅ App is running",
        "base_url": base_url,
        "base_url_test": webhook_test,
        "twilio_number": twilio_number,
        "database": db_status,
        "verified_customers": db_customer_count,
        "endpoints": {
            "make_call": f"{base_url}/call/make-single-call?to_number=+919381305134",
            "docs": "http://localhost:8000/docs",
            "incoming_webhook": f"{base_url}/voice/incoming",
            "process_webhook": f"{base_url}/voice/process"
        },
        "instructions": [
            "1. Make sure BASE_URL in .env matches your ngrok URL",
            "2. Restart app after changing .env",
            "3. Use /call/make-single-call to test calls"
        ]
    }

@app.post("/voice/incoming", response_class=PlainTextResponse)
async def handle_incoming_call(request: Request):
    """Handle incoming call - Initial greeting"""
    form_data = await request.form()
    from_number = form_data.get("From", "")
    call_sid = form_data.get("CallSid", "")
    
    print(f"📞 Incoming call from: {from_number} | SID: {call_sid}")
    
    # Get customer from database
    customer = db.get_customer_by_phone(from_number)
    
    # Create TwiML response
    response = VoiceResponse()
    
    if customer and customer.get('is_verified') and customer.get('preferred_language') != 'English':
        # Returning customer with known language preference - skip language selection
        preferred_lang = customer.get('preferred_language', 'English')
        name = customer.get('name', '')
        
        # Get construction updates for context
        construction_updates = db.get_latest_construction_updates(limit=1)
        update_text = ""
        if construction_updates:
            update = construction_updates[0]
            update_text = f"{update.get('title', '')} - {update.get('progress_percentage', 0)}% complete"
        
        # Generate personalized greeting based on language
        if preferred_lang == "Hindi":
            if name:
                greeting = f"Namaste {name} ji! Main Riverwood se bol rahi hoon. Kaise hain aap? Aaj construction mein acchi progress hui hai!"
            else:
                greeting = f"Namaste! Main Riverwood Projects se bol rahi hoon. Aaj ka construction update hai - {update_text}. Aap kaise hain?"
        elif preferred_lang == "Telugu":
            if name:
                greeting = f"Namaskaram {name} garu! Nenu Riverwood nundi. Meeru ela unnaru? Ee roju construction lo manchi progress ayyindi!"
            else:
                greeting = f"Namaskaram! Nenu Riverwood Projects nundi. Ee roju construction update - {update_text}. Meeru ela unnaru?"
        else:  # English
            if name:
                greeting = f"Hello {name}! This is Riverwood Projects calling. How are you today? We have some great construction updates!"
            else:
                greeting = f"Hello! I'm calling from Riverwood Projects with today's construction update. {update_text}. How are you doing?"
        
        language_code = {"English": "en-IN", "Hindi": "hi-IN", "Telugu": "te-IN"}.get(preferred_lang, "en-IN")
        
    else:
        # New customer OR customer with English preference - ask for language
        greeting = "Hello! I'm calling from Riverwood Projects with your daily construction update. Which language would you prefer - English, Hindi, or Telugu?"
        preferred_lang = "English"
        language_code = "en-IN"
        
        # If customer doesn't exist, create them
        if not customer:
            db.create_customer(from_number, preferred_language="English")
    
    # Store initial call log
    if customer and customer.get('id'):
        db.create_call_log(
            customer_id=customer['id'],
            call_sid=call_sid,
            call_status='in-progress',
            language_used=preferred_lang
        )
    
    # Configure gather for speech input
    gather = Gather(
        input='speech',
        action='/voice/process',
        method='POST',
        timeout=5,
        language=language_code,
        speech_timeout='auto',
        hints='English, Hindi, Telugu, construction, update, project, plot'  # Help speech recognition
    )
    gather.say(greeting, language=language_code)
    response.append(gather)
    
    # If no input, say goodbye
    if preferred_lang == "Hindi":
        response.say("Koi response nahi mila. Theek hai, kal phir baat karte hain. Namaste!", 
                    language='hi-IN')
    elif preferred_lang == "Telugu":
        response.say("Response raaledu. Sare, repu malli maatladukuntam. Namaskaram!", 
                    language='te-IN')
    else:
        response.say("No response received. Alright, we'll talk tomorrow. Thank you!", 
                    language='en-IN')
    
    return str(response)

@app.post("/voice/process", response_class=PlainTextResponse)
async def process_user_input(request: Request):
    """Process user speech input and respond"""
    form_data = await request.form()
    user_speech = form_data.get("SpeechResult", "")
    from_number = form_data.get("From", "")
    call_sid = form_data.get("CallSid", "")
    
    print(f"🎤 User said: {user_speech}")
    
    # Get customer from database
    customer = db.get_customer_by_phone(from_number)
    
    if not customer:
        # Create new customer if doesn't exist
        customer_id = db.create_customer(from_number)
        customer = db.get_customer_by_phone(from_number)
    
    preferred_lang = customer.get('preferred_language', 'English')
    customer_id = customer.get('id')
    is_language_selection = False
    
    # Detect if this is the first interaction (language selection)
    if user_speech:
        user_lower = user_speech.lower()
        
        # Check if user is selecting language
        if any(word in user_lower for word in ['hindi', 'हिंदी', 'हिन्दी', 'prefer hindi']):
            preferred_lang = "Hindi"
            db.update_customer_preferences(from_number, preferred_language="Hindi")
            is_language_selection = True
        elif any(word in user_lower for word in ['telugu', 'తెలుగు', 'prefer telugu']):
            preferred_lang = "Telugu"
            db.update_customer_preferences(from_number, preferred_language="Telugu")
            is_language_selection = True
        elif any(word in user_lower for word in ['english', 'इंग्लिश', 'prefer english']):
            preferred_lang = "English"
            db.update_customer_preferences(from_number, preferred_language="English")
            is_language_selection = True
    
    # Get call history for context (last 3 calls)
    call_history = db.get_call_history(from_number, limit=3)
    history_context = []
    for call in call_history:
        if call.get('conversation_summary'):
            history_context.append(call['conversation_summary'])
    
    # Get latest construction updates
    construction_updates = db.get_latest_construction_updates(limit=3)
    updates_context = []
    for update in construction_updates:
        updates_context.append({
            'title': update.get('title', ''),
            'description': update.get('description', ''),
            'progress': update.get('progress_percentage', 0)
        })
    
    # Build customer context
    customer_context = {
        'total_calls': len(call_history),
        'is_new_customer': len(call_history) == 0,
        'last_call_date': call_history[0].get('call_date') if call_history else None
    }
    
    # Generate AI response with full context
    ai_response = llm_service.generate_response(
        user_message=user_speech,
        conversation_history=history_context,
        preferred_language=preferred_lang,
        construction_updates=updates_context,
        is_first_message=is_language_selection,
        customer_name=customer.get('name'),
        customer_context=customer_context
    )
    print(f"🤖 AI Response: {ai_response}")
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Language codes for TTS
    language_codes = {
        "English": "en-IN",
        "Hindi": "hi-IN",
        "Telugu": "te-IN"
    }
    
    # Continue conversation
    gather = Gather(
        input='speech',
        action='/voice/process',
        method='POST',
        timeout=5,
        language=language_codes.get(preferred_lang, 'en-IN'),
        speech_timeout='auto',
        hints='construction, update, project, plot, clubhouse, amenities, price, location'
    )
    gather.say(ai_response, language=language_codes.get(preferred_lang, 'en-IN'))
    response.append(gather)
    
    # If no response, end call with goodbye
    if preferred_lang == "Hindi":
        response.say("Theek hai, aaj ke liye bas itna hi. Kal phir baat karte hain. Namaste!", 
                    language='hi-IN')
    elif preferred_lang == "Telugu":
        response.say("Sare, ee roju idi chalu. Repu malli maatladukuntam. Namaskaram!", 
                    language='te-IN')
    else:
        response.say("Alright, that's all for today. We'll talk tomorrow. Thank you!", 
                    language='en-IN')
    
    # Update call log with conversation summary
    if customer_id:
        summary = f"User: {user_speech[:100]} | AI: {ai_response[:100]}"
        db.create_call_log(
            customer_id=customer_id,
            call_sid=call_sid,
            call_status='in-progress',
            conversation_summary=summary,
            language_used=preferred_lang
        )
    
    return str(response)

@app.get("/call/make-single-call")
async def make_single_call_get(to_number: str):
    """Make a single call via GET request (for browser testing)"""
    try:
        # Get or create customer
        customer = db.get_customer_by_phone(to_number)
        
        if not customer:
            # Create customer with default settings
            customer_id = db.create_customer(
                phone_number=to_number,
                name="Test Customer",
                preferred_language="English",
                preferred_call_time="09:00:00"
            )
            if not customer_id:
                return {"status": "error", "message": "Failed to create customer"}
        
        # Make the call
        call = twilio_client.calls.create(
            to=to_number,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            url=f"{os.getenv('BASE_URL')}/voice/incoming",
            method="POST",
            status_callback=f"{os.getenv('BASE_URL')}/call/status",
            status_callback_event=['completed']
        )
        
        print(f"✅ Call initiated to {to_number} - SID: {call.sid}")
        
        return {
            "status": "success",
            "call_sid": call.sid,
            "to_number": to_number,
            "message": f"Call initiated successfully! Check your phone.",
            "call_url": f"https://console.twilio.com/us1/monitor/logs/calls/{call.sid}"
        }
        
    except Exception as e:
        print(f"❌ Error making call: {e}")
        return {
            "status": "error",
            "message": str(e),
            "to_number": to_number
        }

@app.post("/call/initiate-daily-calls")
async def initiate_daily_calls(background_tasks: BackgroundTasks, target_time: str = None):
    """Initiate daily calls to all verified customers asynchronously"""
    
    customers = db.get_customers_for_calling(target_time)
    print(f"📋 Found {len(customers)} customers to call")

    def make_call(customer):
        try:
            phone = customer['phone_number'].strip()
            call = twilio_client.calls.create(
                to=phone,
                from_=os.getenv("TWILIO_PHONE_NUMBER"),
                url=f"{os.getenv('BASE_URL')}/voice/incoming",
                method="POST",
                status_callback=f"{os.getenv('BASE_URL')}/call/status",
                status_callback_event=['completed']
            )

            db.create_call_log(
                customer_id=customer['id'],
                call_sid=call.sid,
                call_status='initiated',
                language_used=customer.get('preferred_language', 'English')
            )
            print(f"✅ Called {phone} - SID: {call.sid}")

        except Exception as e:
            print(f"❌ Failed to call {customer['phone_number']}: {e}")

    # Schedule background calls
    for customer in customers:
        background_tasks.add_task(make_call, customer)

    return {
        "status": "initiated",
        "total_customers": len(customers),
        "message": "Calls have been scheduled in background.",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/call/status")
async def handle_call_status(request: Request):
    """Handle call status callbacks from Twilio"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")
    call_duration = form_data.get("CallDuration", "0")
    
    print(f"📊 Call Status Update - SID: {call_sid} | Status: {call_status} | Duration: {call_duration}s")
    
    # You can update call logs here if needed
    
    return {"status": "received"}

@app.get("/customers/all")
async def get_all_customers():
    """Get all verified customers"""
    customers = db.get_all_verified_customers()
    return {
        "total": len(customers),
        "customers": customers
    }

@app.get("/customers/{phone_number}/history")
async def get_customer_history(phone_number: str):
    """Get conversation history for a phone number"""
    customer = db.get_customer_by_phone(phone_number)
    if not customer:
        return {"error": "Customer not found"}
    
    call_history = db.get_call_history(phone_number, limit=20)
    
    return {
        "customer": customer,
        "call_history": call_history,
        "total_calls": len(call_history)
    }

@app.post("/customers/create")
async def create_new_customer(
    phone_number: str,
    name: str = None,
    preferred_language: str = "English",
    preferred_call_time: str = "09:00:00"
):
    """Manually create a new customer"""
    customer_id = db.create_customer(
        phone_number=phone_number,
        name=name,
        preferred_language=preferred_language,
        preferred_call_time=preferred_call_time
    )
    
    if customer_id:
        return {
            "status": "success",
            "customer_id": customer_id,
            "message": f"Customer {phone_number} created successfully"
        }
    else:
        return {
            "status": "error",
            "message": "Customer already exists or creation failed"
        }

@app.post("/customers/{phone_number}/set-language")
async def set_customer_language(phone_number: str, language: str):
    """Set customer's preferred language (English, Hindi, Telugu)"""
    if language not in ["English", "Hindi", "Telugu"]:
        return {
            "status": "error",
            "message": "Language must be English, Hindi, or Telugu"
        }
    
    success = db.update_customer_preferences(
        phone_number=phone_number,
        preferred_language=language
    )
    
    if success:
        return {
            "status": "success",
            "message": f"Language set to {language} for {phone_number}"
        }
    else:
        return {
            "status": "error",
            "message": "Customer not found or update failed"
        }

@app.get("/updates/construction")
async def get_construction_updates():
    """Get latest construction updates"""
    updates = db.get_latest_construction_updates(limit=10)
    return {
        "total": len(updates),
        "updates": updates
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
