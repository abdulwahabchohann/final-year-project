"""Service layer helpers for external integrations and sentiment analysis."""

# Optional imports - only available if NLP dependencies are installed
try:
    from accounts.services.sentiment_analysis import get_sentiment_analyzer
    from accounts.services.mood_recommender import get_mood_recommender
    __all__ = [
        'get_sentiment_analyzer',
        'get_mood_recommender',
    ]
except ImportError:
    # NLP dependencies not installed - provide fallback functions
    def get_sentiment_analyzer():
        """Fallback when sentiment analysis dependencies are not installed."""
        raise ImportError(
            "Sentiment analysis requires additional packages. "
            "Install them with: pip install numpy transformers sentence-transformers torch"
        )
    
    def get_mood_recommender():
        """Fallback when mood recommender dependencies are not installed."""
        raise ImportError(
            "Mood recommender requires additional packages. "
            "Install them with: pip install numpy transformers sentence-transformers torch"
        )

__all__ = [
    'get_sentiment_analyzer',
    'get_mood_recommender',
]
