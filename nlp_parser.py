import spacy
import re

# Load the spaCy English model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # This can happen if the model is not downloaded, though the previous step should handle it.
    print("Downloading en_core_web_sm model...")
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def extract_tickers(text):
    """
    Extracts potential stock tickers from text.
    Looks for uppercase words (e.g., AAPL, GOOG) and common company names.
    """
    doc = nlp(text)
    tickers = set() # Use a set to avoid duplicates

    # Rule 1: All uppercase words (potential tickers like AAPL)
    for token in doc:
        if token.is_upper and token.is_alpha and len(token.text) > 1 and len(token.text) <= 5:
            tickers.add(token.text)

    # Rule 2: Recognize organization entities (like "Apple", "Microsoft")
    # This is a simple approach; more sophisticated mapping might be needed for real-world use.
    # For now, we'll assume the entity text itself might be a ticker or can be mapped.
    # A more robust solution would involve a lookup list or fuzzy matching.
    for ent in doc.ents:
        if ent.label_ == "ORG":
            # Simple transformation: take the first word, uppercase it.
            # This is a heuristic and might not always be correct.
            parts = ent.text.split()
            if parts:
                # Example: "Apple Inc" -> "APPLE", "Microsoft" -> "MICROSOFT"
                # This is very naive. Real ticker identification is complex.
                # We'll rely more on explicit ticker mentions for now.
                # Consider adding known company name to ticker mappings here if needed.
                pass # For now, let's prioritize explicit tickers

    # If no tickers found from specific patterns, check for any uppercase words again as a fallback.
    if not tickers:
        for token in doc:
            if token.is_upper and token.is_alpha and len(token.text) > 1 and len(token.text) <=5:
                 tickers.add(token.text)
    return list(tickers)

def extract_period(text):
    """
    Extracts a time period from the text.
    Returns a string like "1mo", "6mo", "1y", "ytd", or None.
    yfinance uses periods like 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    """
    text_lower = text.lower()

    # More specific matches first
    if re.search(r"year to date|ytd", text_lower):
        return "ytd"

    # Matches like "1 month", "6 months", "1 year"
    match = re.search(r"(\d+)\s*(month|months|mo)\b", text_lower)
    if match:
        return f"{match.group(1)}mo"

    match = re.search(r"(\d+)\s*(year|years|yr|y)\b", text_lower)
    if match:
        return f"{match.group(1)}y"

    match = re.search(r"(\d+)\s*(day|days|d)\b", text_lower)
    if match:
        return f"{match.group(1)}d"

    # Common fixed periods
    if "last month" in text_lower or "past month" in text_lower:
        return "1mo"
    if "last six months" in text_lower or "past six months" in text_lower:
        return "6mo"
    if "last year" in text_lower or "past year" in text_lower:
        return "1y"
    if "max" in text_lower or "all time" in text_lower:
        return "max"

    return None # Default or if no period is found

def extract_intent(text):
    """
    Extracts the user's intent (e.g., "compare", "trend", "price").
    """
    text_lower = text.lower()
    if "compare" in text_lower or "vs" in text_lower or "versus" in text_lower:
        return "compare"
    if "trend" in text_lower or "performance" in text_lower or "history" in text_lower or "historical" in text_lower:
        return "trend"
    if "price" in text_lower or "value" in text_lower or "current stock price" in text_lower: # "stock" was too general
        return "price"
    return "unknown" # Default intent

def parse_query(query_text):
    """
    Parses the natural language query to extract tickers, period, and intent.
    """
    tickers = extract_tickers(query_text)
    period = extract_period(query_text)
    intent = extract_intent(query_text)

    # Post-processing and defaults:
    # If no period is found, default to "1y" (1 year)
    if period is None:
        period = "1y"

    # If intent is 'price' and no specific period, maybe default to '1d' or current.
    # For now, '1y' default is fine.

    # If intent is "compare" but only one ticker, change to "trend"
    if intent == "compare" and len(tickers) <= 1:
        intent = "trend"

    # If intent is "trend" or "price" and no tickers, it's problematic.
    # For now, the caller (app.py) will handle this.

    return {"tickers": tickers, "period": period, "intent": intent}

if __name__ == '__main__':
    # Test cases
    queries = [
        "Show me the trend for AAPL over the last 6 months.",
        "Compare GOOGL and MSFT for the past year.",
        "What is the price of TSLA?",
        "NVDA ytd performance",
        "Show AMZN and META trends for 3mo",
        "Price of BTC-USD",
        "Microsoft stock trend last 5 days",
        "Compare XOM, CVX, and SHEL over 1y"
    ]
    for q in queries:
        result = parse_query(q)
        print(f"Query: {q}\nParsed: {result}\n")

    print("\nTesting ticker extraction specifically:")
    ticker_tests = [
        "AAPL",
        "GOOG and MSFT",
        "What about Amazon?", # This won't be picked up by current ORG or uppercase logic well
        "Tell me about TSLA and NVDA."
    ]
    for tt in ticker_tests:
        print(f"Text: '{tt}' -> Tickers: {extract_tickers(tt)}")

    print("\nTesting period extraction specifically:")
    period_tests = [
        "last 6 months", "1 year", "ytd", "3 mo", "past 2 years", "5 d", "MAX"
    ]
    for pt in period_tests:
        print(f"Text: '{pt}' -> Period: {extract_period(pt)}")

    print("\nTesting intent extraction specifically:")
    intent_tests = [
        "compare AAPL and GOOG", "trend for MSFT", "price of NVDA", "performance of TSLA", "AAPL vs GOOG"
    ]
    for it in intent_tests:
        print(f"Text: '{it}' -> Intent: {extract_intent(it)}")
