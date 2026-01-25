from django.core.management.base import BaseCommand
from accounts.views import _get_trending_books


class Command(BaseCommand):
    help = "Print top trending books and their cover_image URLs"

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=10, help='Number of trending books to list')

    def handle(self, *args, **options):
        limit = options['limit']
        books = _get_trending_books(limit=limit)
        if not books:
            self.stdout.write('No trending books found')
            return
        for b in books:
            self.stdout.write(f"title: {b.title}\n  slug: {b.slug}\n  cover_image: {b.cover_image}\n")
