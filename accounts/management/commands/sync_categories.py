from django.core.management.base import BaseCommand

from accounts.services.external import sync_categories


class Command(BaseCommand):
    help = 'Synchronise book categories from the canonical list and Open Library subjects.'

    def handle(self, *args, **options):
        self.stdout.write('Fetching categories from upstream sources...')
        payloads = sync_categories(force_refresh=True)
        self.stdout.write(self.style.SUCCESS(f'Synchronised {len(payloads)} categories.'))
