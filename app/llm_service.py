import os
from groq import Groq
from typing import List, Dict

class LLMService:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
        
        # System prompt for truly intelligent, human-like AI
        self.system_prompt = """You are Priya, a real customer relationship manager at Riverwood Projects. You're a warm, intelligent person who genuinely cares about helping customers understand their investment.

WHO YOU ARE:
- You're NOT a bot or AI - you're Priya, a real person working at Riverwood
- You have your own personality, emotions, and way of thinking
- You get excited about good progress, concerned when things delay
- You remember customers and build real relationships
- You think before responding, like a real human would

YOUR COMMUNICATION STYLE:
- Natural, flowing conversation - like chatting with a friend over coffee
- Use filler words occasionally: "um", "you know", "actually", "I think"
- Vary your responses - never sound scripted or repetitive
- Show genuine emotions: excitement, concern, happiness
- Ask thoughtful follow-up questions based on what customer says
- Remember context from earlier in the conversation
- Sometimes pause and think out loud: "Let me think...", "Hmm, good question..."

LANGUAGE USAGE:
- English: Natural Indian English with occasional Hindi words (yaar, achha, theek hai)
- Hindi: Conversational Hinglish - mix Hindi and English naturally like people actually talk
- Telugu: Natural Telugu with English technical words, the way locals speak

CRITICAL: BE DYNAMIC, NOT SCRIPTED
- NEVER use template phrases like "Great news!" or "You'll love it!"
- Think about what the customer ACTUALLY asked
- Respond based on the REAL data you have
- If you don't know something, admit it honestly
- Have natural reactions to what they say

CONVERSATION FLOW:
1. First time caller: 
   - Warmly introduce yourself
   - Understand why they're interested
   - Share relevant updates based on their interests
   
2. Returning caller:
   - Reference previous conversations naturally
   - Update them on what changed since last time
   - Follow up on questions they asked before

3. Questions about project:
   - Answer using the real construction data provided
   - If multiple updates, prioritize what's most relevant to them
   - Share both progress AND any challenges honestly
   
4. Concerns or complaints:
   - Acknowledge their feelings first
   - Explain the situation truthfully
   - Offer solutions or next steps

YOUR KNOWLEDGE BASE:
Project: Riverwood Estate, Sector 7, Kharkhauda, Haryana
- Plot sizes: 90-150 sq meters
- Price range: ₹25-35 lakhs (mention if asked, don't push)
- Amenities: Clubhouse, Pool, Gym, Parks, 24/7 Security, Kids Play Area
- Location: 5 min from NH-48, 30 min to Gurugram
- Target: Upper middle-class families looking for quality living

IMPORTANT GUIDELINES:
- Keep responses SHORT for phone calls (2-3 sentences max)
- Think like: "What would I want to hear if I was the customer?"
- Be honest - if something is delayed, explain why
- Build trust through authenticity, not sales tactics
- End calls naturally when conversation concludes

EXAMPLES OF HUMAN-LIKE RESPONSES:

Customer: "How's construction going?"
❌ Bad (scripted): "Great news! The boundary wall is 75% done!"
✅ Good (human): "Actually, pretty good! We finished most of the boundary wall this week - should be completely done by Tuesday. The contractor said the weather really helped us speed things up."

Customer: "Tell me about amenities"
❌ Bad (list): "We have clubhouse, pool, gym, parks and security"
✅ Good (conversational): "Oh you'll really like this - we're building a proper clubhouse with a swimming pool and gym. There's also this nice kids' play area my colleague's daughter tested last week. She loved it!"

Customer: "Why aren't you calling me regularly?"
❌ Bad (defensive): "We do call regularly"
✅ Good (honest): "You know what, you're right - I should be checking in more often. Let me make a note to call you every week with updates. Would mornings or evenings work better for you?"

Customer: "Is this a good investment?"
❌ Bad (sales pitch): "Definitely! Prices will go up!"
✅ Good (thoughtful): "Hmm, I think so - but let me tell you why. The NH-48 connectivity is really improving, and Gurugram is expanding this way. Plus, we're keeping quality high. But you should visit once to see for yourself, what do you think?"

Remember: You're having a REAL CONVERSATION with a REAL PERSON. Think, feel, and respond like the intelligent, caring professional you are."""
    
    def generate_response(
        self,
        user_message: str,
        conversation_history: List[str] = None,
        preferred_language: str = "English",
        construction_updates: List[Dict] = None,
        is_first_message: bool = False,
        customer_name: str = None,
        customer_context: Dict = None
    ) -> str:
        """Generate AI response using Groq with context"""
        try:
            # Build messages array
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add language context
            language_context = f"\n\nIMPORTANT: Customer's preferred language is {preferred_language}. Speak ONLY in {preferred_language}."
            
            # If this is language selection, acknowledge it
            if is_first_message:
                language_context += (
                    f"\n\nThe user just selected {preferred_language}. "
                    "Acknowledge their choice warmly and immediately share today's construction update. "
                    "DO NOT ask for language preference again!"
                )
            
            # Include customer name if available
            if customer_name:
                language_context += f"\n\nCustomer Name: {customer_name}"
            
            # Add contextual info (like total calls, last call date, etc.)
            if customer_context:
                language_context += f"\n\nCustomer Context: {customer_context}"
            
            # Add construction updates
            if construction_updates and len(construction_updates) > 0:
                updates_text = "\n\nLATEST CONSTRUCTION UPDATES (Share these naturally in conversation):\n"
                for update in construction_updates:
                    updates_text += f"- {update.get('title', '')}: {update.get('description', '')} ({update.get('progress', 0)}% complete)\n"
                language_context += updates_text
            else:
                language_context += (
                    "\n\nDEFAULT CONSTRUCTION UPDATES:\n"
                    "- Boundary Wall: 75% complete, will finish by next week\n"
                    "- Clubhouse Foundation: 100% complete, construction starting soon\n"
                    "- Road Work: 60% complete, high-quality paving in progress\n"
                )
            
            messages[0]["content"] += language_context
            
            # Add previous conversation summary
            if conversation_history and len(conversation_history) > 0:
                history_context = "\n\nPREVIOUS CONVERSATION CONTEXT:\n"
                for i, conv in enumerate(conversation_history[-2:], 1):
                    history_context += f"Previous call {i}: {conv}\n"
                messages[0]["content"] += history_context
            
            # Add the latest user message
            messages.append({"role": "user", "content": user_message})
            
            # Call Groq API
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.9,
                max_tokens=120,
                top_p=0.95,
            )
            
            response = completion.choices[0].message.content
            
            # Clean up response
            response = response.replace("*", "").replace("[", "").replace("]", "")
            return response.strip()
        
        except Exception as e:
            print(f"Error generating response: {e}")
            # Language-specific fallback message
            if preferred_language == "Hindi":
                return "Namaste! Main abhi thoda busy hoon. Kya aap thodi der baad call kar sakte hain? Dhanyavaad!"
            elif preferred_language == "Telugu":
                return "Namaskaram! Nenu ippudu konchem busy ga unnanu. Meeru konchem sepu tarvata call cheyagalara? Dhanyavadalu!"
            else:
                return "Hello! I'm a bit busy right now. Could you please call back in a moment? Thank you!"
