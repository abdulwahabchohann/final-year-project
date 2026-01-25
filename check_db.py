import sqlite3
import sys

try:
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
    
    print("\n" + "="*50)
    
    # Check for book-related tables
    book_tables = [t[0] for t in tables if 'book' in t[0].lower()]
    if book_tables:
        print(f"\nFound {len(book_tables)} book-related table(s):")
        for table_name in book_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  - {table_name}: {count} rows")
            
            # Show schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"    Columns: {', '.join([col[1] for col in columns])}")
    else:
        print("\nNo book-related tables found.")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
