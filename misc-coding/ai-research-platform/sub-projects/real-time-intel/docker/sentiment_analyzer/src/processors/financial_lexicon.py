"""Financial lexicon for sentiment analysis weighting."""

from typing import Dict, Set

# Financial sentiment lexicon with weights
FINANCIAL_POSITIVE_TERMS = {
    # Growth and performance
    "growth": 1.2, "profit": 1.3, "revenue": 1.1, "earnings": 1.2,
    "beat": 1.4, "exceed": 1.3, "outperform": 1.4, "strong": 1.2,
    "robust": 1.3, "solid": 1.1, "impressive": 1.3, "record": 1.4,
    
    # Market sentiment
    "bullish": 1.5, "optimistic": 1.2, "confident": 1.2, "positive": 1.1,
    "upgrade": 1.3, "buy": 1.4, "overweight": 1.3, "outperform": 1.4,
    
    # Business fundamentals
    "expansion": 1.2, "acquisition": 1.1, "merger": 1.2, "dividend": 1.2,
    "buyback": 1.3, "innovation": 1.1, "breakthrough": 1.4, "launch": 1.1,
    
    # Financial health
    "cashflow": 1.2, "margin": 1.1, "efficient": 1.1, "profitable": 1.3,
    "sustainable": 1.1, "stable": 1.0, "recovery": 1.2, "turnaround": 1.3
}

FINANCIAL_NEGATIVE_TERMS = {
    # Losses and declines
    "loss": -1.3, "decline": -1.2, "drop": -1.2, "fall": -1.1,
    "miss": -1.4, "disappoint": -1.3, "underperform": -1.4, "weak": -1.2,
    "poor": -1.3, "terrible": -1.4, "dismal": -1.4, "plunge": -1.5,
    
    # Market sentiment
    "bearish": -1.5, "pessimistic": -1.2, "negative": -1.1, "concerned": -1.1,
    "downgrade": -1.3, "sell": -1.4, "underweight": -1.3, "avoid": -1.4,
    
    # Business problems
    "bankruptcy": -1.8, "lawsuit": -1.3, "investigation": -1.2, "scandal": -1.5,
    "fraud": -1.7, "violation": -1.3, "fine": -1.2, "penalty": -1.2,
    
    # Financial stress
    "debt": -1.1, "deficit": -1.2, "shortage": -1.2, "crisis": -1.4,
    "risk": -1.1, "uncertainty": -1.1, "volatility": -1.1, "concern": -1.1
}

# Emotion categories for financial context
FINANCIAL_EMOTIONS = {
    "fear": ["fear", "panic", "worry", "anxiety", "nervous", "scared"],
    "greed": ["greed", "euphoria", "fomo", "bubble", "mania", "speculation"],
    "uncertainty": ["uncertain", "unclear", "ambiguous", "confused", "mixed"],
    "confidence": ["confident", "certain", "assured", "convinced", "bullish"],
    "excitement": ["excited", "enthusiastic", "optimistic", "hopeful", "positive"],
    "disappointment": ["disappointed", "frustrated", "concerned", "worried", "bearish"]
}

# Sector-specific multipliers
SECTOR_MULTIPLIERS = {
    "technology": 1.1,    # Higher volatility, sentiment matters more
    "healthcare": 1.0,    # Moderate sensitivity
    "financials": 1.2,    # High sensitivity to market sentiment
    "energy": 1.1,        # Commodity-driven but sentiment matters
    "utilities": 0.8,     # Lower sensitivity to sentiment
    "consumer": 1.0,      # Moderate sensitivity
    "industrials": 0.9,   # Less sentiment-driven
    "materials": 0.9,     # Commodity-driven
    "real_estate": 1.0,   # Moderate sensitivity
    "communications": 1.1 # Social sentiment matters
}


def get_financial_sentiment_weight(text: str, sector: str = None) -> float:
    """Calculate financial sentiment weight based on lexicon."""
    text_lower = text.lower()
    total_weight = 0.0
    term_count = 0
    
    # Check positive terms
    for term, weight in FINANCIAL_POSITIVE_TERMS.items():
        if term in text_lower:
            total_weight += weight
            term_count += 1
    
    # Check negative terms
    for term, weight in FINANCIAL_NEGATIVE_TERMS.items():
        if term in text_lower:
            total_weight += weight  # weight is already negative
            term_count += 1
    
    if term_count == 0:
        base_weight = 1.0
    else:
        base_weight = 1.0 + (total_weight / term_count - 1.0) * 0.3  # Dampen effect
    
    # Apply sector multiplier
    if sector and sector.lower() in SECTOR_MULTIPLIERS:
        base_weight *= SECTOR_MULTIPLIERS[sector.lower()]
    
    return max(0.1, min(2.0, base_weight))  # Clamp between 0.1 and 2.0


def detect_emotions(text: str) -> Dict[str, float]:
    """Detect financial emotions in text."""
    text_lower = text.lower()
    emotions = {}
    
    for emotion, terms in FINANCIAL_EMOTIONS.items():
        score = 0.0
        for term in terms:
            if term in text_lower:
                score += 1.0
        
        if score > 0:
            emotions[emotion] = min(1.0, score / len(terms))
    
    return emotions


def extract_financial_entities(text: str) -> Set[str]:
    """Extract potential financial entities (tickers, companies)."""
    import re
    
    # Simple ticker pattern (3-5 uppercase letters)
    ticker_pattern = r'\b[A-Z]{2,5}\b'
    tickers = set(re.findall(ticker_pattern, text))
    
    # Filter out common words that match ticker pattern
    common_words = {"THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER", "WAS", "ONE", "OUR", "HAD", "BUT", "WILL", "NEW", "WHO", "ITS", "DID", "GET", "MAY", "HIM", "OLD", "SEE", "NOW", "WAY", "USE", "MAN", "DAY", "TOO", "ANY", "YOUR", "HOW", "SAY"}
    
    return tickers - common_words 