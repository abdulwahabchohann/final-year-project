"""
Management command to analyze book sentiments using advanced NLP techniques.

This command processes all books in the database and updates them with:
- Multi-dimensional mood scores
- Dominant mood
- Emotional intensity
- Sentiment confidence scores

Usage:
    python manage.py analyze_book_sentiments
    python manage.py analyze_book_sentiments --batch-size 100
    python manage.py analyze_book_sentiments --book-id 123
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Book
from accounts.services.sentiment_analysis import get_sentiment_analyzer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Analyze book sentiments using advanced NLP techniques"

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of books to process in each batch (default: 50)',
        )
        parser.add_argument(
            '--book-id',
            type=int,
            help='Analyze a specific book by ID',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-analyze books that already have sentiment data',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit the number of books to analyze',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        book_id = options.get('book_id')
        force = options.get('force', False)
        limit = options.get('limit')

        self.stdout.write("Initializing sentiment analyzer...")
        analyzer = get_sentiment_analyzer()
        
        if analyzer.embedding_model is None:
            self.stdout.write(
                self.style.WARNING(
                    "Warning: Transformer models not available. "
                    "Falling back to keyword-based analysis. "
                    "Install transformers and sentence-transformers for better accuracy."
                )
            )

        # Get books to analyze
        if book_id:
            books = Book.objects.filter(id=book_id)
            if not books.exists():
                self.stdout.write(self.style.ERROR(f"Book with ID {book_id} not found."))
                return
        else:
            if force:
                books = Book.objects.filter(description__isnull=False).exclude(description='')
            else:
                books = Book.objects.filter(
                    description__isnull=False
                ).exclude(
                    description=''
                ).filter(
                    mood_scores__isnull=True
                ) | Book.objects.filter(
                    description__isnull=False
                ).exclude(
                    description=''
                ).filter(mood_scores={})
            
            total_books = books.count()
            self.stdout.write(f"Found {total_books} books to analyze.")

        if not books.exists():
            self.stdout.write(self.style.SUCCESS("No books to analyze."))
            return

        processed = 0
        errors = 0

        # Process in batches
        count_to_process = books.count()
        if limit:
            count_to_process = min(count_to_process, limit)
            
        for i in range(0, count_to_process, batch_size):
            batch = books[i:i + batch_size]
            
            for book in batch:
                try:
                    self._analyze_book(book, analyzer)
                    processed += 1
                    
                    if processed % 10 == 0:
                        self.stdout.write(f"Processed {processed} books...")
                        
                except Exception as e:
                    errors += 1
                    logger.error(f"Error analyzing book {book.id} ({book.title}): {e}", exc_info=True)
                    self.stdout.write(
                        self.style.ERROR(f"Error analyzing book {book.id}: {str(e)}")
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nAnalysis complete!\n"
                f"  Processed: {processed}\n"
                f"  Errors: {errors}"
            )
        )

    def _analyze_book(self, book: Book, analyzer):
        """Analyze a single book and update its sentiment fields."""
        # Get all text content
        text_parts = []
        if book.title:
            text_parts.append(book.title)
        if book.subtitle:
            text_parts.append(book.subtitle)
        if book.description:
            text_parts.append(book.description)
        
        if not text_parts:
            return
        
        text = ' '.join(text_parts)
        
        # Perform analysis
        analysis = analyzer.analyze_text(text)
        
        # Update book fields
        with transaction.atomic():
            book.mood_scores = analysis.get('moods', {})
            book.dominant_mood = analysis.get('dominant_mood', 'neutral')
            book.emotional_intensity = Decimal(str(analysis.get('emotional_intensity', 0.0)))
            book.sentiment_confidence = Decimal(str(analysis.get('confidence', 0.0)))
            
            # Also update legacy sentiment fields for backward compatibility
            sentiment_score = analysis.get('sentiment_score', 0.0)
            sentiment_label = analysis.get('sentiment_label', 'neutral')
            sentiment_magnitude = analysis.get('emotional_intensity', 0.0)
            
            book.sentiment_score = Decimal(str(sentiment_score))
            book.sentiment_label = sentiment_label
            book.sentiment_magnitude = Decimal(str(sentiment_magnitude))
            
            book.save(update_fields=[
                'mood_scores',
                'dominant_mood',
                'emotional_intensity',
                'sentiment_confidence',
                'sentiment_score',
                'sentiment_label',
                'sentiment_magnitude',
            ])

