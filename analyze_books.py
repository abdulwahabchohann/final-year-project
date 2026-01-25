import sqlite3
import json

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Get sample of books with their data
cursor.execute("""
    SELECT id, title, description, average_rating, 
           sentiment_label, sentiment_score, mood_scores,
           dominant_mood, emotional_intensity
    FROM accounts_book
    LIMIT 20
""")

books = cursor.fetchall()

print("Sample of Books in Database:")
print("="*80)

for book in books[:5]:
    print(f"\nID: {book[0]}")
    print(f"Title: {book[1]}")
    print(f"Description: {book[2][:150] if book[2] else 'NO DESCRIPTION'}...")
    print(f"Rating: {book[3]}")
    print(f"Sentiment Label: {book[4]}")
    print(f"Sentiment Score: {book[5]}")
    print(f"Mood Scores: {book[6]}")
    print(f"Dominant Mood: {book[7]}")
    print(f"Emotional Intensity: {book[8]}")
    print("-"*80)

# Check completeness
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END) as with_description,
        SUM(CASE WHEN sentiment_score IS NOT NULL THEN 1 ELSE 0 END) as with_sentiment,
        SUM(CASE WHEN mood_scores IS NOT NULL THEN 1 ELSE 0 END) as with_mood
    FROM accounts_book
""")

stats = cursor.fetchone()
print(f"\nDatabase Statistics:")
print(f"Total Books: {stats[0]}")
print(f"Books with Description: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
print(f"Books with Sentiment Score: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)")
print(f"Books with Mood Scores: {stats[3]} ({stats[3]/stats[0]*100:.1f}%)")

# Get genre distribution
cursor.execute("""
    SELECT g.name, COUNT(*) as count
    FROM accounts_genre g
    JOIN accounts_book_genres bg ON g.id = bg.genre_id
    GROUP BY g.name
    ORDER BY count DESC
    LIMIT 10
""")

genres = cursor.fetchall()
print(f"\nTop 10 Genres:")
for genre, count in genres:
    print(f"  {genre}: {count} books")

conn.close()
