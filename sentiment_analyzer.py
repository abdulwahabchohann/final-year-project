"""
Production-Ready Sentiment Analysis Module for Book Recommendations
Uses state-of-the-art transformer models for multi-dimensional emotion detection
"""

import os
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import pickle

# Check if transformers is available
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: transformers not installed. Install with: pip install transformers torch")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Install with: pip install sentence-transformers")

from sklearn.metrics.pairwise import cosine_similarity


class EmotionAnalyzer:
    """
    Multi-dimensional emotion detection using transformer models
    Detects: joy, sadness, anger, fear, surprise, love, optimism, anxiety, calm, excitement
    """
    
    def __init__(self, model_name: str = "cardiffnlp/twitter-roberta-base-emotion-multilabel-latest"):
        """
        Initialize emotion analyzer with pre-trained model
        
        Args:
            model_name: HuggingFace model name for emotion detection
        """
        self.model_name = model_name
        self.emotion_pipeline = None
        
        if TRANSFORMERS_AVAILABLE:
            self._load_model()
        else:
            print("Transformers not available. Using fallback sentiment analysis.")
    
    def _load_model(self):
        """Load the emotion detection model"""
        try:
            print(f"Loading emotion detection model: {self.model_name}")
            self.emotion_pipeline = pipeline(
                "text-classification",
                model=self.model_name,
                top_k=None,
                device=0 if torch.cuda.is_available() else -1
            )
            print("✓ Model loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load model {self.model_name}: {e}")
            print("Falling back to simpler model...")
            try:
                self.emotion_pipeline = pipeline(
                    "sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english"
                )
                print("✓ Fallback model loaded")
            except Exception as e2:
                print(f"Error loading fallback model: {e2}")
    
    def analyze_text(self, text: str) -> Dict[str, float]:
        """
        Analyze text and return emotion scores
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of emotion labels and their scores (0-1)
        """
        if not text or not isinstance(text, str):
            return {}
        
        # Truncate very long text
        text = text[:512]
        
        if self.emotion_pipeline is None:
            return self._fallback_sentiment(text)
        
        try:
            results = self.emotion_pipeline(text)
            
            if isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], list):
                    # Multi-label classification
                    emotion_scores = {item['label']: item['score'] for item in results[0]}
                else:
                    # Single label
                    emotion_scores = {results[0]['label']: results[0]['score']}
                
                return emotion_scores
            
            return {}
        
        except Exception as e:
            print(f"Error analyzing text: {e}")
            return self._fallback_sentiment(text)
    
    def _fallback_sentiment(self, text: str) -> Dict[str, float]:
        """Simple keyword-based fallback sentiment analysis"""
        emotions = {
            'joy': 0.0,
            'sadness': 0.0,
            'anger': 0.0,
            'fear': 0.0,
            'love': 0.0,
            'optimism': 0.0,
            'calm': 0.0
        }
        
        text_lower = text.lower()
        
        # Joy keywords
        joy_words = ['happy', 'joy', 'delightful', 'wonderful', 'amazing', 'great', 'excellent', 'fun', 'cheerful']
        emotions['joy'] = sum(1 for word in joy_words if word in text_lower) * 0.2
        
        # Sadness keywords
        sad_words = ['sad', 'depressing', 'melancholy', 'tragic', 'sorrow', 'grief', 'loss']
        emotions['sadness'] = sum(1 for word in sad_words if word in text_lower) * 0.2
        
        # Anger keywords
        anger_words = ['angry', 'rage', 'fury', 'hostile', 'violent', 'conflict']
        emotions['anger'] = sum(1 for word in anger_words if word in text_lower) * 0.2
        
        # Fear keywords
        fear_words = ['fear', 'scary', 'terror', 'horror', 'frightening', 'suspense', 'thriller']
        emotions['fear'] = sum(1 for word in fear_words if word in text_lower) * 0.2
        
        # Love keywords
        love_words = ['love', 'romance', 'romantic', 'passion', 'affection', 'heart']
        emotions['love'] = sum(1 for word in love_words if word in text_lower) * 0.2
        
        # Optimism keywords
        optimism_words = ['hope', 'optimis', 'inspiring', 'uplifting', 'positive', 'bright']
        emotions['optimism'] = sum(1 for word in optimism_words if word in text_lower) * 0.2
        
        # Calm keywords
        calm_words = ['calm', 'peaceful', 'serene', 'tranquil', 'relaxing', 'quiet', 'gentle']
        emotions['calm'] = sum(1 for word in calm_words if word in text_lower) * 0.2
        
        # Normalize scores
        total = sum(emotions.values())
        if total > 0:
            emotions = {k: min(v / total, 1.0) for k, v in emotions.items()}
        
        return emotions


class BookProcessor:
    """Process book metadata and extract analyzable text"""
    
    @staticmethod
    def extract_text(book: Dict) -> str:
        """
        Extract all analyzable text from a book
        
        Args:
            book: Book dictionary with metadata
            
        Returns:
            Combined text for analysis
        """
        text_parts = []
        
        # Add title and author for context
        if book.get('title'):
            text_parts.append(book['title'])
        
        # Description is the main content
        if book.get('description'):
            text_parts.append(book['description'])
        
        # Add reviews if available
        if book.get('reviews'):
            for review in book['reviews'][:3]:  # Limit to first 3 reviews
                text_parts.append(review)
        
        return ' '.join(text_parts)
    
    @staticmethod
    def preprocess_text(text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Basic cleaning
        text = text.strip()
        text = ' '.join(text.split())  # Normalize whitespace
        
        return text


class SentimentScorer:
    """Calculate sentiment match scores between user mood and books"""
    
    def __init__(self):
        self.embedding_model = None
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                print("Loading semantic similarity model...")
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                print("✓ Similarity model loaded")
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
    
    def calculate_emotion_similarity(
        self,
        user_emotions: Dict[str, float],
        book_emotions: Dict[str, float]
    ) -> float:
        """
        Calculate similarity between user mood and book emotions
        
        Args:
            user_emotions: User's emotional state
            book_emotions: Book's emotional profile
            
        Returns:
            Similarity score (0-1)
        """
        # Get common emotion labels
        all_emotions = set(user_emotions.keys()) | set(book_emotions.keys())
        
        if not all_emotions:
            return 0.0
        
        # Create vectors
        user_vector = [user_emotions.get(emotion, 0.0) for emotion in sorted(all_emotions)]
        book_vector = [book_emotions.get(emotion, 0.0) for emotion in sorted(all_emotions)]
        
        # Calculate cosine similarity
        user_array = np.array(user_vector).reshape(1, -1)
        book_array = np.array(book_vector).reshape(1, -1)
        
        similarity = cosine_similarity(user_array, book_array)[0][0]
        
        return max(0.0, min(1.0, similarity))
    
    def calculate_semantic_similarity(self, user_mood: str, book_text: str) -> float:
        """
        Calculate semantic similarity between user mood description and book content
        
        Args:
            user_mood: User's mood in natural language
            book_text: Book description/content
            
        Returns:
            Semantic similarity score (0-1)
        """
        if not self.embedding_model or not user_mood or not book_text:
            return 0.5  # Neutral score if can't compute
        
        try:
            # Generate embeddings
            user_embedding = self.embedding_model.encode([user_mood])
            book_embedding = self.embedding_model.encode([book_text[:512]])
            
            # Calculate similarity
            similarity = cosine_similarity(user_embedding, book_embedding)[0][0]
            
            return max(0.0, min(1.0, similarity))
        
        except Exception as e:
            print(f"Error calculating semantic similarity: {e}")
            return 0.5
    
    def calculate_match_score(
        self,
        user_mood: str,
        user_emotions: Dict[str, float],
        book: Dict,
        book_emotions: Dict[str, float],
        complementary_mode: bool = True
    ) -> float:
        """
        Calculate overall match score
        
        Args:
            user_mood: User's mood description
            user_emotions: User's emotion scores
            book: Book data
            book_emotions: Book's emotion scores
            complementary_mode: If True, boost positive books for negative moods
            
        Returns:
            Overall match score (0-1)
        """
        # Emotion similarity (40% weight)
        emotion_sim = self.calculate_emotion_similarity(user_emotions, book_emotions)
        
        # Semantic similarity (40% weight)
        book_text = BookProcessor.extract_text(book)
        semantic_sim = self.calculate_semantic_similarity(user_mood, book_text)
        
        # Complementary matching for mood improvement (20% weight)
        complementary_score = 0.5
        if complementary_mode:
            # Check if user is in negative mood
            negative_emotions = ['sadness', 'anger', 'fear', 'anxious', 'anxiety']
            user_negative = sum(user_emotions.get(e, 0) for e in negative_emotions)
            
            # Check if book has positive emotions
            positive_emotions = ['joy', 'love', 'optimism', 'calm', 'hope']
            book_positive = sum(book_emotions.get(e, 0) for e in positive_emotions)
            
            if user_negative > 0.3:  # User is in negative mood
                complementary_score = book_positive  # Boost positive books
        
        # Weighted combination
        final_score = (
            0.4 * emotion_sim +
            0.4 * semantic_sim +
            0.2 * complementary_score
        )
        
        return max(0.0, min(1.0, final_score))


class ExplainabilityEngine:
    """Generate human-readable explanations for recommendations"""
    
    @staticmethod
    def generate_explanation(
        book: Dict,
        book_emotions: Dict[str, float],
        user_emotions: Dict[str, float],
        match_score: float
    ) -> str:
        """
        Generate explanation for why this book was recommended
        
        Args:
            book: Book data
            book_emotions: Book's emotion profile
            user_emotions: User's emotion profile
            match_score: Overall match score
            
        Returns:
            Human-readable explanation
        """
        explanations = []
        
        # Get top emotions from book
        top_book_emotions = sorted(
            book_emotions.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # Get top emotions from user
        top_user_emotions = sorted(
            user_emotions.items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]
        
        # Matching emotions
        matching_emotions = []
        for emotion, score in top_book_emotions:
            if emotion in user_emotions and user_emotions[emotion] > 0.2:
                matching_emotions.append(emotion)
        
        if matching_emotions:
            emotion_text = ', '.join(matching_emotions)
            explanations.append(f"This book resonates with your current feelings of {emotion_text}")
        
        # Complementary recommendation
        negative_user = any(e in ['sadness', 'anger', 'fear', 'anxiety'] for e, s in top_user_emotions if s > 0.3)
        positive_book = any(e in ['joy', 'love', 'optimism', 'calm'] for e, s in top_book_emotions if s > 0.3)
        
        if negative_user and positive_book:
            explanations.append("This uplifting story can help improve your mood")
        
        # Genre context
        genres = book.get('genres', [])
        if genres:
            genre_text = genres[0] if len(genres) == 1 else f"{genres[0]} and {genres[1]}"
            
            # Map emotions to genre benefits
            if 'calm' in [e for e, s in top_book_emotions]:
                explanations.append(f"This {genre_text} book offers a calming, peaceful narrative")
            elif 'joy' in [e for e, s in top_book_emotions]:
                explanations.append(f"This {genre_text} book delivers an uplifting, joyful experience")
            elif 'love' in [e for e, s in top_book_emotions]:
                explanations.append(f"This {genre_text} book centers on heartwarming themes of love and connection")
        
        # Book-specific themes from description
        description = book.get('description', '').lower()
        if 'friendship' in description or 'friend' in description:
            explanations.append("Features powerful themes of friendship and human connection")
        if 'overcom' in description or 'challenge' in description:
            explanations.append("Inspires through stories of overcoming challenges")
        if 'adventure' in description:
            explanations.append("Takes you on an exciting and engaging adventure")
        
        # Default explanation if none generated
        if not explanations:
            explanations.append(f"This book's emotional tone aligns with your current mood (match score: {match_score:.0%})")
        
        return '. '.join(explanations[:3]) + '.'


class RecommendationEngine:
    """Main recommendation engine - combines all components"""
    
    def __init__(self, cache_file: str = "sentiment_cache.pkl"):
        """
        Initialize recommendation engine
        
        Args:
            cache_file: Path to cache file for storing analyzed books
        """
        self.emotion_analyzer = EmotionAnalyzer()
        self.scorer = SentimentScorer()
        self.explainer = ExplainabilityEngine()
        self.cache_file = cache_file
        self.sentiment_cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Load previously analyzed books from cache"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save analyzed books to cache"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.sentiment_cache, f)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")
    
    def analyze_book(self, book: Dict) -> Dict[str, float]:
        """
        Analyze a book's emotional content
        
        Args:
            book: Book dictionary
            
        Returns:
            Emotion scores dictionary
        """
        book_id = book.get('book_id')
        
        # Check cache
        if book_id and book_id in self.sentiment_cache:
            return self.sentiment_cache[book_id]
        
        # Extract and analyze text
        text = BookProcessor.extract_text(book)
        text = BookProcessor.preprocess_text(text)
        
        emotions = self.emotion_analyzer.analyze_text(text)
        
        # Cache result
        if book_id:
            self.sentiment_cache[book_id] = emotions
        
        return emotions
    
    def analyze_dataset(self, books: List[Dict], save_every: int = 100) -> Dict[str, Dict[str, float]]:
        """
        Analyze entire dataset of books
        
        Args:
            books: List of book dictionaries
            save_every: Save cache every N books
            
        Returns:
            Dictionary mapping book_id to emotion scores
        """
        print(f"Analyzing {len(books)} books...")
        
        results = {}
        for i, book in enumerate(books):
            book_id = book.get('book_id')
            
            if book_id:
                emotions = self.analyze_book(book)
                results[book_id] = emotions
                
                if (i + 1) % save_every == 0:
                    print(f"Processed {i + 1}/{len(books)} books")
                    self._save_cache()
        
        self._save_cache()
        print(f"✓ Analysis complete! Processed {len(results)} books")
        
        return results
    
    def get_recommendations(
        self,
        user_mood: str,
        books: List[Dict],
        top_k: int = 5,
        complementary_mode: bool = True
    ) -> List[Dict]:
        """
        Get book recommendations based on user's mood
        
        Args:
            user_mood: User's mood in natural language
            books: List of available books
            top_k: Number of recommendations to return
            complementary_mode: Whether to recommend mood-improving books
            
        Returns:
            List of recommended books with scores and explanations
        """
        print(f"Analyzing user mood: '{user_mood}'")
        
        # Analyze user's mood
        user_emotions = self.emotion_analyzer.analyze_text(user_mood)
        print(f"Detected emotions: {user_emotions}")
        
        # Score all books
        recommendations = []
        
        for book in books:
            # Get book emotions
            book_emotions = self.analyze_book(book)
            
            # Calculate match score
            match_score = self.scorer.calculate_match_score(
                user_mood,
                user_emotions,
                book,
                book_emotions,
                complementary_mode
            )
            
            # Generate explanation
            explanation = self.explainer.generate_explanation(
                book,
                book_emotions,
                user_emotions,
                match_score
            )
            
            recommendations.append({
                'book_id': book.get('book_id'),
                'title': book.get('title'),
                'author': book.get('author'),
                'genres': book.get('genres', []),
                'sentiment_score': round(match_score, 3),
                'recommendation_reason': explanation,
                'book_emotions': book_emotions,
                'average_rating': book.get('average_rating')
            })
        
        # Sort by match score
        recommendations.sort(key=lambda x: x['sentiment_score'], reverse=True)
        
        return recommendations[:top_k]


# Convenience function for easy usage
def recommend_books_by_mood(mood: str, dataset_path: str, top_k: int = 5) -> List[Dict]:
    """
    Simple function to get recommendations
    
    Args:
        mood: User's current mood
        dataset_path: Path to books JSON dataset
        top_k: Number of recommendations
        
    Returns:
        List of recommended books
    """
    # Load dataset
    with open(dataset_path, 'r', encoding='utf-8') as f:
        books = json.load(f)
    
    # Get recommendations
    engine = RecommendationEngine()
    recommendations = engine.get_recommendations(mood, books, top_k)
    
    return recommendations


if __name__ == "__main__":
    print("Sentiment Analysis Module for Book Recommendations")
    print("=" * 60)
    print("\nThis module provides:")
    print("✓ Multi-dimensional emotion detection")
    print("✓ Mood-based book matching")
    print("✓ Explainable recommendations")
    print("✓ Scalable architecture")
    print("\nSee example_usage.py for usage examples")
