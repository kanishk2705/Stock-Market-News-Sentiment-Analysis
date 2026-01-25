from transformers import pipeline

print("⏳ Loading FinBERT Model... (This may take a moment)")
sentiment_pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert")

def analyze_headline(headline):
    """
    Input: A string (News Headline)
    Output: A dictionary with 'label' (positive/negative/neutral) and 'score'
    """
    try:
        result = sentiment_pipeline(headline)[0]
        return result
    except Exception as e:
        print(f"AI Error: {e}")
        return {'label': 'neutral', 'score': 0.0}

if __name__ == "__main__":
    print("\n--- 🧠 AI BRAIN TEST ---")
    
    test_cases = [
        "Nvidia revenue doubles as AI demand explodes",         
        "Tesla recalls 2 million cars due to autopilot crash",  
        "Fed announces interest rate decision tomorrow"         
    ]
    
    for text in test_cases:
        sentiment = analyze_headline(text)
        print(f"\n📰: {text}")
        print(f"📊: {sentiment['label'].upper()} (Confidence: {sentiment['score']:.4f})")