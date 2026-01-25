"""
Clean a JSON dataset of books for mood-based recommendations.
"""
import argparse
import re

import pandas as pd

GENRE_MAP = {
    "Self-Help": "Motivation",
    "Biography": "Inspiration",
    "Horror": "Dark",
    "Crime": "Thriller",
    "Comedy": "Feel-Good",
    "Romance": "Emotional",
    "Philosophy": "Calm",
    "Business": "Neutral",
    "Fiction": "Fiction",
    "Fantasy": "Fantasy",
    "Drama": "Drama",
    "Adventure": "Adventure",
    "Thriller": "Thriller",
}

GENERIC_PHRASES = [
    "This analytical work examines",
    "This reference work offers",
]

KEEP_COLUMNS = [
    "book_id",
    "title",
    "author",
    "genres",
    "description",
    "language",
    "published_year",
    "average_rating",
    "ratings_count",
    "page_count",
]


def normalize_language(series: pd.Series) -> pd.Series:
    normalized = series.fillna("").astype(str).str.strip().str.lower()
    return normalized.replace({"english": "en"})


def filter_descriptions(df: pd.DataFrame) -> pd.DataFrame:
    descriptions = df["description"].fillna("").astype(str).str.strip()
    nonempty_mask = descriptions != ""
    if GENERIC_PHRASES:
        pattern = "|".join(re.escape(phrase) for phrase in GENERIC_PHRASES)
        generic_mask = descriptions.str.contains(pattern, case=False, regex=True)
    else:
        generic_mask = False
    return df[nonempty_mask & ~generic_mask]


def map_genres(genres_value):
    if genres_value is None or (isinstance(genres_value, float) and pd.isna(genres_value)):
        return []
    if isinstance(genres_value, list):
        genres_list = genres_value
    else:
        genres_list = [genres_value]
    mapped = []
    for genre in genres_list:
        if genre is None:
            continue
        genre_name = str(genre).strip()
        if not genre_name:
            continue
        mapped_genre = GENRE_MAP.get(genre_name, genre_name)
        if mapped_genre not in mapped:
            mapped.append(mapped_genre)
    return mapped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean books dataset for mood-based recommendations."
    )
    parser.add_argument(
        "--input",
        default="books_dataset_5000.json",
        help="Path to input JSON file (array of book objects).",
    )
    parser.add_argument(
        "--output",
        default="books_dataset_cleaned.json",
        help="Path for cleaned JSON output.",
    )
    parser.add_argument(
        "--min-ratings-count",
        type=int,
        default=50,
        help="Minimum ratings_count to keep. Set to 0 to disable this filter.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    df = pd.read_json(args.input)

    df["language"] = normalize_language(df["language"])
    df = df[df["language"] == "en"]
    df = filter_descriptions(df)

    if args.min_ratings_count and args.min_ratings_count > 0:
        ratings = pd.to_numeric(df["ratings_count"], errors="coerce")
        df = df[ratings >= args.min_ratings_count]

    df["genres_mapped"] = df["genres"].apply(map_genres)
    df["book_id"] = df["book_id"].astype(str)

    output_columns = KEEP_COLUMNS + ["genres_mapped"]
    df = df.loc[:, output_columns]

    df.to_json(args.output, orient="records", indent=2, force_ascii=False)
    print(f"Wrote {len(df)} records to {args.output}")


if __name__ == "__main__":
    main()
