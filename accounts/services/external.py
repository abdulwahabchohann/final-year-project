"""External integrations for the book categories module."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from typing import Iterable, List, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils.text import slugify

from accounts.caching import delete_cached, get_cached_json, set_cached_json

logger = logging.getLogger(__name__)

CATEGORY_CACHE_KEY = 'accounts:categories:list:v1'
BOOKS_CACHE_KEY_TEMPLATE = 'accounts:categories:{slug}:{page}'

CANONICAL_CATEGORIES: Sequence[str] = [
    "Fiction",
    "Nonfiction",
    "Self-Help",
    "Business",
    "History",
    "Biography",
    "Science",
    "Technology",
    "Fantasy",
    "Romance",
    "Mystery",
    "Thriller",
    "Young Adult",
    "Children",
    "Poetry",
    "Comics",
    "Art",
    "Travel",
    "Health",
    "Religion",
    "Philosophy",
]

GOOGLE_API_ENDPOINT = 'https://www.googleapis.com/books/v1/volumes'
OPEN_LIBRARY_SUBJECTS_URL = 'https://openlibrary.org/subjects.json'
OPEN_LIBRARY_SUBJECT_DETAIL_URL = 'https://openlibrary.org/subjects/{slug}.json'
GOOGLE_TIMEOUT = 3.0
OPEN_LIBRARY_TIMEOUT = 3.0
MAX_RETRIES = 1


@dataclass(slots=True)
class CategoryPayload:
    slug: str
    display_name: str
    source: str
    book_count_estimate: int | None = None


@dataclass(slots=True)
class BookPayload:
    id: str
    title: str
    authors: List[str]
    description: str | None
    categories: List[str]
    thumbnail: str | None
    info_url: str | None
    published_year: int | None
    source: str


def _http_get_json(url: str, params: dict | None = None, timeout: float = 3.0, retries: int = 0) -> dict | None:
    """Fetch JSON from a remote endpoint with basic retry support."""
    if params:
        url = f'{url}?{urlencode(params)}'

    attempt = 0
    while True:
        attempt += 1
        try:
            req = Request(url, headers={'User-Agent': 'ReadWise/1.0'})
            with urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            logger.warning('External request failed (attempt %s/%s) for %s: %s', attempt, retries + 1, url, exc)
            if attempt >= retries + 1:
                return None


def _normalise_slug(value: str) -> str:
    slug = slugify(value or '')
    return slug or 'category'


def _merge_categories(open_library_subjects: Iterable[dict]) -> List[CategoryPayload]:
    merged: dict[str, CategoryPayload] = {}

    for name in CANONICAL_CATEGORIES:
        slug = _normalise_slug(name)
        merged[slug] = CategoryPayload(
            slug=slug,
            display_name=name,
            source='canonical',
            book_count_estimate=None,
        )

    for subject in open_library_subjects:
        name = subject.get('name') or subject.get('title')
        if not name:
            continue
        slug = subject.get('key')
        if slug:
            slug = slug.strip('/').split('/')[-1]
        slug = _normalise_slug(slug or name)
        work_count = subject.get('work_count')

        if slug in merged:
            payload = merged[slug]
            payload.book_count_estimate = payload.book_count_estimate or work_count
        else:
            merged[slug] = CategoryPayload(
                slug=slug,
                display_name=name,
                source='open_library',
                book_count_estimate=work_count,
            )

    return sorted(merged.values(), key=lambda item: item.display_name.lower())


def fetch_open_library_subjects(limit: int = 50) -> list[dict]:
    params = {'limit': limit}
    data = _http_get_json(
        OPEN_LIBRARY_SUBJECTS_URL,
        params=params,
        timeout=OPEN_LIBRARY_TIMEOUT,
        retries=MAX_RETRIES,
    )
    if not data:
        return []
    subjects = data.get('subjects', [])
    return [subject for subject in subjects if isinstance(subject, dict)]


def sync_categories(force_refresh: bool = False) -> List[CategoryPayload]:
    """Fetch categories from external sources, persist to DB, and refresh cache."""
    from accounts.models import Category

    if not force_refresh:
        cached = get_cached_json(CATEGORY_CACHE_KEY)
        if cached:
            return [
                CategoryPayload(
                    slug=item['slug'],
                    display_name=item['display_name'],
                    source=item.get('source', 'canonical'),
                    book_count_estimate=item.get('book_count_estimate'),
                )
                for item in cached
            ]

    subjects = fetch_open_library_subjects()
    merged = _merge_categories(subjects)

    existing = {category.slug: category for category in Category.objects.all()}
    to_create: list[Category] = []
    to_update: list[Category] = []

    for payload in merged:
        category = existing.get(payload.slug)
        if category:
            changed = False
            if category.display_name != payload.display_name:
                category.display_name = payload.display_name
                changed = True
            if category.source != payload.source:
                category.source = payload.source
                changed = True
            if changed:
                to_update.append(category)
        else:
            to_create.append(
                Category(
                    slug=payload.slug,
                    display_name=payload.display_name,
                    source=payload.source,
                )
            )

    if to_create:
        Category.objects.bulk_create(to_create, ignore_conflicts=True)
    if to_update:
        Category.objects.bulk_update(to_update, ['display_name', 'source'])

    dump = [
        {
            'slug': payload.slug,
            'display_name': payload.display_name,
            'source': payload.source,
            'book_count_estimate': payload.book_count_estimate,
        }
        for payload in merged
    ]
    set_cached_json(CATEGORY_CACHE_KEY, dump, timeout=60 * 60 * 12)
    return merged


def get_cached_category_list(force_refresh: bool = False) -> List[dict]:
    """Return the cached category list ready for serialization."""
    if not force_refresh:
        cached = get_cached_json(CATEGORY_CACHE_KEY)
        if cached:
            return cached
    payloads = sync_categories(force_refresh=True)
    if not payloads:
        from accounts.models import Genre

        return [
            {
                'slug': genre.slug,
                'display_name': genre.name,
                'source': 'local',
                'book_count_estimate': genre.books.count(),
            }
            for genre in Genre.objects.all().order_by('name')
        ]
    return [
        {
            'slug': payload.slug,
            'display_name': payload.display_name,
            'source': payload.source,
            'book_count_estimate': payload.book_count_estimate,
        }
        for payload in payloads
    ]


def invalidate_category_cache() -> None:
    delete_cached(CATEGORY_CACHE_KEY)


def _extract_year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r'(19|20)\d{2}', value)
    return int(match.group()) if match else None


def _normalise_google_item(item: dict) -> BookPayload | None:
    volume_id = item.get('id')
    info = item.get('volumeInfo', {})
    if not volume_id or not info:
        return None
    image_links = info.get('imageLinks') or {}

    return BookPayload(
        id=f'gb:{volume_id}',
        title=info.get('title') or 'Untitled',
        authors=info.get('authors') or [],
        description=info.get('description'),
        categories=info.get('categories') or [],
        thumbnail=image_links.get('thumbnail') or image_links.get('smallThumbnail'),
        info_url=info.get('infoLink') or item.get('selfLink'),
        published_year=_extract_year(info.get('publishedDate')),
        source='google',
    )


def fetch_google_books_for_category(display_name: str, page: int) -> List[BookPayload]:
    start_index = max((page - 1) * 20, 0)
    params = {
        'q': f'subject:{display_name}',
        'maxResults': 20,
        'startIndex': start_index,
    }
    api_key = getattr(settings, 'GOOGLE_BOOKS_API_KEY', '') or os.getenv('GOOGLE_BOOKS_API_KEY', '')
    if api_key:
        params['key'] = api_key

    data = _http_get_json(
        GOOGLE_API_ENDPOINT,
        params=params,
        timeout=GOOGLE_TIMEOUT,
        retries=MAX_RETRIES,
    )
    if not data:
        return []
    items = data.get('items', [])
    normalised: List[BookPayload] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        payload = _normalise_google_item(item)
        if payload:
            normalised.append(payload)
    return normalised


def _build_open_library_cover(work: dict) -> str | None:
    cover_edition = work.get('cover_edition_key')
    if cover_edition:
        return f'https://covers.openlibrary.org/b/olid/{cover_edition}-M.jpg'
    cover_id = work.get('cover_id')
    if cover_id:
        return f'https://covers.openlibrary.org/b/id/{cover_id}-M.jpg'
    return None


def fetch_open_library_books(slug: str, page: int) -> List[BookPayload]:
    offset = max((page - 1) * 20, 0)
    params = {'limit': 20, 'offset': offset}
    data = _http_get_json(
        OPEN_LIBRARY_SUBJECT_DETAIL_URL.format(slug=slug),
        params=params,
        timeout=OPEN_LIBRARY_TIMEOUT,
        retries=MAX_RETRIES,
    )
    if not data:
        return []
    works = data.get('works', [])
    normalised: List[BookPayload] = []
    for work in works:
        if not isinstance(work, dict):
            continue
        key = work.get('key')
        if not key:
            continue
        authors = [author.get('name') for author in work.get('authors', []) if isinstance(author, dict) and author.get('name')]
        description = work.get('description')
        if isinstance(description, dict):
            description = description.get('value')
        elif not isinstance(description, str):
            description = None
        subjects = [subject for subject in work.get('subject', []) if isinstance(subject, str)]
        normalised.append(
            BookPayload(
                id=f"ol:{key.strip('/')}",
                title=work.get('title') or 'Untitled',
                authors=authors,
                description=description,
                categories=subjects,
                thumbnail=_build_open_library_cover(work),
                info_url=f"https://openlibrary.org{key}",
                published_year=work.get('first_publish_year'),
                source='openlibrary',
            )
        )
    return normalised


def fetch_books_for_category(slug: str, display_name: str, page: int) -> List[dict]:
    """Fetch normalised book data for the requested category."""
    google_results = fetch_google_books_for_category(display_name, page)
    if google_results:
        return [asdict(payload) for payload in google_results]

    fallback_results = fetch_open_library_books(slug, page)
    return [asdict(payload) for payload in fallback_results]


def get_cached_books(slug: str, page: int) -> dict | None:
    key = BOOKS_CACHE_KEY_TEMPLATE.format(slug=slug, page=page)
    return get_cached_json(key)


def cache_books(slug: str, page: int, payload: dict) -> None:
    key = BOOKS_CACHE_KEY_TEMPLATE.format(slug=slug, page=page)
    set_cached_json(key, payload, timeout=60 * 60)
