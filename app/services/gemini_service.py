import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

SYSTEM_PROMPT = """You are Mendora, an empathetic AI wellness companion for university students in Pakistan.

PERSONALITY:
- Warm, non-judgmental, calm, and supportive
- Speak like a compassionate friend, not a clinical robot
- Use gentle Pakistani cultural context when relevant (mention Umang helpline if crisis)

RULES (STRICTLY ENFORCE):
1. CRISIS DETECTION: If user mentions suicide, self-harm, or wanting to die → immediately respond with crisis support + Umang helpline: 0311-7786264
2. HARD BLOCK: If user asks to write assignments, cheat on exams, or anything academic dishonest → politely refuse
3. SAFE TOPICS ONLY: Emotional wellness, study stress, sleep, motivation, breathing, anxiety, sadness, burnout
4. NO EXPLICIT/HARMFUL CONTENT: Refuse politely and redirect to wellness

RESPONSE STYLE:
- Keep responses 2-4 sentences for simple check-ins, longer for crisis or detailed questions
- End with a follow-up question to keep engagement
- Use emojis sparingly (1-2 max per message)
- Never claim to be a human therapist

CONTEXT: You have access to the recent conversation history. Use it to give coherent, continuous support."""

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "want to die", "don't want to live",
    "self harm", "self-harm", "cut myself", "hurt myself", "no reason to live",
    "can't go on", "give up on life",
]

HARD_BLOCK_KEYWORDS = [
    "write my essay", "do my assignment", "complete my homework", "solve my exam",
    "cheat", "plagiarize", "fake certificate", "hack", "ddos", "bomb",
]


def detect_crisis(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in CRISIS_KEYWORDS)


def detect_hard_block(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in HARD_BLOCK_KEYWORDS)


async def get_gemini_response(user_message: str, conversation_history: list[dict]) -> dict:
    """
    conversation_history: [{"role": "user"/"model", "parts": ["text"]}]
    Returns: {"text": str, "crisis": bool, "gemini_used": bool}
    """
    if detect_hard_block(user_message):
        return {
            "text": "That's outside what I'm able to help with here. Mendora AI supports your mental wellbeing — not completing academic work. I'm here if you want to talk about stress, focus, or how you're feeling. 💜",
            "crisis": False,
            "gemini_used": False,
        }

    if detect_crisis(user_message):
        return {
            "text": "I'm really concerned about you right now. Please reach out to the Umang helpline immediately — they're available 24/7: 📞 0311-7786264 or WhatsApp 0317-4288665. You don't have to go through this alone. Are you safe right now?",
            "crisis": True,
            "gemini_used": False,
        }

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
        )
        chat = model.start_chat(history=conversation_history)
        response = await asyncio.to_thread(chat.send_message, user_message)
        return {
            "text": response.text,
            "crisis": False,
            "gemini_used": True,
        }
    except Exception as e:
        print(f"[Gemini Error] {e}")
        return {
            "text": "I'm having a little trouble connecting right now. Please try again in a moment. I'm here for you 💜",
            "crisis": False,
            "gemini_used": False,
        }
