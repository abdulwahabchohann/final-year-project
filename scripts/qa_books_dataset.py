"""
Run QA checks on an enriched books dataset and write a JSON report.
"""
from __future__ import annotations

import argparse
import json
import random
from typing import Any, Dict, List, Tuple


SUM_TOLERANCE = 1e-3
DEFAULT_SAMPLE_SEED = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QA check for enriched books dataset.")
    parser.add_argument(
        "--input",
        default="books_dataset_5000.json",
        help="Path to enriched books JSON file.",
    )
    parser.add_argument(
        "--output",
        default="books_dataset_qacheck.json",
        help="Path to output QA report JSON.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=50,
        help="Number of books to sample for validation checks.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SAMPLE_SEED,
        help="Random seed for sampling.",
    )
    return parser.parse_args()


def load_dataset(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as infile:
        data = json.load(infile)
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON array.")
    return data


def coerce_mood_scores(value: Any) -> Tuple[Dict[str, float], bool]:
    if isinstance(value, dict):
        try:
            return {str(k): float(v) for k, v in value.items()}, True
        except (TypeError, ValueError):
            return {}, False
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}, False
        if isinstance(parsed, dict):
            try:
                return {str(k): float(v) for k, v in parsed.items()}, True
            except (TypeError, ValueError):
                return {}, False
    return {}, False


def mood_sum_ok(mood_scores: Dict[str, float]) -> bool:
    if not mood_scores:
        return False
    total = sum(mood_scores.values())
    return abs(total - 1.0) <= SUM_TOLERANCE


def dominant_mood_ok(dominant_mood: Any, mood_scores: Dict[str, float]) -> bool:
    if not mood_scores or not dominant_mood:
        return False
    try:
        max_value = max(mood_scores.values())
    except ValueError:
        return False
    top_moods = {m for m, v in mood_scores.items() if abs(v - max_value) <= SUM_TOLERANCE}
    return str(dominant_mood) in top_moods


def number_in_range(value: Any, lower: float, upper: float) -> bool:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return lower <= numeric <= upper


def nonempty_text(value: Any) -> bool:
    if value is None:
        return False
    return bool(str(value).strip())


def validate_book(book: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    mood_scores, mood_ok = coerce_mood_scores(book.get("mood_scores"))
    if not mood_ok or not mood_sum_ok(mood_scores):
        failures.append("mood_scores_sum_not_1")
    if not dominant_mood_ok(book.get("dominant_mood"), mood_scores):
        failures.append("dominant_mood_mismatch")
    if not number_in_range(book.get("emotional_intensity"), 0.05, 1.0):
        failures.append("emotional_intensity_out_of_range")
    if not number_in_range(book.get("sentiment_score"), -1.0, 1.0):
        failures.append("sentiment_score_out_of_range")
    if not nonempty_text(book.get("title")):
        failures.append("title_empty")
    if not nonempty_text(book.get("description")):
        failures.append("description_empty")
    return failures


def dominant_mood_distribution(books: List[Dict[str, Any]]) -> Dict[str, int]:
    distribution: Dict[str, int] = {}
    for book in books:
        mood = book.get("dominant_mood")
        if mood is None or str(mood).strip() == "":
            mood = "UNKNOWN"
        mood_key = str(mood)
        distribution[mood_key] = distribution.get(mood_key, 0) + 1
    return dict(sorted(distribution.items(), key=lambda item: (-item[1], item[0])))


def compute_average(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def collect_numeric(books: List[Dict[str, Any]], field: str) -> List[float]:
    numbers: List[float] = []
    for book in books:
        try:
            numbers.append(float(book.get(field)))
        except (TypeError, ValueError):
            continue
    return numbers


def main() -> None:
    args = parse_args()
    books = load_dataset(args.input)

    sample_size = min(args.sample_size, len(books))
    rng = random.Random(args.seed)
    sampled = rng.sample(books, sample_size) if sample_size else []

    failed_books: List[Dict[str, Any]] = []
    for book in sampled:
        failures = validate_book(book)
        if failures:
            failed_books.append(
                {
                    "book_id": book.get("book_id"),
                    "title": book.get("title"),
                    "failures": failures,
                }
            )

    sentiment_scores = collect_numeric(books, "sentiment_score")
    emotional_intensity_scores = collect_numeric(books, "emotional_intensity")

    report = {
        "input_file": args.input,
        "total_books": len(books),
        "sample_seed": args.seed,
        "sample_size": sample_size,
        "sampled_book_ids": [book.get("book_id") for book in sampled],
        "failed_books": failed_books,
        "failed_books_count": len(failed_books),
        "dominant_mood_distribution": dominant_mood_distribution(books),
        "average_sentiment_score": round(compute_average(sentiment_scores), 4),
        "average_emotional_intensity": round(compute_average(emotional_intensity_scores), 4),
        "sentiment_score_stats": {
            "count": len(sentiment_scores),
            "missing": len(books) - len(sentiment_scores),
            "min": round(min(sentiment_scores), 4) if sentiment_scores else None,
            "max": round(max(sentiment_scores), 4) if sentiment_scores else None,
        },
        "emotional_intensity_stats": {
            "count": len(emotional_intensity_scores),
            "missing": len(books) - len(emotional_intensity_scores),
            "min": round(min(emotional_intensity_scores), 4) if emotional_intensity_scores else None,
            "max": round(max(emotional_intensity_scores), 4) if emotional_intensity_scores else None,
        },
    }

    with open(args.output, "w", encoding="utf-8") as outfile:
        json.dump(report, outfile, indent=2, ensure_ascii=False)

    print(f"Wrote QA report to {args.output}")


if __name__ == "__main__":
    main()
