"""
Export 5000 books from database with good diversity
"""
import sqlite3
import json
from collections import defaultdict

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Get 5000 books with descriptions, ordered randomly for diversity
cursor.execute("""
    SELECT 
        b.id, b.title, b.description, b.published_year,
        b.average_rating, b.ratings_count, b.language,
        b.sentiment_score, b.mood_scores, b.dominant_mood,
        b.emotional_intensity, b.page_count
    FROM accounts_book b
    WHERE b.description IS NOT NULL AND b.description != ''
    ORDER BY RANDOM()
    LIMIT 5000
""")

all_books = []
for row in cursor.fetchall():
    # Get authors
    cursor.execute("""
        SELECT a.full_name
        FROM accounts_author a
        JOIN accounts_book_authors ba ON a.id = ba.author_id
        WHERE ba.book_id = ?
    """, (row[0],))
    authors = [a[0] for a in cursor.fetchall()]
    
    # Get all genres for this book
    cursor.execute("""
        SELECT g.name
        FROM accounts_genre g
        JOIN accounts_book_genres bg ON g.id = bg.genre_id
        WHERE bg.book_id = ?
        LIMIT 5
    """, (row[0],))
    book_genres = [g[0] for g in cursor.fetchall()]
    
    book_data = {
        'book_id': str(row[0]),
        'title': row[1],
        'author': ', '.join(authors[:3]) if authors else 'Unknown',  # Limit to 3 authors
        'genres': book_genres[:3] if book_genres else ['General'],  # Limit to top 3 genres
        'description': row[2],
        'published_year': row[3],
        'average_rating': float(row[4]) if row[4] else None,
        'ratings_count': row[5],
        'language': row[6],
        'sentiment_score': float(row[7]) if row[7] else None,
        'mood_scores': row[8] if row[8] else '{}',
        'dominant_mood': row[9],
        'emotional_intensity': float(row[10]) if row[10] else None,
        'page_count': row[11],
        'reviews': []  # Can add synthetic reviews later if needed
    }
    
    all_books.append(book_data)

print(f"Exported {len(all_books)} books")

# Save to JSON
output_file = 'books_dataset_5000.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_books, f, indent=2, ensure_ascii=False)

print(f"Dataset saved to {output_file}")

# Print statistics
genre_counts = defaultdict(int)
lang_counts = defaultdict(int)
for book in all_books:
    for genre in book['genres']:
        genre_counts[genre] += 1
    if book.get('language'):
        lang_counts[book['language']] += 1

print("\nTop 20 Genres:")
for genre, count in sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
    print(f"  {genre}: {count} books")

print(f"\nLanguage Distribution:")
for lang, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {lang}: {count} books")

print(f"\nBooks with descriptions: {sum(1 for b in all_books if b['description'])}")
print(f"Books with ratings: {sum(1 for b in all_books if b['average_rating'])}")
if sum(1 for b in all_books if b['average_rating']) > 0:
    print(f"Average rating: {sum(b['average_rating'] for b in all_books if b['average_rating']) / sum(1 for b in all_books if b['average_rating']):.2f}")

conn.close()
print("\n✓ Dataset export complete!")
