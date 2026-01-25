"""
Example usage of the Sentiment Analysis Module
Demonstrates how to use the recommendation engine
"""

import json
from sentiment_analyzer import RecommendationEngine, recommend_books_by_mood

def example_1_basic_usage():
    """Basic usage - quick recommendations"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Usage - Quick Recommendations")
    print("="*80)
    
    mood = "I'm feeling anxious and need something calming"
    
    print(f"\nUser mood: '{mood}'")
    print("\nGetting recommendations...")
    
    recommendations = recommend_books_by_mood(
        mood=mood,
        dataset_path='books_dataset_5000.json',
        top_k=5
    )
    
    print(f"\n{'='*80}")
    print("TOP 5 RECOMMENDATIONS:")
    print(f"{'='*80}\n")
    
    for i, book in enumerate(recommendations, 1):
        print(f"{i}. {book['title']}")
        print(f"   Author: {book['author']}")
        print(f"   Genres: {', '.join(book['genres'][:2])}")
        print(f"   Match Score: {book['sentiment_score']:.1%}")
        print(f"   Why: {book['recommendation_reason']}")
        if book['average_rating']:
            print(f"   Rating: {book['average_rating']:.2f}/5.0")
        print()


def example_2_multiple_moods():
    """Test different moods"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Testing Multiple Moods")
    print("="*80)
    
    # Load dataset once
    with open('books_dataset_5000.json', 'r', encoding='utf-8') as f:
        books = json.load(f)
    
    # Initialize engine once
    engine = RecommendationEngine()
    
    moods = [
        "I'm feeling happy and want something fun",
        "I'm sad and need comfort",
        "I want something exciting and adventurous",
        "I need inspiration and motivation",
        "I'm feeling romantic and dreamy"
    ]
    
    for mood in moods:
        print(f"\n{'-'*80}")
        print(f"Mood: {mood}")
        print(f"{'-'*80}")
        
        recommendations = engine.get_recommendations(mood, books, top_k=3)
        
        for i, book in enumerate(recommendations, 1):
            print(f"\n{i}. {book['title']} by {book['author']}")
            print(f"   Score: {book['sentiment_score']:.1%} | {book['recommendation_reason']}")


def example_3_analyze_dataset():
    """Pre-analyze entire dataset and cache results"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Analyzing Entire Dataset (with caching)")
    print("="*80)
    
    # Load dataset
    with open('books_dataset_5000.json', 'r', encoding='utf-8') as f:
        books = json.load(f)
    
    print(f"\nDataset loaded: {len(books)} books")
    
    # Initialize engine
    engine = RecommendationEngine(cache_file='sentiment_cache.pkl')
    
    # Analyze all books (this will cache results)
    print("\nAnalyzing all books... (this may take a few minutes)")
    results = engine.analyze_dataset(books)
    
    print(f"\n✓ Analyzed {len(results)} books")
    print("✓ Results cached to 'sentiment_cache.pkl'")
    print("\nNow subsequent recommendations will be much faster!")
    
    # Show some statistics
    print("\n" + "="*80)
    print("EMOTION STATISTICS ACROSS DATASET:")
    print("="*80)
    
    from collections import defaultdict
    emotion_totals = defaultdict(float)
    emotion_counts = defaultdict(int)
    
    for book_id, emotions in results.items():
        for emotion, score in emotions.items():
            if score > 0.1:  # Only count significant emotions
                emotion_totals[emotion] += score
                emotion_counts[emotion] += 1
    
    print("\nMost common emotions in books:")
    sorted_emotions = sorted(
        emotion_totals.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    for emotion, total in sorted_emotions[:10]:
        avg_score = total / emotion_counts[emotion] if emotion_counts[emotion] > 0 else 0
        print(f"  {emotion.capitalize():15s}: {emotion_counts[emotion]:4d} books (avg score: {avg_score:.2f})")


def example_4_custom_book_search():
    """Search for books with specific emotional characteristics"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Finding Books by Specific Emotions")
    print("="*80)
    
    # Load dataset
    with open('books_dataset_5000.json', 'r', encoding='utf-8') as f:
        books = json.load(f)
    
    # Initialize engine
    engine = RecommendationEngine()
    
    # Analyze books
    print("\nAnalyzing books...")
    results = engine.analyze_dataset(books)
    
    # Find books with high joy content
    print("\n" + "-"*80)
    print("Books with HIGH JOY content:")
    print("-"*80)
    
    joyful_books = []
    for book in books:
        book_id = book.get('book_id')
        if book_id in results:
            emotions = results[book_id]
            joy_score = emotions.get('joy', 0) + emotions.get('optimism', 0)
            if joy_score > 0.5:
                joyful_books.append((book, joy_score))
    
    joyful_books.sort(key=lambda x: x[1], reverse=True)
    
    for book, score in joyful_books[:5]:
        print(f"\n• {book['title']}")
        print(f"  Genres: {', '.join(book['genres'][:2])}")
        print(f"  Joy Score: {score:.2f}")


def example_5_production_integration():
    """Example of how to integrate into a production system"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Production Integration Pattern")
    print("="*80)
    
    print("""
The module is designed for easy integration into larger systems:

# In your Django/Flask application:

from sentiment_analyzer import RecommendationEngine
import json

# Initialize once (e.g., at app startup)
with open('books_dataset_5000.json', 'r') as f:
    BOOKS_DATABASE = json.load(f)

# Pre-analyze and cache (do this once, maybe in a background job)
engine = RecommendationEngine(cache_file='prod_sentiment_cache.pkl')
engine.analyze_dataset(BOOKS_DATABASE)

# In your API endpoint:
def get_mood_recommendations(user_id, user_mood_text):
    '''API endpoint to get recommendations'''
    
    # Get recommendations
    recommendations = engine.get_recommendations(
        user_mood=user_mood_text,
        books=BOOKS_DATABASE,
        top_k=5,
        complementary_mode=True
    )
    
    # Format for API response
    return {
        'user_id': user_id,
        'mood': user_mood_text,
        'recommendations': [
            {
                'book_id': rec['book_id'],
                'title': rec['title'],
                'author': rec['author'],
                'genres': rec['genres'],
                'match_score': rec['sentiment_score'],
                'explanation': rec['recommendation_reason'],
                'rating': rec['average_rating']
            }
            for rec in recommendations
        ],
        'timestamp': datetime.now().isoformat()
    }

# Benefits:
# ✓ Pre-analyzed dataset = fast recommendations (< 2 seconds)
# ✓ Cached results = no re-computation
# ✓ Modular design = easy to update models
# ✓ Explainable AI = users understand why books are recommended
    """)


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("SENTIMENT ANALYSIS MODULE - EXAMPLES")
    print("="*80)
    
    print("\nThis script demonstrates various usage patterns.")
    print("Choose an example to run:")
    print("\n1. Basic usage - Quick recommendations")
    print("2. Multiple moods testing")
    print("3. Analyze entire dataset (with caching)")
    print("4. Find books by specific emotions")
    print("5. Production integration pattern")
    print("6. Run all examples")
    
    try:
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == '1':
            example_1_basic_usage()
        elif choice == '2':
            example_2_multiple_moods()
        elif choice == '3':
            example_3_analyze_dataset()
        elif choice == '4':
            example_4_custom_book_search()
        elif choice == '5':
            example_5_production_integration()
        elif choice == '6':
            example_1_basic_usage()
            example_2_multiple_moods()
            example_3_analyze_dataset()
            example_4_custom_book_search()
            example_5_production_integration()
        else:
            print("Invalid choice. Running Example 1...")
            example_1_basic_usage()
    
    except KeyboardInterrupt:
        print("\n\nExecution cancelled by user.")
    except FileNotFoundError:
        print("\n❌ Error: books_dataset_5000.json not found!")
        print("Please run export_books_dataset.py first to generate the dataset.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
