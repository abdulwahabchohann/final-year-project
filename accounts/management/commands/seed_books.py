"""Seed a large catalogue of books using Open Library and Google Books."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from itertools import cycle
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from accounts.models import Author, Book, Genre
from accounts.services.external import fetch_open_library_books
from accounts.services.google_books import GoogleBooksError, search_google_books

OPEN_LIBRARY_EDITIONS_LIMIT = 10
OPEN_LIBRARY_EDITION_TIMEOUT = 5
PROGRESS_INTERVAL = 250


SUBJECTS: List[Tuple[str, str]] = [
    ("fiction", "Fiction"),
    ("science", "Science"),
    ("history", "History"),
    ("romance", "Romance"),
    ("fantasy", "Fantasy"),
    ("biography", "Biography"),
    ("children", "Children"),
    ("mystery", "Mystery"),
    ("thriller", "Thriller"),
    ("young_adult", "Young Adult"),
    ("self-help", "Self Help"),
    ("business", "Business"),
    ("technology", "Technology"),
    ("philosophy", "Philosophy"),
    ("health", "Health"),
    ("travel", "Travel"),
    ("art", "Art"),
    ("poetry", "Poetry"),
]


@dataclass
class CandidateBook:
    title: str
    description: str | None
    authors: List[str]
    genres: List[str]
    cover_image: str | None
    info_url: str | None
    published_year: int | None
    isbn_10: str
    isbn_13: str
    page_count: int | None
    language: str | None
    average_rating: Decimal | None = None
    ratings_count: int = 0


class Command(BaseCommand):
    help = "Seed the database with a rich catalogue of books (~5k) using Open Library and Google Books."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=5000,
            help="Number of unique books to seed (default: 5000).",
        )

    def handle(self, *args, **options):
        limit: int = max(1, options["limit"])
        self.stdout.write(f"Seeding up to {limit:,} books using Open Library + Google Books …")

        existing_keys = self._load_existing_keys()
        author_cache = self._build_author_cache()
        genre_cache = self._build_genre_cache()

        created = 0
        enriched = 0
        duplicates = 0
        total_fetched = 0
        google_attempts = 0

        subject_cycle = cycle(SUBJECTS)
        subject_page: Dict[str, int] = defaultdict(lambda: 1)
        exhausted_subjects: set[str] = set()

        while created < limit and len(exhausted_subjects) < len(SUBJECTS):
            slug, label = next(subject_cycle)
            if slug in exhausted_subjects:
                continue

            page = subject_page[slug]
            try:
                payloads = fetch_open_library_books(slug, page)
            except Exception as exc:  # pragma: no cover - network error safeguard
                self.stderr.write(f"Failed to fetch subject '{label}' (page {page}): {exc}")
                exhausted_subjects.add(slug)
                continue

            if not payloads:
                exhausted_subjects.add(slug)
                continue

            subject_page[slug] += 1
            total_fetched += len(payloads)

            if total_fetched % (PROGRESS_INTERVAL * 4) == 0:
                self.stdout.write(f"Fetched {total_fetched:,} Open Library records so far …")

            for record in payloads:
                candidate = self._build_candidate(record)
                if not candidate:
                    continue

                key = self._make_dedupe_key(candidate)
                if not key or key in existing_keys:
                    duplicates += 1
                    continue

                enrichment = None
                if candidate.isbn_13 or candidate.isbn_10:
                    try:
                        enrichment = self._enrich_from_google(candidate)
                        google_attempts += 1
                    except GoogleBooksError as exc:
                        self.stderr.write(f"Google Books lookup failed for '{candidate.title}': {exc}")
                    except Exception as exc:  # pragma: no cover - defensive
                        self.stderr.write(f"Unexpected Google Books error for '{candidate.title}': {exc}")

                if enrichment:
                    if enrichment.get("average_rating") is not None:
                        candidate.average_rating = enrichment["average_rating"]
                        candidate.ratings_count = enrichment.get("ratings_count", candidate.ratings_count)
                        enriched += 1
                    candidate.cover_image = enrichment.get("cover_image") or candidate.cover_image
                    candidate.page_count = enrichment.get("page_count") or candidate.page_count
                    candidate.language = enrichment.get("language") or candidate.language
                    candidate.published_year = enrichment.get("published_year") or candidate.published_year

                try:
                    saved = self._persist_candidate(candidate, author_cache, genre_cache)
                except IntegrityError:
                    duplicates += 1
                    continue

                if saved:
                    created += 1
                    existing_keys.add(key)
                    if created % PROGRESS_INTERVAL == 0:
                        self.stdout.write(
                            f"Inserted {created:,} unique books "
                            f"({enriched:,} enriched, {duplicates:,} skipped duplicates)…"
                        )

                if created >= limit:
                    break

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created:,} books successfully "
                f"({enriched:,} enriched with ratings, {duplicates:,} duplicates skipped, "
                f"{google_attempts:,} Google lookups executed)."
            )
        )

    # ------------------------------------------------------------------ helpers

    def _load_existing_keys(self) -> set[str]:
        keys: set[str] = set()
        for isbn13, isbn10, title in Book.objects.values_list("isbn_13", "isbn_10", "title"):
            key = self._compose_key(isbn13 or "", isbn10 or "", title or "")
            if key:
                keys.add(key)
        return keys

    def _build_author_cache(self) -> Dict[str, Author]:
        cache: Dict[str, Author] = {}
        for author in Author.objects.all():
            cache[author.full_name.lower()] = author
        return cache

    def _build_genre_cache(self) -> Dict[str, Genre]:
        cache: Dict[str, Genre] = {}
        for genre in Genre.objects.all():
            cache[genre.name.lower()] = genre
        return cache

    def _build_candidate(self, record) -> Optional[CandidateBook]:
        isbn_10 = ""
        isbn_13 = ""
        page_count = None
        language = None
        published_year = record.published_year

        meta = self._fetch_open_library_editions(record.info_url)
        if meta:
            isbn_10 = meta.get("isbn_10", "")
            isbn_13 = meta.get("isbn_13", "")
            page_count = meta.get("page_count")
            language = meta.get("language")
            published_year = published_year or meta.get("published_year")

        title = record.title.strip() if record.title else ""
        if not title:
            return None

        authors = [a.strip() for a in record.authors if a and a.strip()]
        genres = [g.strip() for g in record.categories if g and g.strip()]

        return CandidateBook(
            title=title,
            description=record.description,
            authors=authors,
            genres=genres,
            cover_image=record.thumbnail,
            info_url=record.info_url,
            published_year=published_year,
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            page_count=page_count,
            language=language,
        )

    def _fetch_open_library_editions(self, info_url: str | None) -> dict:
        if not info_url:
            return {}
        url = f"{info_url.rstrip('/')}/editions.json?limit={OPEN_LIBRARY_EDITIONS_LIMIT}"
        try:
            with urlopen(url, timeout=OPEN_LIBRARY_EDITION_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
            return {}

        entries = data.get("entries") or []
        isbn_10 = ""
        isbn_13 = ""
        page_count = None
        language = None
        year = None

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if not isbn_13:
                isbn_13 = self._extract_isbn(entry.get("isbn_13"))
            if not isbn_10:
                isbn_10 = self._extract_isbn(entry.get("isbn_10"))
            if page_count is None and isinstance(entry.get("number_of_pages"), int):
                page_count = entry["number_of_pages"]
            if language is None:
                languages = entry.get("languages") or []
                for lang in languages:
                    if isinstance(lang, dict) and lang.get("key"):
                        language = lang["key"].split("/")[-1]
                        break
            if year is None:
                year = self._extract_year(entry.get("publish_date"))
            if isbn_13 and isbn_10 and page_count and language and year:
                break

        meta: dict = {}
        if isbn_13:
            meta["isbn_13"] = isbn_13
        if isbn_10:
            meta["isbn_10"] = isbn_10
        if page_count:
            meta["page_count"] = page_count
        if language:
            meta["language"] = language
        if year:
            meta["published_year"] = year
        return meta

    def _extract_isbn(self, value) -> str:
        if isinstance(value, list) and value:
            value = value[0]
        if not isinstance(value, str):
            return ""
        return value.replace("-", "").strip()

    def _extract_year(self, value: str | None) -> Optional[int]:
        if not value:
            return None
        match = re.search(r"(19|20)\d{2}", value)
        return int(match.group()) if match else None

    def _enrich_from_google(self, candidate: CandidateBook) -> Optional[dict]:
        if not candidate.isbn_13 and not candidate.isbn_10:
            return None

        if candidate.isbn_13:
            query = f"isbn:{candidate.isbn_13}"
        elif candidate.isbn_10:
            query = f"isbn:{candidate.isbn_10}"
        else:
            query = candidate.title

        results = search_google_books(query, max_results=5, language="en")
        if not results:
            return None

        def normalise_isbn(value: str | None) -> str:
            return (value or "").replace("-", "").strip()

        match = None
        for item in results:
            isbn13 = normalise_isbn(item.isbn_13)
            isbn10 = normalise_isbn(item.isbn_10)
            if candidate.isbn_13 and isbn13 and isbn13 == candidate.isbn_13:
                match = item
                break
            if candidate.isbn_10 and isbn10 and isbn10 == candidate.isbn_10:
                match = item
                break

        if not match:
            match = results[0]

        payload = {
            "average_rating": Decimal(str(match.average_rating)) if match.average_rating is not None else None,
            "ratings_count": match.ratings_count or 0,
            "page_count": match.page_count,
            "language": match.language,
            "cover_image": match.thumbnail,
            "published_year": self._extract_year(match.published_year),
        }
        return payload

    def _persist_candidate(
        self,
        candidate: CandidateBook,
        author_cache: Dict[str, Author],
        genre_cache: Dict[str, Genre],
    ) -> Optional[Book]:
        with transaction.atomic():
            book = Book.objects.create(
                title=candidate.title,
                subtitle="",
                description=candidate.description or "",
                isbn_10=candidate.isbn_10,
                isbn_13=candidate.isbn_13,
                published_year=candidate.published_year,
                page_count=candidate.page_count,
                language=candidate.language or "",
                cover_image=candidate.cover_image or "",
                average_rating=candidate.average_rating,
                ratings_count=candidate.ratings_count,
            )

            author_objs = [self._get_author(name, author_cache) for name in candidate.authors]
            author_objs = [author for author in author_objs if author is not None]
            if author_objs:
                book.authors.set(author_objs)

            genre_objs = [self._get_genre(name, genre_cache) for name in candidate.genres]
            genre_objs = [genre for genre in genre_objs if genre is not None]
            if genre_objs:
                book.genres.set(genre_objs)

            return book

    def _get_author(self, name: str, cache: Dict[str, Author]) -> Optional[Author]:
        key = name.strip()
        if not key:
            return None
        normalised = key.lower()
        author = cache.get(normalised)
        if author:
            return author
        author, _ = Author.objects.get_or_create(full_name=key)
        cache[normalised] = author
        return author

    def _get_genre(self, name: str, cache: Dict[str, Genre]) -> Optional[Genre]:
        key = name.strip()
        if not key:
            return None
        normalised = key.lower()
        genre = cache.get(normalised)
        if genre:
            return genre
        genre, _ = Genre.objects.get_or_create(name=key)
        cache[normalised] = genre
        return genre

    def _make_dedupe_key(self, candidate: CandidateBook) -> Optional[str]:
        return self._compose_key(candidate.isbn_13, candidate.isbn_10, candidate.title)

    def _compose_key(self, isbn13: str, isbn10: str, title: str) -> Optional[str]:
        clean_isbn13 = (isbn13 or "").strip()
        clean_isbn10 = (isbn10 or "").strip()
        clean_title = (title or "").strip().lower()
        if clean_isbn13:
            return f"isbn13:{clean_isbn13.lower()}"
        if clean_isbn10:
            return f"isbn10:{clean_isbn10.lower()}"
        if clean_title:
            return f"title:{clean_title}"
        return None
