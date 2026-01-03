import json
import logging
import re
import secrets
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import DecimalField, IntegerField, Q, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.cache import cache
from django.utils.text import slugify
from django.urls import reverse

from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import LoginForm, SignupForm
from .models import Author, Book, Category, Genre
from .serializers import BookSerializer, CategorySerializer
from .services.external import (
    cache_books,
    fetch_books_for_category,
    get_cached_books,
    get_cached_category_list,
)
from .services.google_books import GoogleBooksError, search_google_books

logger = logging.getLogger(__name__)
SLUG_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
TRENDING_SEED_CACHE_KEY = 'accounts:trending:seeded:v1'


def _book_identity_key(book: Book) -> str:
    """Return a stable identity token used to deduplicate very similar books."""
    if book.isbn_13:
        return book.isbn_13.strip()
    if book.isbn_10:
        return book.isbn_10.strip()
    # Fall back to a normalized title when ISBN data is missing.
    return ' '.join((book.title or '').split()).casefold()


def _deduplicate_books(queryset, limit: int | None = None) -> list[Book]:
    """Return books without duplicates using the identity key helper."""
    unique_books: list[Book] = []
    seen_ids: set[str] = set()
    for book in queryset:
        identity = _book_identity_key(book)
        if identity in seen_ids:
            continue
        seen_ids.add(identity)
        unique_books.append(book)
        if limit and len(unique_books) >= limit:
            break
    return unique_books if limit is None else unique_books[:limit]


def _get_trending_books(limit: int | None = 12) -> list[Book]:
    """Return a list of popular books ordered by rating and review volume."""
    queryset = (
        Book.objects.annotate(
            popularity_rating=Coalesce(
                'average_rating',
                Value(0),
                output_field=DecimalField(max_digits=3, decimal_places=2),
            ),
            popularity_count=Coalesce(
                'ratings_count',
                Value(0),
                output_field=IntegerField(),
            ),
        )
        .prefetch_related('authors', 'genres')
        .order_by('-popularity_rating', '-popularity_count', '-updated_at', 'title')
    )

    return _deduplicate_books(queryset, limit=limit)


def _ingest_external_trending(limit: int = 40) -> int:
    """
    Fetch trending-ish books from external APIs (via category feed) and store locally.

    We pull the "Fiction" subject to keep results broad, and only run once per cache window
    to avoid slow page loads.
    """
    if cache.get(TRENDING_SEED_CACHE_KEY):
        return 0

    created = 0
    try:
        payloads = fetch_books_for_category('fiction', 'Fiction', page=1) or []
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to fetch external trending feed: %s", exc)
        payloads = []

    for item in payloads:
        if created >= limit:
            break
        title = (item.get('title') or '').strip()
        if not title:
            continue

        base_slug = slugify(title)[:280] or 'book'
        slug_candidate = base_slug
        counter = 1
        while Book.objects.filter(slug=slug_candidate).exists():
            suffix = f'-{counter}'
            slug_candidate = f"{base_slug[:280 - len(suffix)]}{suffix}"
            counter += 1

        book = Book.objects.create(
            title=title,
            subtitle=item.get('subtitle') or '',
            description=item.get('description') or '',
            isbn_10='',
            isbn_13='',
            published_year=item.get('published_year'),
            page_count=None,
            language='',
            cover_image=item.get('thumbnail') or '',
            average_rating=Decimal(str(item.get('average_rating'))) if item.get('average_rating') is not None else Decimal('4.2'),
            ratings_count=item.get('ratings_count') or 120,
            slug=slug_candidate,
        )

        for name in item.get('authors') or []:
            clean = name.strip()
            if not clean:
                continue
            author, _ = Author.objects.get_or_create(full_name=clean[:150])
            book.authors.add(author)

        genres = item.get('categories') or ['Fiction']
        for genre_name in genres:
            clean = (genre_name or '').strip()
            if not clean:
                continue
            genre, _ = Genre.objects.get_or_create(name=clean)
            book.genres.add(genre)

        created += 1

    if created:
        cache.set(TRENDING_SEED_CACHE_KEY, True, timeout=60 * 60 * 6)  # 6 hours
    return created


def _normalize_card(book: Book) -> dict:
    authors = [author.full_name for author in book.authors.all()]
    genres = [genre.name for genre in book.genres.all()[:3]]
    return {
        'title': book.title,
        'subtitle': book.subtitle,
        'authors_display': ', '.join(authors) if authors else 'Author unknown',
        'description': book.description,
        'cover_image': book.cover_image,
        'published_year': book.published_year,
        'average_rating': book.average_rating,
        'ratings_count': book.ratings_count,
        'tags': genres,
        'url': reverse('book_detail', args=[book.slug]),
        'source': 'local',
    }


def _normalize_external_card(payload: dict) -> dict:
    authors = payload.get('authors') or []
    categories = payload.get('categories') or []
    return {
        'title': payload.get('title') or 'Untitled',
        'subtitle': payload.get('subtitle') or '',
        'authors_display': ', '.join(authors) if authors else 'Author unknown',
        'description': payload.get('description') or '',
        'cover_image': payload.get('thumbnail') or '',
        'published_year': payload.get('published_year'),
        'average_rating': payload.get('average_rating'),
        'ratings_count': payload.get('ratings_count'),
        'tags': categories[:3],
        'url': payload.get('info_url') or '',
        'source': 'external',
    }


def _get_external_trending(limit: int) -> list[dict]:
    try:
        payloads = fetch_books_for_category('fiction', 'Fiction', page=1) or []
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to fetch external trending feed: %s", exc)
        return []

    cards: list[dict] = []
    for item in payloads:
        cards.append(_normalize_external_card(item))
        if len(cards) >= limit:
            break
    return cards


def home(request):
    trending_cards = _get_external_trending(limit=8)
    if not trending_cards:
        # fallback to local DB and try to seed if empty
        local_books = _get_trending_books(limit=8)
        if not local_books and _ingest_external_trending(limit=16):
            local_books = _get_trending_books(limit=8)
        trending_cards = [_normalize_card(book) for book in local_books]

    genre_palette = [
        ('#5a7dff', '#1f3bb3'),
        ('#637fff', '#2240bd'),
        ('#6d88ff', '#2545c7'),
        ('#7791ff', '#294bce'),
        ('#4f6bff', '#1d369f'),
        ('#5873ff', '#203ba8'),
        ('#6180ff', '#2440b2'),
        ('#6a89ff', '#2646bc'),
        ('#7392ff', '#2a4cc6'),
    ]

    desired_home_categories = [
        ('self-improvement', 'Self-Improvement'),
        ('business', 'Business'),
        ('technology', 'Technology'),
        ('psychology', 'Psychology'),
        ('data-science-ai', 'Data Science & AI'),
        ('religion-spirituality', 'Religion & Spirituality'),
        ('philosophy-critical-thinking', 'Philosophy & Critical Thinking'),
        ('health-wellness', 'Health & Wellness'),
    ]

    category_payload = get_cached_category_list()
    payload_by_slug = {item['slug']: item for item in category_payload}
    home_categories = []
    for index, (slug, display_name) in enumerate(desired_home_categories):
        gradient_start, gradient_end = genre_palette[index % len(genre_palette)]
        payload = payload_by_slug.get(slug, {})
        home_categories.append(
            {
                'name': display_name,
                'slug': slug,
                'book_count': payload.get('book_count_estimate'),
                'gradient': f'linear-gradient(140deg, {gradient_start}, {gradient_end})',
            }
        )

    context = {
        'trending_books': trending_cards,
        'home_categories': home_categories,
    }
    return render(request, 'index.html', context)


def trending(request):
    trending_cards = _get_external_trending(limit=48)
    if not trending_cards:
        local_books = _get_trending_books(limit=48)
        if not local_books and _ingest_external_trending(limit=60):
            local_books = _get_trending_books(limit=48)
        trending_cards = [_normalize_card(book) for book in local_books]

    context = {
        'trending_books': trending_cards,
        'total_trending': len(trending_cards),
    }
    return render(request, 'trend.html', context)


def categories(request):
    category_payload = get_cached_category_list()
    initial_slug = request.GET.get('slug', '').strip().lower()
    if initial_slug and not SLUG_PATTERN.match(initial_slug):
        initial_slug = ''

    context = {
        'initial_categories_json': json.dumps(category_payload),
        'initial_slug': initial_slug,
    }
    return render(request, 'categories.html', context)


def category_detail(request, slug):
    genre = get_object_or_404(Genre, slug=slug)

    books = (
        Book.objects.filter(genres=genre)
        .prefetch_related('authors', 'genres')
        .order_by('-average_rating', '-ratings_count', 'title')
    )
    books = list(books)

    context = {
        'genre': genre,
        'books': books,
        'book_total': len(books),
    }
    return render(request, 'category_detail.html', context)


class CategoryPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


REFRESH_PARAM_VALUES = {'1', 'true', 'yes'}


class CategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        refresh_flag = str(request.query_params.get('refresh', '')).strip().lower()
        force_refresh = refresh_flag in REFRESH_PARAM_VALUES
        categories = get_cached_category_list(force_refresh=force_refresh)
        paginator = CategoryPagination()
        page = paginator.paginate_queryset(categories, request)
        serializer = CategorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class CategoryBooksView(APIView):
    permission_classes = [AllowAny]

    def _serialize_local_books(self, slug: str) -> list[dict]:
        genre = Genre.objects.filter(slug=slug).first()
        if not genre:
            normalized = slug.replace('-', ' ')
            genre = (
                Genre.objects.filter(name__iexact=normalized).first()
                or Genre.objects.filter(name__icontains=normalized).first()
            )
        if not genre:
            return []

        books = (
            Book.objects.filter(genres=genre)
            .prefetch_related('authors')
            .order_by('-average_rating', '-ratings_count', 'title')[:20]
        )

        results: list[dict] = []
        for book in books:
            results.append(
                {
                    'id': f'local:{book.pk}',
                    'title': book.title,
                    'authors': [author.full_name for author in book.authors.all()],
                    'description': book.description or '',
                    'categories': [genre.name],
                    'thumbnail': book.cover_image or '',
                    'info_url': '',
                    'published_year': book.published_year,
                    'source': 'local',
                }
            )
        return results

    def _merge_remote_and_local(self, remote_items: list[dict], local_items: list[dict]) -> list[dict]:
        combined: list[dict] = []
        seen: set[str] = set()

        def make_key(item: dict) -> str:
            if item.get('id'):
                return str(item['id']).lower()
            title = (item.get('title') or '').strip().lower()
            authors = ','.join(sorted((item.get('authors') or [])))
            return f"{title}|{authors}"

        for source in (remote_items or [], local_items or []):
            for item in source:
                key = make_key(item)
                if not key or key in seen:
                    continue
                seen.add(key)
                combined.append(item)
        return combined

    def get(self, request, slug: str):
        if not SLUG_PATTERN.match(slug):
            raise ValidationError({'slug': 'Invalid category slug.'})

        page_param = request.query_params.get('page', '1')
        try:
            page_number = int(page_param)
        except (TypeError, ValueError):
            raise ValidationError({'page': 'Page must be a positive integer.'})
        if page_number < 1:
            raise ValidationError({'page': 'Page must be a positive integer.'})

        category = Category.objects.filter(slug=slug).first()
        category_display_name = category.display_name if category else ''
        if not category:
            category_payload = get_cached_category_list()
            category_meta = next((item for item in category_payload if item.get('slug') == slug), None)
            if not category_meta:
                raise ValidationError({'slug': 'Unknown category slug.'})
            defaults = {
                'display_name': category_meta.get('display_name') or slug.replace('-', ' ').title(),
                'source': category_meta.get('source') or Category.SOURCE_CANONICAL,
            }
            category, created = Category.objects.get_or_create(slug=slug, defaults=defaults)
            if not created:
                updated = False
                if defaults['display_name'] and category.display_name != defaults['display_name']:
                    category.display_name = defaults['display_name']
                    updated = True
                if defaults['source'] and category.source != defaults['source']:
                    category.source = defaults['source']
                    updated = True
                if updated:
                    category.save(update_fields=['display_name', 'source'])
            category_display_name = category.display_name
        elif not category_display_name:
            category_display_name = slug.replace('-', ' ').title()
        refresh_flag = str(request.query_params.get('refresh', '')).strip().lower()
        force_refresh = refresh_flag in REFRESH_PARAM_VALUES
        cached = None if force_refresh else get_cached_books(slug, page_number)
        if cached and not cached.get('items'):
            cached = None

        if cached is None:
            items = fetch_books_for_category(slug, category_display_name, page_number)
            payload = {'page': page_number, 'items': items}
            if items:
                cache_books(slug, page_number, payload)
        else:
            payload = cached

        remote_items = payload.get('items', [])
        local_items: list[dict] = []
        if page_number == 1:
            local_items = self._serialize_local_books(slug)

        merged_items = self._merge_remote_and_local(remote_items, local_items)

        if not merged_items:
            merged_items = local_items
            payload = {'page': 1, 'items': merged_items}

        serializer = BookSerializer(merged_items, many=True)
        return Response({'page': payload.get('page', page_number), 'items': serializer.data})


def book_detail(request, slug):
    book = get_object_or_404(
        Book.objects.prefetch_related('authors', 'genres'),
        slug=slug,
    )

    related_books = list(
        Book.objects.filter(genres__in=book.genres.all())
        .exclude(pk=book.pk)
        .order_by('-average_rating', '-ratings_count')
        .prefetch_related('authors')
        .distinct()[:6]
    )

    context = {
        'book': book,
        'related_books': related_books,
    }
    return render(request, 'book_detail.html', context)


class MoodRecommendationsAPIView(APIView):
    """
    API endpoint for mood-based book recommendations.
    
    POST /api/recommendations/mood/
    Body: {
        "mood": "I feel sad and anxious",
        "improve_mood": true,
        "limit": 5
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Get book recommendations based on user mood."""
        user_mood = (request.data.get('mood', '') or '').strip()
        improve_mood = request.data.get('improve_mood', True)
        limit = min(int(request.data.get('limit', 5)), 20)  # Max 20 recommendations
        
        if not user_mood:
            return Response(
                {'error': 'Mood description is required'},
                status=400
            )
        
        try:
            from accounts.services.mood_recommender import get_mood_recommender
            recommender = get_mood_recommender()
            recommendations = recommender.recommend_books(
                user_mood=user_mood,
                limit=limit,
                improve_mood=improve_mood,
                min_confidence=0.3
            )
            
            return Response({
                'mood': user_mood,
                'improve_mood': improve_mood,
                'count': len(recommendations),
                'recommendations': recommendations
            })
        except ImportError as e:
            logger.error(f"Mood recommendations feature not available: {e}", exc_info=True)
            return Response(
                {'error': 'Mood-based recommendations are currently unavailable. This feature requires additional setup.'},
                status=503
            )
        except Exception as e:
            logger.error(f"Error in MoodRecommendationsAPIView: {e}", exc_info=True)
            return Response(
                {'error': 'Unable to generate recommendations at this time. Please try again later.'},
                status=500
            )


def recommendations(request):
    """
    Mood-based book recommendations view.
    Supports both GET (form) and POST (mood input) requests.
    """
    recommendations_list = []
    user_mood = ''
    error_message = ''
    
    if request.method == 'POST':
        user_mood = (request.POST.get('mood', '') or '').strip()
        improve_mood = request.POST.get('improve_mood', 'on') == 'on'  # Default to True
        
        if user_mood:
            try:
                from accounts.services.mood_recommender import get_mood_recommender
                recommender = get_mood_recommender()
                recommendations_list = recommender.recommend_books(
                    user_mood=user_mood,
                    limit=5,
                    improve_mood=improve_mood,
                    min_confidence=0.3
                )
            except ImportError as e:
                error_message = (
                    'Mood-based recommendations are currently unavailable. '
                    'This feature requires additional packages to be installed. '
                    'Please contact the administrator or install: numpy, transformers, sentence-transformers, torch'
                )
                logger.error(f"Mood recommendations feature not available: {e}", exc_info=True)
            except Exception as e:
                error_message = f'Unable to generate recommendations: {str(e)}. Please try again later.'
                logger.error(f"Error in recommendations view: {e}", exc_info=True)
        else:
            error_message = "Please describe your current mood."
    
    context = {
        'recommendations': recommendations_list,
        'user_mood': user_mood,
        'error_message': error_message,
    }
    return render(request, 'recommendations.html', context)


@login_required(login_url='login')
def personalize(request):
    # Next step: handle POST to save user preferences
    return render(request, 'personalize.html')


def search_books(request):
    query = (request.GET.get('q') or '').strip()
    genre_slug = (request.GET.get('genre') or '').strip()

    results = Book.objects.none()
    total_results = 0

    base_queryset = Book.objects.all().prefetch_related('authors', 'genres')

    if query:
        text_filters = (
            Q(title__icontains=query)
            | Q(subtitle__icontains=query)
            | Q(description__icontains=query)
            | Q(authors__full_name__icontains=query)
            | Q(isbn_10__icontains=query)
            | Q(isbn_13__icontains=query)
        )
        base_queryset = base_queryset.filter(text_filters)

    if genre_slug:
        base_queryset = base_queryset.filter(genres__slug=genre_slug)

    if query or genre_slug:
        results = base_queryset.distinct()
        total_results = results.count()

    genres = list(Genre.objects.order_by('name'))
    active_genre_obj = None
    if genre_slug:
        active_genre_obj = next((genre for genre in genres if genre.slug == genre_slug), None)
    popular_books = []
    external_books = []
    external_error = ''

    if query:
        try:
            external_books = search_google_books(query, max_results=8, language='en')
        except GoogleBooksError as exc:
            external_error = str(exc)

    if not (query or genre_slug):
        popular_books = list(
            Book.objects.order_by('-average_rating', '-ratings_count')
            .prefetch_related('authors', 'genres')[:8]
        )

    show_empty_state = total_results == 0 and bool(query or active_genre_obj) and not external_books

    context = {
        'query': query,
        'active_genre': genre_slug,
        'genres': genres,
        'results': results,
        'total_results': total_results,
        'popular_books': popular_books,
        'active_genre_obj': active_genre_obj,
        'external_books': external_books,
        'external_error': external_error,
        'show_empty_state': show_empty_state,
    }
    return render(request, 'search_results.html', context)


# -------------------- AUTH VIEWS --------------------

def login_view(request):
    google_enabled = bool(
        getattr(settings, 'GOOGLE_OAUTH', {})
        and settings.GOOGLE_OAUTH.get('CLIENT_ID')
        and settings.GOOGLE_OAUTH.get('REDIRECT_URI')
    )
    if request.user.is_authenticated:
        return redirect('home')

    next_url = request.GET.get('next') or request.POST.get('next') or 'home'

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier'].strip()
            password = form.cleaned_data['password']

            if not identifier or not password:
                messages.error(request, 'Username/Email and password are required.')
                return render(request, 'login.html', {'form': form, 'next': next_url, 'google_login_enabled': google_enabled})

            # Try email then username
            user = None
            try:
                u = User.objects.get(email__iexact=identifier)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                user = authenticate(request, username=identifier, password=password)

            if user is not None:
                login(request, user)

                # Remember me
                if form.cleaned_data.get('remember_me'):
                    request.session.set_expiry(60 * 60 * 24 * 14)  # 14 days
                else:
                    request.session.set_expiry(0)  # expire on browser close

                # Safe redirect only - reject protocol-relative URLs explicitly
                if next_url and next_url.startswith('//'):
                    # Reject protocol-relative URLs (//evil.com)
                    return redirect('home')
                elif next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                    return redirect(next_url)
                return redirect('home')
            else:
                messages.error(request, 'Invalid username/email or password')
        # failed auth or invalid form
        return render(request, 'login.html', {'form': form, 'next': next_url, 'google_login_enabled': google_enabled})

    # GET
    form = LoginForm()
    return render(request, 'login.html', {'form': form, 'next': next_url, 'google_login_enabled': google_enabled})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.create_user(
                    username=form.cleaned_data['username'].strip(),
                    email=form.cleaned_data['email'].strip(),
                    password=form.cleaned_data['password'],
                )
                messages.success(request, "Account created successfully. You're now logged in.")
                login(request, user)
                return redirect('home')
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
                return render(request, 'signup.html', {'form': form})
        else:
            return render(request, 'signup.html', {'form': form})

    form = SignupForm()
    return render(request, 'signup.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.success(request, f'Goodbye {username}! You have been logged out successfully!')
    return redirect('home')


# -------------------- PROFILE VIEWS --------------------

@login_required(login_url='login')
def profile(request):
    return render(request, 'profile.html', {'user': request.user})


@login_required(login_url='login')
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        username = (request.POST.get('username') or '').strip()
        email = (request.POST.get('email') or '').strip()
        first_name = (request.POST.get('first_name') or '').strip()
        last_name = (request.POST.get('last_name') or '').strip()

        if username and username != user.username and User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken!')
            return render(request, 'edit_profile.html')

        if email and email != user.email and User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'Email already registered!')
            return render(request, 'edit_profile.html')

        try:
            if username:
                user.username = username
            if email:
                user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            return render(request, 'edit_profile.html')

    return render(request, 'edit_profile.html')


@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        user = request.user
        old_password = (request.POST.get('old_password') or '')
        new_password = (request.POST.get('new_password') or '')
        confirm_password = (request.POST.get('confirm_password') or '')

        if not user.check_password(old_password):
            messages.error(request, 'Current password is incorrect!')
            return render(request, 'change_password.html')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match!')
            return render(request, 'change_password.html')

        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long!')
            return render(request, 'change_password.html')

        if old_password == new_password:
            messages.error(request, 'New password must be different from current password!')
            return render(request, 'change_password.html')

        try:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)  # keep logged in
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
        except Exception as e:
            messages.error(request, f'Error changing password: {str(e)}')
            return render(request, 'change_password.html')

    return render(request, 'change_password.html')


# -------------------- GOOGLE OAUTH --------------------

def google_login(request):
    client_id = settings.GOOGLE_OAUTH.get('CLIENT_ID', '')
    redirect_uri = settings.GOOGLE_OAUTH.get('REDIRECT_URI', '')
    scope = settings.GOOGLE_OAUTH.get('SCOPE', 'openid email profile')

    if not client_id or not redirect_uri:
        messages.error(request, 'Google login is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_REDIRECT_URI.')
        return redirect('login')

    raw_next = request.GET.get('next') or ''
    # Validate next_url: reject protocol-relative URLs (//evil.com) and only allow safe paths
    # Check url_has_allowed_host_and_scheme first, then allow absolute paths starting with single /
    if raw_next:
        # Reject protocol-relative URLs explicitly
        if raw_next.startswith('//'):
            next_url = ''
        # Allow if it passes host/scheme validation
        elif url_has_allowed_host_and_scheme(raw_next, {request.get_host()}):
            next_url = raw_next
        # Allow absolute paths starting with single / (not //)
        elif raw_next.startswith('/') and not raw_next.startswith('//'):
            next_url = raw_next
        else:
            next_url = ''
    else:
        next_url = ''

    # Generate a cryptographically secure state and store in session
    # and in the cache as a fallback. Some browsers or OAuth setups may
    # not preserve session cookies across the external Google redirect
    # (e.g. different hostnames like 127.0.0.1 vs localhost). Storing
    # the state in a short-lived cache key makes the callback more
    # robust for development environments.
    state = secrets.token_urlsafe(24)
    request.session['google_oauth_state'] = state
    request.session['google_oauth_next'] = next_url
    try:
        cache.set(f'google_oauth_state:{state}', next_url, timeout=600)
    except Exception:
        # Cache is optional; continue without failing if unavailable.
        logger.debug('Could not write google_oauth_state to cache')

    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': scope,
        'access_type': 'online',
        'include_granted_scopes': 'true',
        'prompt': 'select_account',
        'state': state,
    }
    auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(params)
    return redirect(auth_url)


def google_callback(request):
    error = request.GET.get('error')
    if error:
        messages.error(request, f'Google login error: {error}')
        return redirect('login')

    code = request.GET.get('code')
    state = request.GET.get('state') or ''
    expected_state = request.session.get('google_oauth_state') or ''
    next_url = request.session.get('google_oauth_next') or ''

    # Validate state. If the expected state is missing from the session
    # (e.g. session cookie wasn't preserved), try a fallback lookup in
    # the cache using the state value. This makes the flow resilient in
    # development or when clients drop cookies during the external
    # redirect.
    cache_key = f'google_oauth_state:{state}' if state else None
    if (not state) or (not expected_state) or (state != expected_state):
        fallback_next = None
        if cache_key:
            try:
                fallback_next = cache.get(cache_key)
            except Exception:
                fallback_next = None

        if fallback_next is not None:
            # Accept the cached state value; populate next_url for
            # subsequent redirect handling and continue.
            next_url = fallback_next or ''
            logger.info('Google OAuth state resolved from cache for state=%s', state)
        else:
            logger.warning('Invalid Google OAuth state: expected=%s got=%s sessionid=%s', expected_state, state, request.COOKIES.get('sessionid'))
            messages.error(request, 'Invalid login state. Please try again.')
            # Clean up possibly stale session values
            request.session.pop('google_oauth_state', None)
            request.session.pop('google_oauth_next', None)
            if cache_key:
                try:
                    cache.delete(cache_key)
                except Exception:
                    pass
            return redirect('login')

    # If we got here and there is a cache entry, remove it now.
    if cache_key:
        try:
            cache.delete(cache_key)
        except Exception:
            pass

    if not code:
        messages.error(request, 'Missing authorization code from Google.')
        return redirect('login')

    client_id = settings.GOOGLE_OAUTH.get('CLIENT_ID', '')
    client_secret = settings.GOOGLE_OAUTH.get('CLIENT_SECRET', '')
    redirect_uri = settings.GOOGLE_OAUTH.get('REDIRECT_URI', '')

    if not client_id or not client_secret or not redirect_uri:
        messages.error(request, 'Google login is not configured on server.')
        return redirect('login')

    token_endpoint = 'https://oauth2.googleapis.com/token'
    data = urlencode({
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }).encode('utf-8')

    try:
        req = Request(token_endpoint, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with urlopen(req, timeout=10) as resp:
            token_payload = json.loads(resp.read().decode('utf-8'))
    except (HTTPError, URLError) as e:
        messages.error(request, f'Failed to exchange Google auth code: {e}')
        return redirect('login')

    access_token = token_payload.get('access_token')
    if not access_token:
        messages.error(request, 'Google did not return an access token.')
        return redirect('login')

    # Fetch user info
    userinfo_endpoint = 'https://openidconnect.googleapis.com/v1/userinfo'
    try:
        req = Request(userinfo_endpoint, headers={'Authorization': f'Bearer {access_token}'})
        with urlopen(req, timeout=10) as resp:
            profile = json.loads(resp.read().decode('utf-8'))
    except (HTTPError, URLError) as e:
        messages.error(request, f'Failed to fetch Google user profile: {e}')
        return redirect('login')

    email = (profile.get('email') or '').strip().lower()
    email_verified = profile.get('email_verified')
    if not email:
        messages.error(request, 'No email returned from Google.')
        return redirect('login')
    if email_verified is False:
        messages.error(request, 'Google email is not verified. Please verify your email with Google.')
        return redirect('login')

    first_name = (profile.get('given_name') or '').strip()
    last_name = (profile.get('family_name') or '').strip()

    # Get or create a local user mapped by email. It's possible the
    # database contains duplicate User rows for the same email (not
    # enforced by default). Guard against MultipleObjectsReturned by
    # selecting the earliest created user and logging a warning so an
    # administrator can deduplicate later.
    user = None
    users_qs = User.objects.filter(email__iexact=email)
    if users_qs.exists():
        user = users_qs.order_by('id').first()
        if users_qs.count() > 1:
            logger.warning(
                "Multiple user accounts found for email %s. Using user id=%s",
                email,
                user.pk,
            )
    else:
        # Derive a unique username from email
        base_username = email.split('@')[0][:30] or 'user'
        candidate = base_username
        suffix = 1
        while User.objects.filter(username=candidate).exists():
            # Ensure max length 150
            candidate = f"{base_username[:120]}{suffix}"
            suffix += 1

        user = User.objects.create_user(
            username=candidate,
            email=email,
            password=secrets.token_urlsafe(32),
            first_name=first_name,
            last_name=last_name,
        )

    # Log in the user. Since multiple authentication backends are configured
    # (ModelBackend and allauth's AuthenticationBackend), we must specify which
    # backend authenticated this user. We use ModelBackend since this is a
    # local Django User account.
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    # Safe redirect to original destination if present
    # Clean up session state
    request.session.pop('google_oauth_state', None)
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        request.session.pop('google_oauth_next', None)
        return redirect(next_url)
    request.session.pop('google_oauth_next', None)

    return redirect('home')
