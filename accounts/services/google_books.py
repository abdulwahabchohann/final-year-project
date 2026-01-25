"""Lightweight client for the Google Books API used by the search module."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


class GoogleBooksError(RuntimeError):
    """Raised when the Google Books API returns an error response."""


@dataclass
class GoogleBook:
    identifier: str
    title: str
    subtitle: str
    authors: list[str]
    description: str
    published_year: str
    categories: list[str]
    average_rating: float | None
    ratings_count: int | None
    thumbnail: str
    info_link: str
    page_count: int | None
    language: str
    isbn_10: str
    isbn_13: str
    list_price_amount: float | None
    list_price_currency: str | None


def _normalise_year(published_date: Optional[str]) -> str:
    if not published_date:
        return ''
    return published_date.split('-')[0]


def _clean_thumbnail(link: Optional[str]) -> str:
    if not link:
        return ''
    return link.replace('http://', 'https://')


def _extract_isbns(volume_info: dict) -> tuple[str, str]:
    isbn_10 = ''
    isbn_13 = ''
    for identifier in volume_info.get('industryIdentifiers') or []:
        ident_value = (identifier.get('identifier') or '').replace('-', '').strip()
        if not ident_value:
            continue
        if identifier.get('type') == 'ISBN_10' and not isbn_10:
            isbn_10 = ident_value[:10]
        elif identifier.get('type') == 'ISBN_13' and not isbn_13:
            isbn_13 = ident_value[:13]
    return isbn_10, isbn_13


def search_google_books(
    query: str,
    *,
    max_results: int = 8,
    language: str | None = None,
    start_index: int = 0,
) -> list[GoogleBook]:
    """Return a list of Google Books matches for the provided query."""

    if not query:
        return []

    params = {
        'q': query,
        'maxResults': max(1, min(max_results, 40)),  # API caps at 40 per request
        'printType': 'books',
        'startIndex': max(0, start_index),
    }
    if language:
        params['langRestrict'] = language

    api_key = getattr(settings, 'GOOGLE_BOOKS_API_KEY', '')
    if api_key:
        params['key'] = api_key

    api_url = 'https://www.googleapis.com/books/v1/volumes?' + urlencode(params)
    params_log = dict(params)
    if params_log.get('key'):
        params_log['key'] = 'REDACTED'
    log_url = 'https://www.googleapis.com/books/v1/volumes?' + urlencode(params_log)

    try:
        req = Request(api_url, headers={'Accept': 'application/json'})
        with urlopen(req, timeout=8) as response:
            logger.info(
                "Google Books API request url=%s status=%s",
                log_url,
                getattr(response, 'status', 'unknown'),
            )
            payload = json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError) as exc:
        logger.warning("Google Books API request failed url=%s error=%s", log_url, exc)
        raise GoogleBooksError(str(exc)) from exc

    items = payload.get('items') or []
    logger.info("Google Books API response url=%s items=%s", log_url, len(items))
    results: list[GoogleBook] = []
    for item in items:
        volume = item.get('volumeInfo') or {}
        image_links = volume.get('imageLinks') or {}
        sale_info = item.get('saleInfo') or {}
        list_price = sale_info.get('listPrice') or {}
        isbn_10, isbn_13 = _extract_isbns(volume)

        thumbnail = _clean_thumbnail(
            image_links.get('thumbnail')
            or image_links.get('smallThumbnail')
            or image_links.get('medium')
        )
        if thumbnail:
            logger.info("Google Books API thumbnail url=%s", thumbnail)

        results.append(
            GoogleBook(
                identifier=item.get('id') or '',
                title=(volume.get('title') or '').strip() or 'Untitled',
                subtitle=(volume.get('subtitle') or '').strip(),
                authors=list(volume.get('authors') or []),
                description=(volume.get('description') or '').strip(),
                published_year=_normalise_year(volume.get('publishedDate')),
                categories=list(volume.get('categories') or []),
                average_rating=volume.get('averageRating'),
                ratings_count=volume.get('ratingsCount'),
                thumbnail=thumbnail,
                info_link=(volume.get('infoLink') or item.get('selfLink') or '').strip(),
                page_count=volume.get('pageCount'),
                language=(volume.get('language') or '').strip(),
                isbn_10=isbn_10,
                isbn_13=isbn_13,
                list_price_amount=list_price.get('amount'),
                list_price_currency=list_price.get('currencyCode'),
            )
        )

    return results
