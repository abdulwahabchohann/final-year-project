# Populating the Database for Mood Recommendations

To ensure the mood-based recommendation system works efficiently, you need to populate the database with sentiment analysis data.

## 1. Run the Analysis Command

We have created a management command to analyze books and store their mood scores.

```bash
# Analyze all books (this may take a while)
python manage.py analyze_book_sentiments

# Analyze a batch of books (e.g., 100)
python manage.py analyze_book_sentiments --limit 100

# Analyze a specific book by ID
python manage.py analyze_book_sentiments --book-id 123
```

## 2. Verify Data

You can check if the data is populated using the `check_mood_scores.py` script:

```bash
python check_mood_scores.py
```

## 3. Performance Optimization

We have optimized `accounts/services/mood_recommender.py` to use the stored mood scores instead of re-analyzing the text on every request. This significantly improves the response time of the recommendation page.

## 4. Troubleshooting

If you see "No candidate books found" or slow performance:
- Ensure you have run the analysis command for at least a subset of books.
- Check `check_sentiment_labels.py` to see the distribution of sentiment labels.
