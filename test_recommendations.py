#!/usr/bin/env python
"""Test mood recommendations with ML models installed."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readwise.settings')
django.setup()

from accounts.services.mood_recommender import get_mood_recommender

print("Testing Mood Recommender with Transformer Models")
print("=" * 60)

rec = get_mood_recommender()
recommendations = rec.recommend_books('I feel anxious and need something calming', limit=5)

print(f"\nFound {len(recommendations)} recommendations for: 'I feel anxious and need something calming'")
print("-" * 60)

for i, r in enumerate(recommendations, 1):
    print(f"\n{i}. {r['title']}")
    print(f"   Author: {r['author']}")
    print(f"   Match Score: {r['sentiment_score']*100:.1f}%")
    print(f"   Mood: {r['dominant_mood']}")
    print(f"   Genre: {r['genre']}")
    print(f"   Why: {r['recommendation_reason'][:100]}...")
