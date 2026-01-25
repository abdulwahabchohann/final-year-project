"""
Mood-Based Book Recommendation Engine

This module provides intelligent book recommendations based on user mood,
using sentiment analysis to match books that either complement or improve
the user's emotional state.
"""

from __future__ import annotations

import logging
import re
import random
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

from django.db.models import Q, QuerySet
from accounts.models import Book
from accounts.services.cover_utils import PLACEHOLDER_COVER_URL, normalize_cover
from accounts.services.sentiment_analysis import get_sentiment_analyzer, MOOD_COMPATIBILITY
from accounts.services.google_books import search_google_books, GoogleBooksError

logger = logging.getLogger(__name__)


class MoodRecommender:
    """
    Recommends books based on user mood and emotional state.
    
    Features:
    - Multi-mood recognition from plain language input
    - Sentiment matching with explainable reasoning
    - Mood improvement recommendations
    - Scalable querying for large datasets
    """
    
    def __init__(self):
        self.analyzer = get_sentiment_analyzer()
    
    def recommend_books(
        self,
        user_mood: str,
        limit: int = 5,
        improve_mood: bool = True,
        min_confidence: float = 0.3
    ) -> List[Dict[str, any]]:
        """
        Get book recommendations based on user mood.
        
        Args:
            user_mood: User's mood description in plain language (e.g., "I feel sad and anxious")
            limit: Maximum number of recommendations to return
            improve_mood: If True, recommend books that improve mood; if False, match current mood
            min_confidence: Minimum confidence score for recommendations
            
        Returns:
            List of recommendation dictionaries, each containing:
            - book_id: Book ID
            - title: Book title
            - genre: Book genres (comma-separated)
            - sentiment_score: Match score (0.0 to 1.0)
            - recommendation_reason: Explainable reasoning for the recommendation
            - dominant_mood: Book's primary emotional tone
            - cover_image: Book cover image URL
            - author: Primary author name
        """
        if not user_mood or not user_mood.strip():
            logger.warning("Empty user mood provided")
            return []
        
        # Analyze user's mood
        user_analysis = self.analyzer.analyze_text(user_mood)
        user_dominant_mood = user_analysis.get('dominant_mood', 'neutral')
        user_moods = user_analysis.get('moods', {})
        
        logger.info(f"User mood analysis: {user_dominant_mood} (confidence: {user_analysis.get('confidence', 0.0):.2f})")
        
        # Get candidate books
        candidate_books = self._get_candidate_books(user_dominant_mood, improve_mood)
        
        if not candidate_books:
            logger.warning("No candidate books found")
            return []

        self._reset_cover_trace()

        # Score and rank books
        scored_books = []
        for book in candidate_books:
            score, reason, book_dominant_mood = self._score_book(
                book,
                user_mood,
                user_dominant_mood,
                user_moods,
                improve_mood,
            )

            if score >= min_confidence:
                scored_books.append({
                    'book': book,
                    'score': score,
                    'reason': reason,
                    'dominant_mood': book_dominant_mood,
                })

        # Sort by score (descending) with a small random jitter to avoid identical ordering every time
        scored_books.sort(key=lambda x: (x['score'] + random.uniform(0, 0.02)), reverse=True)

        deduped_books = self._dedupe_scored_books(scored_books)
        diversified_books = self._diversify_recommendations(deduped_books, limit)
        diversified_books = self._dedupe_by_book_id(diversified_books)

        recommendations = []
        for item in diversified_books[:limit]:
            book = item['book']
            cover_image = normalize_cover(self._cover_image_for(book))
            cover_source = self._cover_trace_map.get(book.id, {}).get('source', 'unknown')
            if cover_image == PLACEHOLDER_COVER_URL:
                logger.error(
                    "cover.resolve.invalid book_id=%s title=%s resolved=%r forcing_placeholder",
                    book.id,
                    book.title,
                    cover_image,
                )
                cover_image = PLACEHOLDER_COVER_URL
                cover_source = 'placeholder_forced'
            # Avoid showing a repeated 100% score; cap and round for display
            percent_score = int(round(item['score'] * 100))
            percent_score = max(40, min(97, percent_score))
            recommendations.append({
                'book_id': book.id,
                'title': book.title,
                'genre': ', '.join([g.name for g in book.genres.all()[:3]]),
                'sentiment_score': round(item['score'], 3),
                'match_percent': percent_score,
                'recommendation_reason': item['reason'],
                'dominant_mood': item.get('dominant_mood') or self._get_book_dominant_mood(book),
                'cover_image': cover_image,
                '_cover_resolved': True,
                '_cover_source': cover_source,
                'author': book.primary_author(),
                'description': book.description[:200] + '...' if book.description and len(book.description) > 200 else (book.description or ''),
            })

        self._log_cover_summary(len(recommendations))

        return recommendations

    def _make_identity(self, book: Book) -> str:
        """Return a stable identity for deduping editions/duplicates."""
        for ident in (book.isbn_13, book.isbn_10):
            if ident:
                return re.sub(r'[^0-9Xx]', '', ident).lower()
        return re.sub(r'\s+', ' ', (book.title or '')).strip().lower()

    def _dedupe_by_book_id(self, scored_books: List[Dict]) -> List[Dict]:
        """Enforce unique recommendations by primary key while preserving order."""
        seen_ids: set[int] = set()
        unique: List[Dict] = []
        for item in scored_books:
            book_id = item.get('book').id
            if book_id in seen_ids:
                continue
            seen_ids.add(book_id)
            unique.append(item)
        return unique

    def _dedupe_scored_books(self, scored_books: List[Dict]) -> List[Dict]:
        seen: set[str] = set()
        unique: List[Dict] = []
        for item in scored_books:
            key = self._make_identity(item['book'])
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _diversify_recommendations(self, scored_books: List[Dict], limit: int) -> List[Dict]:
        """
        Provide varied recommendations by limiting repeats from the same author/mood
        while keeping the highest scoring items first.
        """
        if not scored_books:
            return []

        pool_size = max(limit * 4, 20)
        pool = scored_books[:pool_size]

        picks: List[Dict] = []
        author_seen: set[str] = set()
        mood_counts: Dict[str, int] = {}

        # Always keep the top 1-2 highest scores, then mix in shuffled remainder for variety.
        guaranteed = pool[:2]
        remainder = pool[2:]
        random.shuffle(remainder)
        blended_pool = guaranteed + remainder

        for item in blended_pool:
            if len(picks) >= limit:
                break
            book = item['book']
            author = (book.primary_author() or '').strip().lower()
            dominant_mood = (item.get('dominant_mood') or 'neutral').lower()

            if author and author in author_seen:
                continue
            if mood_counts.get(dominant_mood, 0) >= 2 and len(pool) > limit:
                # Avoid flooding with the exact same mood when we have options
                continue

            if author:
                author_seen.add(author)
            mood_counts[dominant_mood] = mood_counts.get(dominant_mood, 0) + 1
            picks.append(item)

        # If we still need more, fill from the remaining scored list in order
        if len(picks) < limit:
            for item in scored_books:
                if len(picks) >= limit:
                    break
                if item in picks:
                    continue
                picks.append(item)

        return picks

    def _cover_image_for(self, book: Book) -> str:
        """
        Choose the best available cover image with multiple fallbacks.
        """
        cover = book.cover_image if isinstance(book.cover_image, str) else ''
        cover = cover.strip()
        return self._resolve_cover_image(
            cover=cover,
            isbn_13=book.isbn_13 or '',
            isbn_10=book.isbn_10 or '',
            title=book.title or '',
            author=book.primary_author() or '',
            book_id=book.id,
        )
    
    def _get_candidate_books(self, user_mood: str, improve_mood: bool) -> QuerySet[Book]:
        """
        Get candidate books based on user mood and improvement preference.
        
        Args:
            user_mood: User's dominant mood
            improve_mood: Whether to improve mood or match it
            
        Returns:
            QuerySet of candidate books
        """
        # Base query - get books with descriptions
        base_query = Book.objects.filter(
            description__isnull=False
        ).exclude(
            description=''
        ).select_related().prefetch_related('genres', 'authors')
        
        if improve_mood:
            # Get compatible moods that improve the user's mood
            compatible_moods = MOOD_COMPATIBILITY.get(user_mood, [])
            
            if compatible_moods:
                # Filter by sentiment label for quick filtering
                # Positive books are more likely to improve mood
                if user_mood in ['sad', 'anxious', 'angry']:
                    base_query = base_query.filter(sentiment_label='positive')
                elif user_mood in ['happy', 'excited', 'hopeful']:
                    # For already positive moods, maintain or enhance
                    base_query = base_query.filter(
                        Q(sentiment_label__in=['positive', 'neutral'])
                        | Q(sentiment_label='')
                        | Q(sentiment_label__isnull=True)
                    )
            else:
                # Default to positive books for mood improvement
                base_query = base_query.filter(sentiment_label='positive')
        else:
            # Match current mood
            if user_mood in ['sad', 'anxious', 'angry']:
                base_query = base_query.filter(sentiment_label='negative')
            elif user_mood in ['happy', 'excited', 'hopeful', 'inspired']:
                base_query = base_query.filter(sentiment_label='positive')
            else:
                base_query = base_query.filter(
                    Q(sentiment_label='neutral')
                    | Q(sentiment_label='')
                    | Q(sentiment_label__isnull=True)
                )
        
        # OPTIMIZATION: Prefer pre-computed mood_scores, but do not exclude books
        # without them to avoid repeating the same small candidate pool.
        
        # Order by ratings for better recommendations
        base_query = base_query.order_by('-average_rating', '-ratings_count')
        
        # PERFORMANCE: Use a larger candidate pool to improve variety.
        return base_query[:500]
    
    def _score_book(
        self,
        book: Book,
        user_mood_text: str,
        user_dominant_mood: str,
        user_moods: Dict[str, float],
        improve_mood: bool
    ) -> Tuple[float, str, str]:
        """
        Score a book's match with user mood and generate explainable reasoning.
        
        Returns:
            Tuple of (score, reason, book_dominant_mood)
        """
        # Get book's mood analysis
        # Use stored analysis if available to avoid expensive re-computation
        if book.mood_scores and book.mood_scores != '{}' and book.dominant_mood:
            book_moods = book.mood_scores
            if isinstance(book_moods, str):
                try:
                    import json
                    book_moods = json.loads(book_moods)
                except:
                    book_moods = {}
            book_dominant_mood = book.dominant_mood
        else:
            # OPTIMIZATION: Use fast sentiment label-based fallback instead of expensive transformer
            # This is 50-100x faster than running full transformer inference
            sentiment = book.sentiment_label or 'neutral'
            
            # Map sentiment to basic moods for fast scoring
            if sentiment == 'positive':
                book_moods = {'happy': 0.8, 'hopeful': 0.7, 'inspired': 0.6, 'relaxed': 0.5, 'excited': 0.7}
            elif sentiment == 'negative':
                book_moods = {'sad': 0.8, 'anxious': 0.7, 'angry': 0.6, 'nostalgic': 0.4}
            else:
                book_moods = {'relaxed': 0.6, 'neutral': 0.8, 'thoughtful': 0.5}
            
            # Set dominant mood based on sentiment
            book_dominant_mood = 'happy' if sentiment == 'positive' else ('sad' if sentiment == 'negative' else 'relaxed')
        
        # Calculate match score
        if improve_mood:
            # Score based on compatibility
            compatible_moods = MOOD_COMPATIBILITY.get(user_dominant_mood, [])
            compatibility_score = sum(book_moods.get(mood, 0.0) for mood in compatible_moods)
            
            # Boost score if book has strong positive moods
            positive_boost = sum(book_moods.get(m, 0.0) for m in ['happy', 'hopeful', 'inspired', 'relaxed'])
            
            match_score = (compatibility_score * 0.6) + (positive_boost * 0.4)
            
            # Generate reason
            top_book_moods = sorted(book_moods.items(), key=lambda x: x[1], reverse=True)[:2]
            mood_descriptions = [f"{mood}" for mood, score in top_book_moods if score > 0.2]
            
            if mood_descriptions:
                reason = (
                    f"This book evokes {', '.join(mood_descriptions)} emotions, which can help "
                    f"improve your current {user_dominant_mood} mood. "
                    f"The narrative focuses on themes that promote emotional well-being and positive outlook."
                )
            else:
                reason = (
                    f"This book's uplifting narrative can help shift your {user_dominant_mood} mood "
                    f"toward a more positive emotional state."
                )
        else:
            # Score based on direct match
            direct_match = book_moods.get(user_dominant_mood, 0.0)
            
            # Also consider semantic similarity
            semantic_match = self.analyzer.match_mood(user_mood_text, book_moods)
            
            match_score = (direct_match * 0.7) + (semantic_match * 0.3)
            
            # Generate reason
            if book_dominant_mood == user_dominant_mood:
                reason = (
                    f"This book matches your {user_dominant_mood} mood. "
                    f"Its themes and emotional tone resonate with your current emotional state, "
                    f"providing a relatable reading experience."
                )
            else:
                top_book_moods = sorted(book_moods.items(), key=lambda x: x[1], reverse=True)[:2]
                mood_descriptions = [f"{mood}" for mood, score in top_book_moods if score > 0.2]
                
                if mood_descriptions:
                    reason = (
                        f"This book explores {', '.join(mood_descriptions)} themes that align with "
                        f"your {user_dominant_mood} mood, offering a narrative that understands "
                        f"and reflects your current emotional experience."
                    )
                else:
                    reason = (
                        f"This book's emotional tone aligns with your {user_dominant_mood} mood, "
                        f"providing a reading experience that matches your current state of mind."
                    )
        
        # Normalize score to 0-1 range
        match_score = min(max(match_score, 0.0), 1.0)
        
        return match_score, reason, book_dominant_mood
    
    def _get_book_text(self, book: Book) -> str:
        """Extract all textual content from a book for analysis."""
        text_parts = []
        
        if book.title:
            text_parts.append(book.title)
        if book.subtitle:
            text_parts.append(book.subtitle)
        if book.description:
            text_parts.append(book.description)
        
        # Could also include reviews if available
        # if hasattr(book, 'reviews'):
        #     review_texts = [r.text for r in book.reviews.all()[:3]]
        #     text_parts.extend(review_texts)
        
        return ' '.join(text_parts)
    
    def _get_book_dominant_mood(self, book: Book) -> str:
        """Get the dominant mood for a book (from analysis or cached)."""
        book_text = self._get_book_text(book)
        analysis = self.analyzer.analyze_text(book_text)
        return analysis.get('dominant_mood', 'neutral')

    @lru_cache(maxsize=512)
    def _resolve_cover_image(
        self,
        cover: str,
        isbn_13: str,
        isbn_10: str,
        title: str,
        author: str,
        book_id: int | None = None,
    ) -> str:
        """
        Resolve the best available cover URL with multiple fallbacks:
        1) Existing cover (forced to https)
        2) Open Library cover by ISBN
        3) Google Books thumbnail by title/author
        4) Static placeholder
        """
        placeholder = PLACEHOLDER_COVER_URL
        # Invariant: this method always returns a non-empty cover URL string.
        logger.info(
            "cover.resolve.start book_id=%s title=%s cover=%s isbn_13=%s isbn_10=%s",
            book_id,
            title,
            cover,
            isbn_13,
            isbn_10,
        )

        def _sanitize(url: str) -> str:
            if not url or not isinstance(url, str):
                return ''
            url = url.strip()
            if url.lower() == 'null':
                return ''
            if url.startswith('http://'):
                url = 'https://' + url[len('http://'):]
            return url

        existing = _sanitize(cover)
        if existing:
            self._record_cover_trace(
                book_id=book_id,
                title=title,
                source='db_cover',
                resolved=existing,
                reason='cover_image_present',
                cover=cover,
                isbn_10=isbn_10,
                isbn_13=isbn_13,
            )
            logger.info(
                "cover.resolve.branch book_id=%s source=db_cover resolved=%s",
                book_id,
                existing,
            )
            return normalize_cover(existing)

        for ident in (isbn_13, isbn_10):
            clean = (ident or '').replace('-', '').strip()
            if clean:
                openlibrary_url = f'https://covers.openlibrary.org/b/isbn/{clean}-L.jpg'
                self._record_cover_trace(
                    book_id=book_id,
                    title=title,
                    source='openlibrary_isbn',
                    resolved=openlibrary_url,
                    reason='isbn_present',
                    cover=cover,
                    isbn_10=isbn_10,
                    isbn_13=isbn_13,
                )
                logger.info(
                    "cover.resolve.branch book_id=%s source=openlibrary_isbn url=%s",
                    book_id,
                    openlibrary_url,
                )
                return normalize_cover(openlibrary_url)

        logger.info("cover.resolve.skip book_id=%s reason=no_isbn", book_id)

        google_cover, google_reason = self._lookup_google_cover(
            title,
            author,
            book_id=book_id,
            placeholder=placeholder,
        )
        if google_reason == 'google_ok':
            self._record_cover_trace(
                book_id=book_id,
                title=title,
                source='google_books',
                resolved=google_cover,
                reason=google_reason,
                cover=cover,
                isbn_10=isbn_10,
                isbn_13=isbn_13,
            )
            logger.info(
                "cover.resolve.branch book_id=%s source=google_books resolved=%s",
                book_id,
                google_cover,
            )
            return normalize_cover(google_cover)

        self._record_cover_trace(
            book_id=book_id,
            title=title,
            source='placeholder',
            resolved=placeholder,
            reason=google_reason or 'google_no_cover',
            cover=cover,
            isbn_10=isbn_10,
            isbn_13=isbn_13,
        )
        logger.info(
            "cover.resolve.branch book_id=%s source=placeholder resolved=%s reason=%s",
            book_id,
            placeholder,
            google_reason or 'google_no_cover',
        )
        return normalize_cover(placeholder)

    def _lookup_google_cover(
        self,
        title: str,
        author: str,
        *,
        book_id: int | None = None,
        placeholder: str,
    ) -> tuple[str, str]:
        """Lightweight Google Books lookup for a cover thumbnail."""
        placeholder = normalize_cover(placeholder)
        query_parts = []
        if title:
            query_parts.append(title)
        if author:
            query_parts.append(author)
        if not query_parts:
            logger.info("cover.google.skip book_id=%s reason=missing_query", book_id)
            return placeholder, 'google_missing_query'

        query = ' '.join(query_parts)
        try:
            result = search_google_books(query, max_results=1, language='en')
        except GoogleBooksError as exc:
            logger.warning("cover.google.error book_id=%s query=%s error=%s", book_id, query, exc)
            return placeholder, f'google_error:{exc}'
        except Exception as exc:
            logger.exception("cover.google.exception book_id=%s query=%s", book_id, query)
            return placeholder, f'google_exception:{exc.__class__.__name__}'

        if not result:
            logger.info("cover.google.empty book_id=%s query=%s", book_id, query)
            return placeholder, 'google_empty_results'
        thumbnail = getattr(result[0], 'thumbnail', '') or ''
        if thumbnail.startswith('http://'):
            thumbnail = 'https://' + thumbnail[len('http://'):]
        if not thumbnail:
            logger.info("cover.google.missing_thumbnail book_id=%s query=%s", book_id, query)
            return placeholder, 'google_missing_thumbnail'
        logger.info("cover.google.ok book_id=%s query=%s thumbnail=%s", book_id, query, thumbnail)
        return thumbnail, 'google_ok'

    def _reset_cover_trace(self) -> None:
        self._cover_trace_map: Dict[int, Dict[str, str]] = {}
        self._cover_source_counts: Dict[str, int] = {}
        self._cover_external_failures: List[int] = []

    def _record_cover_trace(
        self,
        *,
        book_id: int | None,
        title: str,
        source: str,
        resolved: str,
        reason: str,
        cover: str,
        isbn_10: str,
        isbn_13: str,
    ) -> None:
        if book_id is None:
            return
        if not hasattr(self, "_cover_trace_map"):
            return
        self._cover_trace_map[book_id] = {
            'book_id': str(book_id),
            'title': title,
            'source': source,
            'resolved': resolved,
            'reason': reason,
            'cover': cover,
            'isbn_10': isbn_10,
            'isbn_13': isbn_13,
        }
        self._cover_source_counts[source] = self._cover_source_counts.get(source, 0) + 1
        if source == 'placeholder' and reason and reason.startswith('google_'):
            self._cover_external_failures.append(book_id)

    def _log_cover_summary(self, total: int) -> None:
        if not hasattr(self, "_cover_source_counts") or total <= 0:
            return
        db_count = self._cover_source_counts.get('db_cover', 0)
        openlibrary_count = self._cover_source_counts.get('openlibrary_isbn', 0)
        google_count = self._cover_source_counts.get('google_books', 0)
        placeholder_count = (
            self._cover_source_counts.get('placeholder', 0)
            + self._cover_source_counts.get('placeholder_forced', 0)
        )
        placeholder_pct = (placeholder_count / total) * 100
        logger.info(
            "cover.summary total=%s db=%s openlibrary=%s google=%s placeholder=%s placeholder_pct=%.1f "
            "external_failures=%s",
            total,
            db_count,
            openlibrary_count,
            google_count,
            placeholder_count,
            placeholder_pct,
            self._cover_external_failures,
        )


# Global recommender instance
_recommender_instance: Optional[MoodRecommender] = None


def get_mood_recommender() -> MoodRecommender:
    """Get or create the global mood recommender instance."""
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = MoodRecommender()
    return _recommender_instance

