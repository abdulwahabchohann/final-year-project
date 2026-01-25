"""Generate 5000 books with sentiment analysis data."""

from __future__ import annotations

import random
from decimal import Decimal
from typing import List, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Author, Book, Genre


# Sample book data with varied descriptions for sentiment analysis
BOOK_TITLES = [
    "The Joy of Discovery", "Tragic Endings", "Hope Springs Eternal", "Dark Shadows",
    "Sunshine and Rainbows", "Broken Dreams", "Love and Laughter", "Fear and Loathing",
    "Peaceful Moments", "Chaos Unleashed", "Beautiful Memories", "Lost in Despair",
    "Triumph Over Adversity", "The Depths of Sorrow", "Celebrating Life", "Eternal Darkness",
    "Radiant Happiness", "Silent Suffering", "Inspiring Journeys", "Crushing Defeats",
    "Magical Adventures", "Terrifying Encounters", "Heartwarming Tales", "Chilling Stories",
    "Uplifting Stories", "Depressing Narratives", "Enlightening Paths", "Confusing Times",
    "Serene Landscapes", "Turbulent Waters", "Victorious Battles", "Devastating Losses",
    "Harmonious Melodies", "Discordant Notes", "Brilliant Ideas", "Foolish Mistakes",
    "Glorious Achievements", "Humiliating Failures", "Tender Moments", "Harsh Realities",
    "Optimistic Futures", "Pessimistic Views", "Radiant Smiles", "Tearful Goodbyes",
]

AUTHORS = [
    "John Smith", "Emily Johnson", "Michael Brown", "Sarah Davis", "David Wilson",
    "Jessica Martinez", "Christopher Anderson", "Amanda Taylor", "Matthew Thomas",
    "Lauren Jackson", "Daniel White", "Ashley Harris", "James Martin", "Nicole Thompson",
    "Robert Garcia", "Michelle Lewis", "William Walker", "Stephanie Hall", "Joseph Allen",
    "Rebecca Young", "Charles King", "Laura Wright", "Thomas Lopez", "Kimberly Hill",
    "Mark Scott", "Angela Green", "Steven Adams", "Melissa Baker", "Kevin Nelson",
    "Jennifer Carter", "Ryan Mitchell", "Lisa Perez", "Jason Roberts", "Amy Turner",
]

GENRES = [
    "Fiction", "Non-Fiction", "Romance", "Mystery", "Thriller", "Science Fiction",
    "Fantasy", "Horror", "Biography", "History", "Self-Help", "Philosophy",
    "Poetry", "Drama", "Comedy", "Adventure", "Crime", "Western", "Young Adult",
    "Children's Literature", "Business", "Technology", "Health", "Travel",
]

# Descriptions with varying sentiment
POSITIVE_DESCRIPTIONS = [
    "An inspiring journey of hope and triumph that will lift your spirits and fill your heart with joy.",
    "A heartwarming tale of love, friendship, and the power of human connection that brings tears of happiness.",
    "This uplifting story celebrates the beauty of life and the resilience of the human spirit.",
    "A delightful narrative filled with laughter, love, and moments of pure happiness that will brighten your day.",
    "An empowering book that inspires readers to pursue their dreams and find success in their endeavors.",
    "A beautiful story of redemption and second chances that restores faith in humanity.",
    "This enchanting tale weaves together themes of love, adventure, and the magic of everyday moments.",
    "A celebration of life's simple pleasures and the joy found in unexpected places.",
]

NEGATIVE_DESCRIPTIONS = [
    "A dark and haunting tale of loss, despair, and the crushing weight of human suffering.",
    "This tragic story explores the depths of human misery and the devastating effects of betrayal.",
    "A chilling narrative that delves into the darkest corners of the human psyche.",
    "An unsettling account of fear, isolation, and the terrifying unknown that lurks in shadows.",
    "This disturbing story reveals the harsh realities of life and the pain of unfulfilled dreams.",
    "A somber reflection on loss, grief, and the emptiness that follows tragedy.",
    "A bleak portrayal of a world without hope, where darkness consumes all light.",
    "This harrowing tale exposes the cruel nature of fate and the suffering it brings.",
]

NEUTRAL_DESCRIPTIONS = [
    "A comprehensive exploration of the subject matter, presenting facts and perspectives in a balanced manner.",
    "This detailed account provides an objective analysis of events and their historical context.",
    "An informative guide that presents information clearly and without bias.",
    "A straightforward narrative that documents events as they occurred, without emotional embellishment.",
    "This analytical work examines various viewpoints and presents them in an even-handed way.",
    "A factual presentation of data and observations, allowing readers to draw their own conclusions.",
    "An educational resource that provides information in a clear, objective format.",
    "This reference work offers comprehensive coverage of the topic with balanced perspectives.",
]


def calculate_sentiment(description: str) -> Tuple[Decimal, str, Decimal]:
    """
    Calculate sentiment score, label, and magnitude based on description.
    Returns: (score, label, magnitude)
    """
    description_lower = description.lower()
    
    # Positive keywords
    positive_words = ['joy', 'happy', 'love', 'beautiful', 'inspiring', 'uplifting', 
                     'triumph', 'hope', 'celebrating', 'radiant', 'heartwarming',
                     'delightful', 'empowering', 'enchanting', 'magic', 'success']
    
    # Negative keywords
    negative_words = ['dark', 'tragic', 'despair', 'sorrow', 'suffering', 'loss',
                     'fear', 'chaos', 'crushing', 'terrifying', 'chilling', 'depressing',
                     'devastating', 'harsh', 'pessimistic', 'tearful', 'bleak', 'harrowing']
    
    positive_count = sum(1 for word in positive_words if word in description_lower)
    negative_count = sum(1 for word in negative_words if word in description_lower)
    
    # Calculate sentiment score (-1.0 to 1.0)
    total_words = positive_count + negative_count
    if total_words == 0:
        score = Decimal('0.000')
        label = 'neutral'
        magnitude = Decimal('0.000')
    else:
        score = Decimal(str((positive_count - negative_count) / max(total_words, 1)))
        # Normalize to -1.0 to 1.0 range
        if score > Decimal('1.0'):
            score = Decimal('1.0')
        elif score < Decimal('-1.0'):
            score = Decimal('-1.0')
        
        # Determine label
        if score > Decimal('0.2'):
            label = 'positive'
        elif score < Decimal('-0.2'):
            label = 'negative'
        else:
            label = 'neutral'
        
        # Calculate magnitude (0.0 to 1.0) - how strong the sentiment is
        magnitude = abs(score)
    
    return score, label, magnitude


class Command(BaseCommand):
    help = "Generate 5000 books with sentiment analysis data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5000,
            help="Number of books to generate (default: 5000).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing books before generating new ones.",
        )

    def handle(self, *args, **options):
        count = max(1, options["count"])
        clear_existing = options.get("clear", False)

        if clear_existing:
            self.stdout.write("Clearing existing books...")
            Book.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Existing books cleared."))

        self.stdout.write(f"Generating {count:,} books with sentiment analysis data...")

        # Get or create authors and genres
        author_objs = self._get_or_create_authors()
        genre_objs = self._get_or_create_genres()

        created = 0
        batch_size = 100

        # Combine all descriptions
        all_descriptions = POSITIVE_DESCRIPTIONS + NEGATIVE_DESCRIPTIONS + NEUTRAL_DESCRIPTIONS

        for i in range(count):
            # Select title and description
            title_base = random.choice(BOOK_TITLES)
            title = f"{title_base} {i + 1}" if i < len(BOOK_TITLES) else f"{title_base} - Volume {i // len(BOOK_TITLES) + 1}"
            description = random.choice(all_descriptions)
            
            # Calculate sentiment
            sentiment_score, sentiment_label, sentiment_magnitude = calculate_sentiment(description)
            
            # Generate book data
            book_data = {
                'title': title,
                'subtitle': f"Book {i + 1}" if random.random() > 0.7 else '',
                'description': description,
                'isbn_10': self._generate_isbn_10(),
                'isbn_13': self._generate_isbn_13(),
                'published_year': random.randint(1950, 2024),
                'page_count': random.randint(100, 800),
                'language': random.choice(['en', 'es', 'fr', 'de', 'it']),
                'cover_image': f"https://example.com/covers/{i + 1}.jpg",
                'average_rating': Decimal(str(round(random.uniform(2.5, 5.0), 2))),
                'ratings_count': random.randint(0, 10000),
                'price': Decimal(str(round(random.uniform(5.99, 29.99), 2))),
                'sentiment_score': sentiment_score,
                'sentiment_label': sentiment_label,
                'sentiment_magnitude': sentiment_magnitude,
            }

            # Create book
            with transaction.atomic():
                book = Book.objects.create(**book_data)
                
                # Assign random authors (1-3 authors)
                num_authors = random.randint(1, 3)
                book.authors.set(random.sample(author_objs, min(num_authors, len(author_objs))))
                
                # Assign random genres (1-2 genres)
                num_genres = random.randint(1, 2)
                book.genres.set(random.sample(genre_objs, min(num_genres, len(genre_objs))))

            created += 1

            if created % batch_size == 0:
                self.stdout.write(
                    f"Generated {created:,} books "
                    f"(Positive: {Book.objects.filter(sentiment_label='positive').count()}, "
                    f"Negative: {Book.objects.filter(sentiment_label='negative').count()}, "
                    f"Neutral: {Book.objects.filter(sentiment_label='neutral').count()})"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully generated {created:,} books with sentiment analysis data!\n"
                f"Sentiment Distribution:\n"
                f"  - Positive: {Book.objects.filter(sentiment_label='positive').count()}\n"
                f"  - Negative: {Book.objects.filter(sentiment_label='negative').count()}\n"
                f"  - Neutral: {Book.objects.filter(sentiment_label='neutral').count()}"
            )
        )

    def _get_or_create_authors(self) -> List[Author]:
        """Get or create author objects."""
        authors = []
        for name in AUTHORS:
            author, _ = Author.objects.get_or_create(full_name=name)
            authors.append(author)
        return authors

    def _get_or_create_genres(self) -> List[Genre]:
        """Get or create genre objects."""
        genres = []
        for name in GENRES:
            genre, _ = Genre.objects.get_or_create(name=name)
            genres.append(genre)
        return genres

    def _generate_isbn_10(self) -> str:
        """Generate a random ISBN-10."""
        isbn = ''.join([str(random.randint(0, 9)) for _ in range(9)])
        # Calculate check digit
        check = sum(int(isbn[i]) * (10 - i) for i in range(9)) % 11
        check_digit = 'X' if check == 10 else str(check)
        return isbn + check_digit

    def _generate_isbn_13(self) -> str:
        """Generate a random ISBN-13."""
        isbn = '978' + ''.join([str(random.randint(0, 9)) for _ in range(9)])
        # Calculate check digit
        check = sum(int(isbn[i]) * (3 if i % 2 else 1) for i in range(12)) % 10
        check_digit = str((10 - check) % 10)
        return isbn + check_digit

