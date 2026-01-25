"""
Enrich a books JSON dataset with mood and sentiment fields.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from typing import Dict, Iterable, List


MOODS: List[str] = [
    "Happy",
    "Sad",
    "Dark",
    "Calm",
    "Excited",
    "Angry",
    "Fearful",
    "Hopeful",
    "Romantic",
    "Humorous",
    "Motivational",
    "Relaxed",
    "Thrilling",
    "Mysterious",
    "Reflective",
    "Adventurous",
]

MOOD_KEYWORDS: Dict[str, List[str]] = {
    "Happy": ["happy", "joy", "delight*", "uplift*", "cheer*", "bright", "smile", "celebrat*", "fun"],
    "Sad": ["sad", "tragic", "grief", "loss", "sorrow", "melanchol*", "depress*", "tear*", "heartbreak*"],
    "Dark": ["dark", "bleak", "grim", "haunt*", "sinister", "macabre", "shadow*", "dystopian", "brutal"],
    "Calm": ["calm", "peaceful", "serene", "quiet", "gentle", "soothing", "tranquil", "meditative"],
    "Excited": ["exciting", "action", "fast-paced", "battle", "chase", "adrenaline", "quest", "adventure"],
    "Angry": ["angry", "rage", "fury", "revenge", "vengeance", "violent", "conflict", "war"],
    "Fearful": ["fear", "terror", "horror", "scary", "fright*", "nightmare", "monster*", "suspense"],
    "Hopeful": ["hope", "optimis*", "redemption", "second chance", "inspir*", "triumph", "resilien*"],
    "Romantic": ["romance", "love", "passion", "relationship", "heart", "affection", "tender", "couple"],
    "Humorous": ["humor", "funny", "laugh", "comedy", "witty", "hilarious", "satire"],
    "Motivational": ["motivation", "inspir*", "empower*", "success", "goal", "habit", "self-help", "growth"],
    "Relaxed": ["relax*", "unwind", "cozy", "comfort", "easygoing", "laid-back", "slow"],
    "Thrilling": ["thrill*", "mystery", "crime", "twist", "investigation", "danger", "escape", "suspense"],
    "Mysterious": ["mystery", "enigmatic", "secret", "clue", "investigation", "unknown"],
    "Reflective": ["reflect*", "introspect*", "contemplat*", "philosoph*", "thoughtful", "meditation"],
    "Adventurous": ["adventure", "journey", "expedition", "quest", "explore", "travel", "voyage"],
}

GENRE_MOOD_BOOSTS: Dict[str, Dict[str, float]] = {
    "Horror": {"Dark": 0.9, "Fearful": 0.8, "Thrilling": 0.4},
    "Crime": {"Thrilling": 0.7, "Dark": 0.4, "Mysterious": 0.4},
    "Thriller": {"Thrilling": 0.8, "Fearful": 0.4},
    "Romance": {"Romantic": 0.9, "Hopeful": 0.3, "Happy": 0.3},
    "Comedy": {"Humorous": 0.9, "Happy": 0.5},
    "Self-Help": {"Motivational": 0.9, "Hopeful": 0.4, "Calm": 0.2},
    "Biography": {"Motivational": 0.4, "Reflective": 0.3, "Hopeful": 0.2},
    "Drama": {"Sad": 0.4, "Reflective": 0.3},
    "Fantasy": {"Excited": 0.4, "Adventurous": 0.4, "Hopeful": 0.2},
    "Adventure": {"Adventurous": 0.8, "Excited": 0.5},
    "Science Fiction": {"Excited": 0.4, "Mysterious": 0.4},
    "Mystery": {"Mysterious": 0.8, "Thrilling": 0.4},
    "Philosophy": {"Reflective": 0.8, "Calm": 0.4},
    "Business": {"Motivational": 0.4, "Calm": 0.2},
    "Poetry": {"Reflective": 0.4, "Calm": 0.3},
    "History": {"Reflective": 0.3, "Calm": 0.2},
    "Health": {"Motivational": 0.4, "Calm": 0.3},
    "Travel": {"Adventurous": 0.5, "Relaxed": 0.3, "Excited": 0.2},
    "Young Adult": {"Hopeful": 0.3, "Excited": 0.3},
    "Children's Literature": {"Happy": 0.4, "Relaxed": 0.3},
    "Western": {"Adventurous": 0.4, "Thrilling": 0.3},
    "Non-Fiction": {"Reflective": 0.3, "Calm": 0.2},
    "Technology": {"Reflective": 0.2, "Excited": 0.2},
    "Fiction": {"Happy": 0.2, "Sad": 0.2, "Reflective": 0.2},
}

POSITIVE_KEYWORDS = [
    "hope",
    "joy",
    "love",
    "uplift*",
    "inspir*",
    "empower*",
    "success",
    "triumph",
    "redemption",
    "peace",
    "calm",
    "delight*",
    "happy",
    "cheer*",
]

NEGATIVE_KEYWORDS = [
    "tragic",
    "grief",
    "loss",
    "dark",
    "bleak",
    "fear",
    "terror",
    "sad",
    "depress*",
    "rage",
    "anger",
    "violent",
    "haunt*",
    "despair",
    "sorrow",
]

WORD_RE = re.compile(r"[a-zA-Z']+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich book dataset with mood fields.")
    parser.add_argument(
        "--input",
        default="books_dataset_5000.json",
        help="Path to input JSON file.",
    )
    parser.add_argument(
        "--output",
        default="books_dataset_enriched.json",
        help="Path to output JSON file.",
    )
    return parser.parse_args()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def tokenize(text: str) -> List[str]:
    return WORD_RE.findall(text.lower())


def count_keyword_hits(text: str, tokens: List[str], keywords: Iterable[str]) -> int:
    hits = 0
    for keyword in keywords:
        if " " in keyword:
            if keyword in text:
                hits += 2
        elif keyword.endswith("*"):
            stem = keyword[:-1]
            hits += sum(1 for token in tokens if token.startswith(stem))
        else:
            hits += tokens.count(keyword)
    return hits


def score_moods(text: str, genres: List[str]) -> Dict[str, float]:
    normalized = normalize_text(text)
    tokens = tokenize(normalized)

    scores = {mood: 0.02 for mood in MOODS}

    for mood, keywords in MOOD_KEYWORDS.items():
        hits = count_keyword_hits(normalized, tokens, keywords)
        if hits:
            scores[mood] += hits * 0.08

    for genre in genres or []:
        for mood, boost in GENRE_MOOD_BOOSTS.get(genre, {}).items():
            scores[mood] += boost

    total = sum(scores.values())
    if total <= 0:
        return {mood: 1.0 / len(MOODS) for mood in MOODS}

    return {mood: score / total for mood, score in scores.items()}


def round_probabilities(probabilities: Dict[str, float]) -> Dict[str, float]:
    rounded = {mood: round(probabilities[mood], 4) for mood in MOODS}
    total = sum(rounded.values())
    if not rounded:
        return rounded
    diff = round(1.0 - total, 4)
    if diff != 0:
        dominant = max(rounded, key=rounded.get)
        rounded[dominant] = round(rounded[dominant] + diff, 4)
    return rounded


def compute_intensity(probabilities: Dict[str, float]) -> float:
    if not probabilities:
        return 0.0
    sorted_probs = sorted(probabilities.values(), reverse=True)
    top_prob = sorted_probs[0]
    gap = top_prob - (sorted_probs[1] if len(sorted_probs) > 1 else 0.0)
    intensity = top_prob + gap * 0.5
    return max(0.05, min(1.0, round(intensity, 4)))


def compute_sentiment(text: str, mood_scores: Dict[str, float]) -> float:
    normalized = normalize_text(text)
    tokens = tokenize(normalized)
    positive_hits = count_keyword_hits(normalized, tokens, POSITIVE_KEYWORDS)
    negative_hits = count_keyword_hits(normalized, tokens, NEGATIVE_KEYWORDS)

    positive_moods = [
        "Happy",
        "Hopeful",
        "Romantic",
        "Humorous",
        "Motivational",
        "Relaxed",
        "Calm",
        "Excited",
        "Adventurous",
    ]
    negative_moods = ["Sad", "Dark", "Angry", "Fearful"]

    mood_balance = sum(mood_scores.get(m, 0.0) for m in positive_moods) - sum(
        mood_scores.get(m, 0.0) for m in negative_moods
    )

    keyword_balance = (positive_hits - negative_hits) * 0.12
    raw_score = mood_balance + keyword_balance
    return round(max(-1.0, min(1.0, math.tanh(raw_score))), 4)


def enrich_book(book: Dict) -> Dict:
    title = book.get("title") or ""
    description = book.get("description") or ""
    genres = book.get("genres") or []
    if not isinstance(genres, list):
        genres = [genres]

    text = f"{title}. {description}".strip()
    mood_scores = score_moods(text, genres)
    dominant_mood = max(mood_scores, key=mood_scores.get) if mood_scores else ""
    emotional_intensity = compute_intensity(mood_scores)
    sentiment_score = compute_sentiment(text, mood_scores)

    book["mood_scores"] = round_probabilities(mood_scores)
    book["dominant_mood"] = dominant_mood
    book["emotional_intensity"] = emotional_intensity
    book["sentiment_score"] = sentiment_score
    return book


def main() -> None:
    args = parse_args()

    with open(args.input, "r", encoding="utf-8") as infile:
        books = json.load(infile)

    enriched = [enrich_book(book) for book in books]

    with open(args.output, "w", encoding="utf-8") as outfile:
        json.dump(enriched, outfile, indent=2, ensure_ascii=False)

    print(f"Wrote {len(enriched)} records to {args.output}")


if __name__ == "__main__":
    main()
