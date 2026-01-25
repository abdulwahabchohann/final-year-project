"""
Deterministic mood-based recommender for JSON book datasets.

Designed for Django integration without heavy ML dependencies.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

MOODS: List[str] = []
compute_intensity = None
compute_sentiment = None
round_probabilities = None
score_moods = None


def _ensure_helpers_loaded() -> None:
    global MOODS, compute_intensity, compute_sentiment, round_probabilities, score_moods
    if MOODS and compute_intensity and compute_sentiment and round_probabilities and score_moods:
        return
    try:
        from enrich_books_dataset import (
            MOODS as SOURCE_MOODS,
            compute_intensity as SOURCE_COMPUTE_INTENSITY,
            compute_sentiment as SOURCE_COMPUTE_SENTIMENT,
            round_probabilities as SOURCE_ROUND_PROBABILITIES,
            score_moods as SOURCE_SCORE_MOODS,
        )
    except ImportError as exc:  # pragma: no cover - fallback should not trigger in repo
        raise ImportError(
            "enrich_books_dataset.py must be importable for deterministic mood scoring."
        ) from exc

    MOODS = list(SOURCE_MOODS)
    compute_intensity = SOURCE_COMPUTE_INTENSITY
    compute_sentiment = SOURCE_COMPUTE_SENTIMENT
    round_probabilities = SOURCE_ROUND_PROBABILITIES
    score_moods = SOURCE_SCORE_MOODS


DEFAULT_WEIGHTS = {
    "mood": 0.6,
    "sentiment": 0.25,
    "intensity": 0.15,
}


@dataclass(frozen=True)
class MoodProfile:
    mood_scores: Dict[str, float]
    dominant_mood: str
    sentiment_score: float
    emotional_intensity: float


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_mood_scores(raw_scores: Dict[str, float]) -> Dict[str, float]:
    _ensure_helpers_loaded()
    cleaned = {mood: max(0.0, _safe_float(raw_scores.get(mood), 0.0) or 0.0) for mood in MOODS}
    total = sum(cleaned.values())
    if total <= 0:
        return {mood: 1.0 / len(MOODS) for mood in MOODS}
    return {mood: value / total for mood, value in cleaned.items()}


def _coerce_mood_scores(value: Any) -> Optional[Dict[str, float]]:
    if isinstance(value, dict):
        return {str(k): _safe_float(v, 0.0) or 0.0 for k, v in value.items()}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return {str(k): _safe_float(v, 0.0) or 0.0 for k, v in parsed.items()}
    return None


def _vectorize(mood_scores: Dict[str, float]) -> List[float]:
    _ensure_helpers_loaded()
    return [mood_scores.get(mood, 0.0) for mood in MOODS]


def _cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for av, bv in zip(a, b):
        dot += av * bv
        norm_a += av * av
        norm_b += bv * bv
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / math.sqrt(norm_a * norm_b)


def _top_moods(mood_scores: Dict[str, float], limit: int = 2, threshold: float = 0.12) -> List[str]:
    _ensure_helpers_loaded()
    ranked = sorted(mood_scores.items(), key=lambda item: item[1], reverse=True)
    filtered = [mood for mood, score in ranked if score >= threshold]
    return filtered[:limit] if filtered else [ranked[0][0]] if ranked else []


def _sentiment_alignment(user_sentiment: float, book_sentiment: float) -> float:
    if user_sentiment is None or book_sentiment is None:
        return 0.5
    return max(0.0, 1.0 - abs(book_sentiment - user_sentiment) / 2.0)


def _intensity_alignment(user_intensity: float, book_intensity: float) -> float:
    if user_intensity is None or book_intensity is None:
        return 0.5
    return max(0.0, 1.0 - abs(book_intensity - user_intensity))


class DatasetMoodRecommender:
    """
    Mood-based recommender operating on a JSON dataset.

    Deterministic scoring uses:
    - Mood similarity (cosine similarity over mood probabilities)
    - Sentiment distance alignment
    - Emotional intensity alignment
    """

    def __init__(
        self,
        dataset_path: str = "books_dataset_5000.json",
        weights: Optional[Dict[str, float]] = None,
        min_rating_count: int = 0,
    ) -> None:
        _ensure_helpers_loaded()
        self.dataset_path = dataset_path
        self.weights = weights or DEFAULT_WEIGHTS
        self.min_rating_count = min_rating_count
        self._books = self._load_books()
        self._prepare_books()

    def _load_books(self) -> List[Dict[str, Any]]:
        with open(self.dataset_path, "r", encoding="utf-8") as infile:
            data = json.load(infile)
        if not isinstance(data, list):
            raise ValueError("Dataset must be a JSON array of book objects.")
        return data

    def _prepare_books(self) -> None:
        prepared = []
        for book in self._books:
            if self.min_rating_count and (book.get("ratings_count") or 0) < self.min_rating_count:
                continue
            self._ensure_book_fields(book)
            prepared.append(book)
        self._books = prepared

    def _ensure_book_fields(self, book: Dict[str, Any]) -> None:
        _ensure_helpers_loaded()
        title = book.get("title") or ""
        description = book.get("description") or ""
        genres = book.get("genres") or []
        if not isinstance(genres, list):
            genres = [genres]

        mood_scores = _coerce_mood_scores(book.get("mood_scores"))
        if not mood_scores:
            mood_scores = score_moods(f"{title}. {description}".strip(), genres)
        mood_scores = _normalize_mood_scores(mood_scores)
        mood_scores = round_probabilities(mood_scores)

        dominant_mood = book.get("dominant_mood")
        if dominant_mood not in mood_scores:
            dominant_mood = max(mood_scores, key=mood_scores.get)

        sentiment_score = _safe_float(book.get("sentiment_score"))
        if sentiment_score is None:
            sentiment_score = compute_sentiment(f"{title}. {description}".strip(), mood_scores)

        emotional_intensity = _safe_float(book.get("emotional_intensity"))
        if emotional_intensity is None:
            emotional_intensity = compute_intensity(mood_scores)

        book["mood_scores"] = mood_scores
        book["dominant_mood"] = dominant_mood
        book["sentiment_score"] = sentiment_score
        book["emotional_intensity"] = emotional_intensity
        book["_mood_vector"] = _vectorize(mood_scores)

    def analyze_user_mood(self, user_text: str) -> MoodProfile:
        _ensure_helpers_loaded()
        mood_scores = score_moods(user_text, [])
        mood_scores = _normalize_mood_scores(mood_scores)
        mood_scores = round_probabilities(mood_scores)
        dominant_mood = max(mood_scores, key=mood_scores.get) if mood_scores else "Neutral"
        sentiment_score = compute_sentiment(user_text, mood_scores)
        emotional_intensity = compute_intensity(mood_scores)
        return MoodProfile(
            mood_scores=mood_scores,
            dominant_mood=dominant_mood,
            sentiment_score=sentiment_score,
            emotional_intensity=emotional_intensity,
        )

    def recommend(self, user_text: str, top_n: int = 5) -> List[Dict[str, Any]]:
        if not user_text or not user_text.strip():
            return []

        user_profile = self.analyze_user_mood(user_text)
        user_vector = _vectorize(user_profile.mood_scores)

        scored = []
        for book in self._books:
            score, components = self._score_book(user_profile, user_vector, book)
            explanation = self._build_explanation(user_profile, book, components)
            scored.append(
                {
                    "book_id": book.get("book_id"),
                    "title": book.get("title"),
                    "author": book.get("author"),
                    "genres": book.get("genres", []),
                    "description": book.get("description"),
                    "average_rating": book.get("average_rating"),
                    "ratings_count": book.get("ratings_count"),
                    "dominant_mood": book.get("dominant_mood"),
                    "sentiment_score": book.get("sentiment_score"),
                    "emotional_intensity": book.get("emotional_intensity"),
                    "score": round(score, 4),
                    "score_components": components,
                    "explanation": explanation,
                }
            )

        scored.sort(
            key=lambda item: (
                -item["score"],
                -(item.get("average_rating") or 0.0),
                -(item.get("ratings_count") or 0),
                str(item.get("title") or ""),
            )
        )

        return scored[: max(top_n, 0)]

    def _score_book(
        self,
        user_profile: MoodProfile,
        user_vector: List[float],
        book: Dict[str, Any],
    ) -> Tuple[float, Dict[str, float]]:
        book_vector = book.get("_mood_vector") or _vectorize(book.get("mood_scores", {}))
        mood_similarity = _cosine_similarity(user_vector, book_vector)

        sentiment_alignment = _sentiment_alignment(
            user_profile.sentiment_score, _safe_float(book.get("sentiment_score"), 0.0)
        )
        intensity_alignment = _intensity_alignment(
            user_profile.emotional_intensity, _safe_float(book.get("emotional_intensity"), 0.0)
        )

        score = (
            self.weights["mood"] * mood_similarity
            + self.weights["sentiment"] * sentiment_alignment
            + self.weights["intensity"] * intensity_alignment
        )

        components = {
            "mood_similarity": round(mood_similarity, 4),
            "sentiment_alignment": round(sentiment_alignment, 4),
            "intensity_alignment": round(intensity_alignment, 4),
        }
        return score, components

    def _build_explanation(
        self,
        user_profile: MoodProfile,
        book: Dict[str, Any],
        components: Dict[str, float],
    ) -> str:
        book_moods = book.get("mood_scores", {})
        user_top = _top_moods(user_profile.mood_scores, limit=2)
        book_top = _top_moods(book_moods, limit=2)
        shared = [mood for mood in user_top if mood in book_top]

        reasons = []
        if shared:
            reasons.append(f"Mood overlap on {', '.join(shared)}.")
        else:
            reasons.append(
                f"Your mood leans {', '.join(user_top)}, while this book is strongest in {', '.join(book_top)}."
            )

        sentiment_gap = abs((book.get("sentiment_score") or 0.0) - user_profile.sentiment_score)
        if sentiment_gap <= 0.2:
            reasons.append(f"Sentiment is close to yours (delta {sentiment_gap:.2f}).")
        elif (book.get("sentiment_score") or 0.0) > user_profile.sentiment_score:
            reasons.append("Sentiment is more positive, offering a lift.")
        else:
            reasons.append("Sentiment is more subdued, matching a softer tone.")

        intensity_gap = abs((book.get("emotional_intensity") or 0.0) - user_profile.emotional_intensity)
        if intensity_gap <= 0.15:
            reasons.append("Emotional intensity aligns with your current level.")
        elif (book.get("emotional_intensity") or 0.0) > user_profile.emotional_intensity:
            reasons.append("Emotional intensity is higher for a more immersive experience.")
        else:
            reasons.append("Emotional intensity is gentler for a lighter read.")

        return " ".join(reasons)


_dataset_recommender_instance: Optional[DatasetMoodRecommender] = None


def get_dataset_recommender(
    dataset_path: str = "books_dataset_5000.json",
    min_rating_count: int = 0,
) -> DatasetMoodRecommender:
    global _dataset_recommender_instance
    if (
        _dataset_recommender_instance is None
        or _dataset_recommender_instance.dataset_path != dataset_path
        or _dataset_recommender_instance.min_rating_count != min_rating_count
    ):
        _dataset_recommender_instance = DatasetMoodRecommender(
            dataset_path=dataset_path,
            min_rating_count=min_rating_count,
        )
    return _dataset_recommender_instance
