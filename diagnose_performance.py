#!/usr/bin/env python
"""Diagnose recommendation processing performance."""
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readwise.settings')
django.setup()

from accounts.services.mood_recommender import get_mood_recommender
from accounts.services.sentiment_analysis import get_sentiment_analyzer

print("="*70)
print("PERFORMANCE DIAGNOSIS: Recommendation Processing")
print("="*70)

# Test 1: Sentiment Analysis Speed
print("\n1. SENTIMENT ANALYZER SPEED TEST")
print("-"*70)
analyzer = get_sentiment_analyzer()

test_moods = [
    "I feel anxious and need something calming",
    "I'm feeling sad and lonely",
]

for mood in test_moods:
    start = time.time()
    result = analyzer.analyze_text(mood)
    elapsed = time.time() - start
    method = result.get('analysis_method', 'unknown')
    print(f"  '{mood[:40]}...'")
    print(f"    Method: {method}")
    print(f"    Time: {elapsed:.2f}s")
    print(f"    Models available: {method == 'transformer'}")

# Test 2: Book Recommendation Speed
print("\n2. BOOK RECOMMENDATION SPEED TEST")
print("-"*70)
rec = get_mood_recommender()

mood = "I feel anxious and need something calming"
print(f"  Mood: {mood}")
print(f"  Processing...")

start = time.time()
recommendations = rec.recommend_books(mood, limit=5)
total_time = time.time() - start

print(f"  [OK] Found {len(recommendations)} recommendations in {total_time:.2f}s")
print(f"  Average time per recommendation: {total_time/len(recommendations):.2f}s")

# Test 3: Database Query Speed
print("\n3. DATABASE QUERY SPEED")
print("-"*70)
from accounts.models import Book

start = time.time()
books_count = Book.objects.count()
elapsed = time.time() - start
print(f"  Total books in DB: {books_count}")
print(f"  Query time: {elapsed:.3f}s")

start = time.time()
books = Book.objects.filter(
    description__isnull=False
).exclude(
    description=''
).select_related().prefetch_related('genres', 'authors')[:1000]
elapsed = time.time() - start
print(f"  Query 1000 books with relations: {elapsed:.3f}s")

# Test 4: Network Check (HuggingFace model cache)
print("\n4. NETWORK/MODEL CACHE STATUS")
print("-"*70)
from transformers import pipeline
from sentence_transformers import SentenceTransformer

try:
    # Check if models are cached
    import os
    hf_cache = os.path.expanduser("~/.cache/huggingface")
    if os.path.exists(hf_cache):
        cache_size = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                        for dirpath, dirnames, filenames in os.walk(hf_cache) 
                        for filename in filenames)
        print(f"  [OK] HuggingFace cache exists: {cache_size / 1e9:.2f} GB")
    else:
        print(f"  ⚠ HuggingFace cache not found (models will download on first use)")
except Exception as e:
    print(f"  ⚠ Cache check failed: {e}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("""
If recommendation processing is slow:

FAST (< 1s total):
  → Good network, models cached, system performing well

SLOW (5-10s total):
  → Normal first-time model load or network lag
  → Subsequent requests will be faster (models cached)

VERY SLOW (> 30s):
  → Check: Internet connection
  → Check: CPU usage (transformer models are CPU intensive)
  → Consider: Reduce limit parameter (fewer books to analyze)
  → Consider: Async processing for production

INTERNET ISSUES INDICATORS:
  - HuggingFace cache not found
  - Models downloading on every request
  - Timeouts when loading transformers
  - Network errors in logs

SYSTEM ISSUES INDICATORS:
  - High CPU usage (> 80%)
  - Low memory available
  - Disk I/O bottleneck
  - Database queries slow (> 1s)
""")
