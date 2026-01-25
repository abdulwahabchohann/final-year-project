#!/usr/bin/env python
"""Test mood recommendations with various moods."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readwise.settings')
django.setup()

from accounts.services.mood_recommender import get_mood_recommender

test_cases = [
    "I feel anxious and need something calming",
    "I'm feeling sad and lonely",
    "I'm excited and want an adventure",
    "I need inspiration and motivation",
    "I'm bored and want something fun"
]

rec = get_mood_recommender()

for mood in test_cases:
    print(f"\n{'='*70}")
    print(f"Mood: {mood}")
    print('='*70)
    
    recommendations = rec.recommend_books(mood, limit=5)
    
    print(f"Found {len(recommendations)} recommendations:\n")
    
    titles = set()
    for i, r in enumerate(recommendations, 1):
        # Check for duplicates
        normalized = r['title'].lower()
        if normalized in titles:
            print(f"❌ DUPLICATE: {r['title']}")
        else:
            titles.add(normalized)
            print(f"{i}. {r['title']}")
            print(f"   Author: {r['author']}")
            print(f"   Match: {r['sentiment_score']*100:.0f}%")
            print(f"   Mood: {r['dominant_mood']}")
            print()
