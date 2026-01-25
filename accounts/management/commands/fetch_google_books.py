"""Fetch a large catalogue of books from Google Books and store locally."""

from __future__ import annotations
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from accounts.models import Author, Book, Genre
from accounts.services.google_books import GoogleBooksError, search_google_books


DEFAULT_QUERIES = [
    'fiction novels',
    'mystery thriller',
    'fantasy adventure',
    'science fiction',
    'historical fiction',
    'romance bestsellers',
    'self help personal growth',
    'business leadership',
    'biography memoir',
    'history world events',
    'technology innovation',
    'psychology science',
]


class Command(BaseCommand):
    help = (
        "Call the Google Books API to pull a broader selection of titles into the local "
        "catalogue. Requires GOOGLE_BOOKS_API_KEY in settings/.env."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--queries',
            nargs='+',
            default=DEFAULT_QUERIES,
            help='List of search phrases to fetch (default covers multiple genres).',
        )
        parser.add_argument(
            '--per-query',
            type=int,
            default=40,
            help='Maximum results to request per query batch (<=40).',
        )
        parser.add_argument(
            '--max-books',
            type=int,
            default=500,
            help='Stop after importing approximately this many unique books.',
        )
        parser.add_argument(
            '--language',
            default='en',
            help='Restrict Google Books results to an ISO language code (e.g. en).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Fetch data but do not write to the database.',
        )

    def handle(self, *args, **options):
        if not getattr(settings, 'GOOGLE_BOOKS_API_KEY', ''):
            self.stdout.write(
                self.style.WARNING(
                    'GOOGLE_BOOKS_API_KEY is not set. Requests may be throttled or fail. '
                    'Set it in your .env for stable imports.'
                )
            )

        queries: list[str] = options['queries']
        per_query: int = max(1, min(options['per_query'], 40))
        language: str | None = options.get('language') or None
        dry_run: bool = options['dry_run']
        max_books: int = max(1, options['max_books'])

        created = 0
        updated = 0
        skipped_duplicates = 0
        seen_keys: set[str] = set()

        with transaction.atomic():
            for query in queries:
                if created + updated >= max_books:
                    break

                start_index = 0
                while created + updated < max_books:
                    remaining = max_books - (created + updated)
                    batch_size = min(per_query, remaining)

                    try:
                        google_books = search_google_books(
                            query,
                            max_results=batch_size,
                            language=language,
                            start_index=start_index,
                        )
                    except GoogleBooksError as exc:
                        self.stdout.write(self.style.ERROR(f"API error for '{query}': {exc}"))
                        break

                    if not google_books:
                        break

                    start_index += len(google_books)

                    for google_book in google_books:
                        unique_key = google_book.isbn_13 or google_book.isbn_10 or google_book.identifier
                        if not unique_key:
                            # Fallback to title to avoid duplicates in the same batch
                            unique_key = google_book.title.lower()

                        if unique_key in seen_keys:
                            skipped_duplicates += 1
                            continue

                        seen_keys.add(unique_key)

                        if dry_run:
                            continue

                        book_obj, created_flag = self._create_or_update_book(google_book)
                        if created_flag:
                            created += 1
                        else:
                            updated += 1

                        if created + updated >= max_books:
                            break

            if dry_run:
                # Rollback the atomic block after reporting counts
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete: created {created}, updated {updated}, skipped duplicates {skipped_duplicates}."
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run was enabled, so no database changes were saved.'))

    def _create_or_update_book(self, google_book):
        """Create or update a Book record from a GoogleBook payload."""

        # Find existing book using ISBNs first
        lookup = Q()
        if google_book.isbn_13:
            lookup |= Q(isbn_13__iexact=google_book.isbn_13)
        if google_book.isbn_10:
            lookup |= Q(isbn_10__iexact=google_book.isbn_10)
        if not lookup:
            lookup = Q(title__iexact=google_book.title)

        book_obj = Book.objects.filter(lookup).first()
        created_flag = False

        if not book_obj:
            book_obj = Book(title=google_book.title)
            created_flag = True

        if google_book.subtitle:
            book_obj.subtitle = google_book.subtitle
        if google_book.description:
            book_obj.description = google_book.description
        book_obj.isbn_10 = google_book.isbn_10
        book_obj.isbn_13 = google_book.isbn_13
        book_obj.published_year = int(google_book.published_year) if google_book.published_year.isdigit() else None
        page_count = google_book.page_count
        if page_count not in (None, ''):
            try:
                book_obj.page_count = int(page_count)
            except (TypeError, ValueError):
                pass
        book_obj.language = google_book.language or book_obj.language
        book_obj.cover_image = google_book.thumbnail or book_obj.cover_image
        if google_book.average_rating is not None:
            book_obj.average_rating = google_book.average_rating
        if google_book.ratings_count is not None:
            book_obj.ratings_count = google_book.ratings_count
        new_price = self._parse_price(google_book)
        if new_price is not None:
            book_obj.price = new_price

        book_obj.save()

        author_objs = []
        for author_name in google_book.authors or ['Unknown Author']:
            author_obj, _ = Author.objects.get_or_create(full_name=author_name.strip() or 'Unknown Author')
            author_objs.append(author_obj)
        book_obj.authors.set(author_objs)

        genre_objs = []
        for category_name in google_book.categories or ['General']:
            genre_obj, _ = Genre.objects.get_or_create(name=category_name.strip() or 'General')
            genre_objs.append(genre_obj)
        book_obj.genres.set(genre_objs)

        return book_obj, created_flag

    @staticmethod
    def _parse_price(google_book) -> Decimal | None:
        amount = google_book.list_price_amount
        currency = (google_book.list_price_currency or '').upper()
        if amount is None or (currency and currency != 'USD'):
            return None

        try:
            # Google may return floats; convert safely to Decimal
            return Decimal(str(amount)).quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError):
            return None
