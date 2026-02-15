import os
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq Client
client = None
api_key = os.getenv("GROQ_API_KEY")

if api_key:
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        print(f"⚠️ Groq Error: {e}")

def generate_market_briefing(ticker, data_context):
    """
    Uses Llama 3 (via Groq) to write a professional financial briefing.
    """
    if not client:
        return "⚠️ AI Analyst unavailable (Check GROQ_API_KEY)."

    # Unpack the context
    price = data_context.get('price', 0)
    currency = data_context.get('currency', '$')
    rsi = data_context.get('rsi', 50)
    sentiment = data_context.get('sentiment', 'neutral')
    headline = data_context.get('headline', 'No major news.')
    prediction = data_context.get('prediction', 'HOLD')

    # Construct the Prompt - TUNED FOR "SMART BREVITY"
    prompt = f"""
    You are a senior financial analyst briefing a busy client. 
    Write a clear, concise 3-sentence executive summary for {ticker}.
    
    Data Snapshot:
    - Current Price: {currency}{price:.2f}
    - Technical Signal: RSI is {rsi:.0f} (Note: >70 is Overbought, <30 is Oversold).
    - News Sentiment: {sentiment.upper()} based on headline: "{headline}"
    - AI Forecast: {prediction}

    Guidelines:
    1. Start with the most important driver (News or Technicals).
    2. Explain WHAT is happening and WHY in plain professional English.
    3. Avoid overly academic jargon. Use clear, actionable language.
    4. Do not start with "Here is the summary". Jump straight into the insight.
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful financial assistant who speaks in clear, professional English."
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile", # Ensure you are using the new model
            temperature=0.6, # Slightly lower temperature for more focused answers
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ Briefing generation failed: {e}"