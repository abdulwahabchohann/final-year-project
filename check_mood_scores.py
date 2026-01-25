import sqlite3
import json

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Get sample of books with non-empty mood scores
cursor.execute("""
    SELECT id, title, mood_scores
    FROM accounts_book
    WHERE mood_scores != '{}' AND mood_scores IS NOT NULL
    LIMIT 1
""")

book = cursor.fetchone()

if book:
    print(f"ID: {book[0]}")
    print(f"Title: {book[1]}")
    print(f"Mood Scores: {book[2]}")
else:
    print("No books with mood scores found.")

conn.close()
