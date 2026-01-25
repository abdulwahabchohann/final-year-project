import pytest
from django.core.management import call_command
from django.urls import reverse

from accounts.models import Category


pytestmark = pytest.mark.django_db


def test_category_list_view_returns_paginated_data(client, monkeypatch):
    sample = [
        {'slug': 'self-help', 'display_name': 'Self-Help', 'book_count_estimate': 18230},
        {'slug': 'fiction', 'display_name': 'Fiction', 'book_count_estimate': None},
    ]

    monkeypatch.setattr('accounts.views.get_cached_category_list', lambda force_refresh=False: sample)

    response = client.get(reverse('api_category_list'))
    assert response.status_code == 200

    payload = response.json()
    assert payload['count'] == len(sample)
    assert payload['results'][0]['slug'] == 'self-help'
    assert payload['results'][1]['book_count_estimate'] is None


def test_category_books_view_uses_cached_payload(client, monkeypatch):
    category = Category.objects.create(display_name='Self-Help', slug='self-help')
    sample_items = [
        {
            'id': 'gb:xyz',
            'title': 'Atomic Habits',
            'authors': ['James Clear'],
            'description': 'An easy & proven way to build good habits and break bad ones.',
            'categories': ['Self-Help'],
            'thumbnail': 'https://example.com/atomic.jpg',
            'info_url': 'https://books.google.com/example',
            'published_year': 2018,
            'source': 'google',
        }
    ]

    monkeypatch.setattr(
        'accounts.views.get_cached_books',
        lambda slug, page: {'page': page, 'items': sample_items},
    )
    monkeypatch.setattr('accounts.views.cache_books', lambda slug, page, payload: None)
    monkeypatch.setattr('accounts.views.fetch_books_for_category', lambda slug, display_name, page: [])

    response = client.get(reverse('api_category_books', kwargs={'slug': category.slug}))
    assert response.status_code == 200

    payload = response.json()
    assert payload['page'] == 1
    assert payload['items'][0]['id'] == 'gb:xyz'
    assert payload['items'][0]['source'] == 'google'


def test_category_books_view_rejects_invalid_page(client):
    category = Category.objects.create(display_name='Fiction', slug='fiction')
    response = client.get(reverse('api_category_books', kwargs={'slug': category.slug}), {'page': 0})
    assert response.status_code == 400
    payload = response.json()
    assert 'page' in payload


def test_sync_categories_command(monkeypatch, capsys):
    sample_payload = [
        type('Payload', (), {'slug': 'fiction', 'display_name': 'Fiction'}),
        type('Payload', (), {'slug': 'science', 'display_name': 'Science'}),
    ]

    monkeypatch.setattr(
        'accounts.management.commands.sync_categories.sync_categories',
        lambda force_refresh=True: sample_payload,
    )

    call_command('sync_categories')
    captured = capsys.readouterr()
    assert 'Synchronised 2 categories' in captured.out
