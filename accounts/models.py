from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    """Reusable base that tracks creation and update times."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(models.Model):
    """Normalized set of high-level book categories sourced from multiple providers."""

    SOURCE_CANONICAL = 'canonical'
    SOURCE_OPEN_LIBRARY = 'open_library'

    SOURCE_CHOICES = [
        (SOURCE_CANONICAL, 'Canonical'),
        (SOURCE_OPEN_LIBRARY, 'Open Library'),
    ]

    slug = models.SlugField(max_length=120, unique=True, db_index=True, blank=True)
    display_name = models.CharField(max_length=120)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_CANONICAL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_name']

    def __str__(self) -> str:
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.display_name)[:110] or 'category'
            candidate = base_slug
            counter = 1
            while Category.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                suffix = f'-{counter}'
                candidate = f"{base_slug[:110 - len(suffix)]}{suffix}"
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class Genre(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug_candidate = base_slug
            counter = 1
            while Genre.objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
                slug_candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug_candidate
        super().save(*args, **kwargs)


class Author(TimeStampedModel):
    full_name = models.CharField(max_length=150, unique=True)
    biography = models.TextField(blank=True)
    website = models.URLField(blank=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self) -> str:
        return self.full_name


class Book(TimeStampedModel):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    isbn_10 = models.CharField(max_length=10, blank=True)
    isbn_13 = models.CharField(max_length=13, blank=True)
    published_year = models.PositiveSmallIntegerField(blank=True, null=True)
    page_count = models.PositiveIntegerField(blank=True, null=True)
    language = models.CharField(max_length=30, blank=True)
    cover_image = models.URLField(blank=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    ratings_count = models.PositiveIntegerField(default=0)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

    # Sentiment Analysis Fields
    sentiment_score = models.DecimalField(
        max_digits=4, 
        decimal_places=3, 
        blank=True, 
        null=True,
        help_text="Sentiment score from -1.0 (negative) to 1.0 (positive)"
    )
    sentiment_label = models.CharField(
        max_length=20, 
        blank=True,
        choices=[
            ('positive', 'Positive'),
            ('negative', 'Negative'),
            ('neutral', 'Neutral'),
        ],
        help_text="Sentiment classification label"
    )
    sentiment_magnitude = models.DecimalField(
        max_digits=4, 
        decimal_places=3, 
        blank=True, 
        null=True,
        help_text="Sentiment magnitude/strength from 0.0 to 1.0"
    )
    
    # Multi-Mood Analysis Fields (JSON storage for flexibility)
    mood_scores = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dictionary of mood scores (happy, sad, angry, relaxed, etc.)"
    )
    dominant_mood = models.CharField(
        max_length=30,
        blank=True,
        help_text="Primary emotional tone identified in the book"
    )
    emotional_intensity = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="Strength of emotional content (0.0 to 1.0)"
    )
    sentiment_confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="Confidence score for sentiment analysis (0.0 to 1.0)"
    )

    authors = models.ManyToManyField(Author, related_name='books', blank=True)
    genres = models.ManyToManyField(Genre, related_name='books', blank=True)

    class Meta:
        ordering = ['title']

    def __str__(self) -> str:
        return self.title

    def primary_author(self) -> str:
        first_author = self.authors.first()
        return first_author.full_name if first_author else ''

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:250] or 'book'
            slug_candidate = base_slug
            counter = 1
            while Book.objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
                slug_candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug_candidate
        super().save(*args, **kwargs)
