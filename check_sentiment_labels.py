import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Check sentiment_label distribution
cursor.execute("""
    SELECT sentiment_label, COUNT(*)
    FROM accounts_book
    GROUP BY sentiment_label
""")

print("Sentiment Label Distribution:")
for row in cursor.fetchall():
    print(f"'{row[0]}': {row[1]}")

conn.close()
