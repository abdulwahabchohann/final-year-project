# Deployment (Aggregated)

This file aggregates the platform-specific deployment guides and related setup notes.

## DEPLOY_RENDER.md

# Render Deployment Guide

This project is configured for Render using `render.yaml` with:
- one Python web service
- one managed Postgres database
- production-safe Django settings from environment variables

## 1. Prepare repository

1. Push the latest branch to GitHub.
2. In Render, create a new Blueprint service from this repository.
3. Set your final service hostname in `render.yaml` values (replace `your-service-name.onrender.com`) or override those env vars in the Render dashboard.

## 2. Required environment variables

Set these in Render (or keep from `render.yaml` defaults where applicable):
- `SECRET_KEY`
- `DEBUG=False`
- `IS_PRODUCTION=True`
- `ALLOWED_HOSTS=<service>.onrender.com`
- `CSRF_TRUSTED_ORIGINS=https://<service>.onrender.com`
- `SITE_BASE_URL=https://<service>.onrender.com`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI=https://<service>.onrender.com/accounts/oauth2callback/`
- `GOOGLE_BOOKS_API_KEY`
- `DATABASE_URL` (injected from Render Postgres)
- Optional: `SECURE_HSTS_PRELOAD=False` (set `True` if you want `check --deploy` with zero HSTS preload warnings)

## 3. Data migration: SQLite -> Postgres

Run these locally to export current SQLite data:

```powershell
python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude admin.logentry --indent 2 > data/prod_seed.json
```

Then import into Postgres (set `DATABASE_URL` to Render Postgres connection string):

```powershell
$env:DATABASE_URL = "postgres://..."
python manage.py migrate
python manage.py loaddata data/prod_seed.json
```

Update Django Sites record for OAuth:

```powershell
python manage.py shell -c "from django.contrib.sites.models import Site; Site.objects.update_or_create(id=1, defaults={'domain':'<service>.onrender.com','name':'readwise'})"
```

Validate key model counts:

```powershell
python manage.py shell -c "from django.contrib.auth.models import User; from accounts.models import Book, Author, Genre; print({'users': User.objects.count(), 'books': Book.objects.count(), 'authors': Author.objects.count(), 'genres': Genre.objects.count()})"
```

## 4. Google OAuth cutover

In Google Cloud Console OAuth client:
- add `https://<service>.onrender.com/accounts/oauth2callback/` to Authorized redirect URIs
- ensure Render env vars match exactly

## 5. Pre-deploy checks

```powershell
python manage.py check
python manage.py check --deploy
python manage.py collectstatic --noinput
```

## 6. Post-deploy smoke tests

1. Home page static assets load.
2. Signup, login, logout work.
3. Google login round-trip succeeds.
4. Search, categories, trending pages work.
5. `POST /api/recommendations/mood/` returns successful response in fallback mode.
6. `POST /api/recommendations/dataset/` returns deterministic payload.

## 7. Rollback approach

If deployment fails, rollback by redeploying the previous stable commit in Render.

---

## DEPLOY_PYTHONANYWHERE.md

# PythonAnywhere Deployment Guide (Free Plan + SQLite)

This guide deploys ReadWise to PythonAnywhere using a free account and SQLite.
It keeps your existing Render files (`render.yaml`, `DEPLOY_RENDER.md`) for rollback.

## 1) Create the web app

1. Log in to PythonAnywhere.
2. Go to `Web` -> `Add a new web app`.
3. Choose `Manual configuration`.
4. Pick Python `3.10+`.
5. Use the provided free-domain app URL:
   - `https://<username>.pythonanywhere.com`
   - or EU region variant shown in your account.

## 2) Clone and install on PythonAnywhere

Open a PythonAnywhere `Bash` console and run:

```bash
cd ~
git clone https://github.com/abdulwahabchohann/final-year-project.git
cd final-year-project
python3.10 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Configure environment variables

Create `/home/<username>/final-year-project/.env`:

```env
DEBUG=False
IS_PRODUCTION=True
SECRET_KEY=<strong-random-secret>
ALLOWED_HOSTS=<username>.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://<username>.pythonanywhere.com
SITE_BASE_URL=https://<username>.pythonanywhere.com
GOOGLE_CLIENT_ID=<google-client-id>
GOOGLE_CLIENT_SECRET=<google-client-secret>
GOOGLE_REDIRECT_URI=https://<username>.pythonanywhere.com/accounts/oauth2callback/
GOOGLE_BOOKS_API_KEY=<google-books-key>
SECURE_HSTS_PRELOAD=False
```

Notes:
- Keep `.env` private (already ignored by git).
- If your domain is different (EU/custom), replace all domain lines with the exact URL.

## 4) Run migrations and collect static

```bash
cd ~/final-year-project
source .venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
```

## 5) Configure WSGI on PythonAnywhere

Edit:

`/var/www/<username>_pythonanywhere_com_wsgi.py`

Use:

```python
import sys

path = '/home/<username>/final-year-project'
if path not in sys.path:
    sys.path.append(path)

from readwise.wsgi import application
```

## 6) Static files mapping in PythonAnywhere Web tab

Add static mapping:
- URL: `/static/`
- Directory: `/home/<username>/final-year-project/staticfiles`

Then click `Reload` in Web tab.

## 7) Move existing local data (SQLite -> SQLite on PythonAnywhere)

On your local machine (this repo), generate fixture:

```bash
python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude admin.logentry --indent 2 > data/pythonanywhere_seed.json
```

Upload `data/pythonanywhere_seed.json` to:

`/home/<username>/final-year-project/data/pythonanywhere_seed.json`

Then on PythonAnywhere:

```bash
cd ~/final-year-project
source .venv/bin/activate
python manage.py loaddata data/pythonanywhere_seed.json
python manage.py shell -c "from django.contrib.sites.models import Site; Site.objects.update_or_create(id=1, defaults={'domain':'<username>.pythonanywhere.com','name':'readwise'})"
```

## 8) Google OAuth cutover

In Google Cloud Console OAuth client:
- Add authorized redirect URI:
  - `https://<username>.pythonanywhere.com/accounts/oauth2callback/`
- Ensure `.env` `GOOGLE_REDIRECT_URI` matches exactly.
- Reload the PythonAnywhere web app.

## 9) Smoke tests

Open:
- `/`
- `/login/`
- `/categories/`
- `/search/`

Test:
- signup/login/logout
- Google login callback
- API endpoints:
  - `POST /api/recommendations/mood/`
  - `POST /api/recommendations/dataset/`

## 10) Troubleshooting

- `DisallowedHost`: fix `ALLOWED_HOSTS` exact domain.
- CSRF failure: fix `CSRF_TRUSTED_ORIGINS` with full `https://` origin.
- Static missing: re-run `collectstatic`, verify static mapping path.
- OAuth redirect mismatch: check Google Console URI and `.env` URI character-for-character.
- Network/API limits on free plan: if blocked, consider upgrading plan.

## 11) Rollback strategy

If PythonAnywhere has issues, keep Render deployment as fallback until PythonAnywhere is stable.

---

## EXACT_FIX_STEPS.md

# Exact Fix Steps - redirect_uri_mismatch Error

## Current Status:
✅ Code mein redirect URI: `http://localhost:8000/accounts/oauth2callback/`
✅ .env file mein redirect URI: `http://localhost:8000/accounts/oauth2callback/`
✅ Google Cloud Console mein: `http://localhost:8000/accounts/oauth2callback/`

## Problem:
Agar aap site `http://127.0.0.1:8000` se access kar rahe hain, to mismatch ho sakta hai.

## Solution:

### Step 1: Google Cloud Console mein jayein
1. [Google Cloud Console](https://console.cloud.google.com/) → Apna project select karein
2. **APIs & Services** → **Credentials**
3. Apni **OAuth 2.0 Client ID** par click karein

### Step 2: Authorized redirect URIs mein DONO add karein

**"Authorized redirect URIs"** section mein yeh **DONO** URIs add karein:

```
http://localhost:8000/accounts/oauth2callback/
http://127.0.0.1:8000/accounts/oauth2callback/
```

**Important:**
- Pehle wala already hai (screenshot mein dikh raha hai)
- **Dusra wala add karein:** `http://127.0.0.1:8000/accounts/oauth2callback/`
- Trailing slash (`/`) zaroori hai
- **"Add URI"** button click karke dusra URI add karein
- **"Save"** button click karein

### Step 3: Wait karein
Google ke according: "It may take 5 minutes to a few hours for settings to take effect"
- Usually 1-2 minutes mein ho jata hai
- Agar immediately kaam nahi kare, to 5 minutes wait karein

### Step 4: Browser mein same URL use karein
- Agar aap `http://localhost:8000` se access kar rahe hain, to wahi use karein
- Ya phir `http://127.0.0.1:8000` use karein (dono kaam karengi ab)

### Step 5: Server restart (optional)
```bash
# Stop server (Ctrl+C)
python manage.py runserver
```

## Why This Works:
- `localhost` aur `127.0.0.1` technically same hain, lekin Google unhein different treat karta hai
- Dono URIs add karne se koi bhi URL se kaam karega
- Safe aur reliable solution hai

## Verification:
1. Google Cloud Console mein dono URIs add karein
2. Save karein
3. 1-2 minutes wait karein
4. Google login try karein
5. Ab kaam karna chahiye! ✅

---

## FIX_REDIRECT_URI.md

# Fix: redirect_uri_mismatch Error

## Problem Analysis:
Screenshot mein Google Cloud Console mein sirf `localhost` ka redirect URI hai, lekin agar aap site `127.0.0.1` se access kar rahe hain to mismatch ho sakta hai.

## Solution:

### Step 1: Google Cloud Console mein DONO redirect URIs add karein

**Authorized redirect URIs** section mein yeh **DONO** add karein:

```
http://localhost:8000/accounts/oauth2callback/
http://127.0.0.1:8000/accounts/oauth2callback/
```

**Important:**
- Dono URIs add karein (localhost aur 127.0.0.1 dono)
- Trailing slash (`/`) zaroori hai
- Exact same format hona chahiye

### Step 2: .env file check karein

`.env` file mein yeh check karein:

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/accounts/oauth2callback/
SITE_BASE_URL=http://localhost:8000
```

**Ya phir** `GOOGLE_REDIRECT_URI` ko completely remove kar dein (comment out kar dein) taake code automatically default use kare:

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
# GOOGLE_REDIRECT_URI=  (comment out - let code use default)
SITE_BASE_URL=http://localhost:8000
```

### Step 3: Server restart karein

```bash
# Stop server (Ctrl+C)
# Then restart:
python manage.py runserver
```

### Step 4: Browser mein same URL use karein

Agar aap `http://localhost:8000` se access kar rahe hain, to Google login bhi wahi se karein.
Agar aap `http://127.0.0.1:8000` se access kar rahe hain, to Google login bhi wahi se karein.

## Why This Happens:
- Google OAuth redirect URI ko EXACT match chahiye
- `localhost` aur `127.0.0.1` technically same hain but Google unhein different treat karta hai
- Isliye dono add karna safe hai

---

## REDIRECT_URI_FIX.md

# Fix: redirect_uri_mismatch Error

## Problem Analysis:
Screenshot mein Google Cloud Console mein sirf `localhost` ka redirect URI hai, lekin agar aap site `127.0.0.1` se access kar rahe hain to mismatch ho sakta hai.

## Solution:

### Step 1: Google Cloud Console mein DONO redirect URIs add karein

**Authorized redirect URIs** section mein yeh **DONO** add karein:

```
http://localhost:8000/accounts/oauth2callback/
http://127.0.0.1:8000/accounts/oauth2callback/
```

**Important:**
- Dono URIs add karein (localhost aur 127.0.0.1 dono)
- Trailing slash (`/`) zaroori hai
- Exact same format hona chahiye

### Step 2: .env file check karein

`.env` file mein yeh check karein:

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/accounts/oauth2callback/
SITE_BASE_URL=http://localhost:8000
```

**Ya phir** `GOOGLE_REDIRECT_URI` ko completely remove kar dein (comment out kar dein) taake code automatically default use kare:

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
# GOOGLE_REDIRECT_URI=  (comment out - let code use default)
SITE_BASE_URL=http://localhost:8000
```

### Step 3: Server restart karein

```bash
# Stop server (Ctrl+C)
# Then restart:
python manage.py runserver
```

### Step 4: Browser mein same URL use karein

Agar aap `http://localhost:8000` se access kar rahe hain, to Google login bhi wahi se karein.
Agar aap `http://127.0.0.1:8000` se access kar rahe hain, to Google login bhi wahi se karein.

## Why This Happens:
- Google OAuth redirect URI ko EXACT match chahiye
- `localhost` aur `127.0.0.1` technically same hain but Google unhein different treat karta hai
- Isliye dono add karna safe hai

---

## GOOGLE_OAUTH_SETUP.md

*(No additional content provided in the upstream file.)*

---

## POPULATE_DB_INSTRUCTIONS.md

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

---

## GOOGLE_OAUTH_FIX.md

# Google OAuth Error 400: redirect_uri_mismatch - Fix Guide

## Problem
Your application is sending this redirect URI to Google:
```
http://localhost:8000/accounts/oauth2callback/
```

But this URI is NOT registered in your Google Cloud Console OAuth credentials.

## Solution: Register the Redirect URI in Google Cloud Console

### Step-by-Step Instructions:

1. **Go to Google Cloud Console**
   - Open: https://console.cloud.google.com/apis/credentials
   - Make sure you're logged in with the same Google account you used to create the OAuth credentials

2. **Find Your OAuth 2.0 Client ID**
   - Look for your OAuth 2.0 Client ID in the list
   - Click on it to open the details

3. **Add Authorized Redirect URIs**
   - Scroll down to the section "Authorized redirect URIs"
   - Click the "+ ADD URI" button
   - Add this EXACT URI (copy-paste it):
     ```
     http://localhost:8000/accounts/oauth2callback/
     ```
   - Click "+ ADD URI" again and also add:
     ```
     http://127.0.0.1:8000/accounts/oauth2callback/
     ```
   - **Important**: Make sure there are NO extra spaces before or after the URI

4. **Save Changes**
   - Click the "SAVE" button at the bottom
   - Wait 1-2 minutes for Google's servers to update

5. **Test Again**
   - Try logging in with Google again
   - The error should be resolved

## Common Mistakes to Avoid:

❌ **DON'T** add `https://localhost:8000/...` (use `http://` not `https://`)
❌ **DON'T** forget the trailing slash `/` at the end
❌ **DON'T** add extra spaces
❌ **DON'T** use `localhost` without the port number `:8000`
❌ **DON'T** forget to click SAVE after adding URIs

✅ **DO** use `http://localhost:8000/accounts/oauth2callback/` (exact match)
✅ **DO** also add `http://127.0.0.1:8000/accounts/oauth2callback/` (alternative)
✅ **DO** wait 1-2 minutes after saving
✅ **DO** make sure you're editing the correct OAuth Client ID (check the Client ID matches your .env file)

## Verification:

After adding the URIs, verify:
1. The URI appears in the "Authorized redirect URIs" list
2. There are no typos or extra spaces
3. You clicked SAVE
4. You waited 1-2 minutes

## Still Having Issues?

If the error persists after following these steps:
1. Double-check that the Client ID in your `.env` file matches the Client ID in Google Cloud Console
2. Make sure you're using the correct Google Cloud project
3. Clear your browser cache and try again
4. Check that your Django server is running on `http://localhost:8000`

---

## SENTIMENT_MODULE_README.md

# Sentiment Analysis Module for Book Recommendations

A production-ready sentiment analysis system that uses state-of-the-art NLP to match books with users' emotional states.

## Features

✅ **Multi-Dimensional Emotion Detection** - Detects 9+ emotions: joy, sadness, anger, fear, surprise, love, optimism, calm, excitement  
✅ **Mood-Based Recommendations** - Natural language mood input → Top 5 matched books  
✅ **Explainable AI** - Every recommendation includes human-readable reasoning  
✅ **Scalable Architecture** - Handles 5000+ books with caching for fast responses  
✅ **Model Training** - Fine-tune on your own book dataset  
✅ **Production Ready** - Modular design, comprehensive tests, easy integration  

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Examples

```bash
# Try the recommendation system
python example_usage.py

# Choose from 5 different examples:
# 1. Basic usage - Quick recommendations
# 2. Multiple moods testing
# 3. Analyze entire dataset (with caching)
# 4. Find books by specific emotions
# 5. Production integration pattern
```

### 3. Get Recommendations

```python
from sentiment_analyzer import recommend_books_by_mood

# Simple one-liner
recommendations = recommend_books_by_mood(
    mood="I'm feeling anxious and need something calming",
    dataset_path="books_dataset_5000.json",
    top_k=5
)

for rec in recommendations:
    print(f"{rec['title']} by {rec['author']}")
    print(f"Match: {rec['sentiment_score']:.0%}")
    print(f"Why: {rec['recommendation_reason']}\n")
```

## Dataset

The module uses `books_dataset_5000.json` containing 5000 diverse books:
- **20+ genres**: Fiction, Self-Help, Biography, Romance, Science Fiction, etc.
- **Multilingual**: English, Spanish, French, German, Italian
- **High quality**: 97% have detailed descriptions
- **Rated**: Average rating 3.76/5.0

### Generate Your Own Dataset

```bash
python export_books_dataset.py
```

This exports 5000 random books from your database with genre diversity.

## Core Components

### 1. EmotionAnalyzer
Uses transformer models for multi-dimensional emotion detection:
- Default: `cardiffnlp/twitter-roberta-base-emotion-multilabel-latest`
- Fallback: Keyword-based sentiment analysis
- Returns emotion scores (0-1) for each category

### 2. SentimentScorer
Calculates match scores using:
- **Emotion similarity** (40%): Cosine similarity between user and book emotions
- **Semantic similarity** (40%): Sentence embeddings comparison
- **Complementary matching** (20%): Uplifting books for negative moods

### 3. ExplainabilityEngine
Generates human-readable explanations:
- Matching emotions identified
- Genre context and themes
- Complementary recommendation reasoning
- Book-specific features extracted from description

### 4. RecommendationEngine
Main API combining all components:
- Book analysis with caching
- Mood-to-book matching
- Top-K recommendations
- Structured output

## Advanced Usage

### Pre-analyze Dataset for Production

```python
from sentiment_analyzer import RecommendationEngine
import json

# Load books
with open('books_dataset_5000.json', 'r') as f:
    books = json.load(f)

# Initialize with cache
engine = RecommendationEngine(cache_file='production_cache.json')

# Analyze all books once (takes ~10 minutes for 5000 books)
engine.analyze_dataset(books)

# Now recommendations are fast (< 2 seconds)
recommendations = engine.get_recommendations(
    user_mood="feeling happy",
    books=books,
    top_k=5
)
```

### Train Custom Model

```bash
# Train on your dataset (uses 1000 books by default for speed)
python train_sentiment_model.py

# Train on more books
python train_sentiment_model.py 5000 5  # 5000 books, 5 epochs

# Use your trained model
from sentiment_analyzer import EmotionAnalyzer
analyzer = EmotionAnalyzer(model_name="./trained_book_sentiment_model")
```

### Integration with Django/Flask

```python
# In your views/routes:
from sentiment_analyzer import RecommendationEngine

# Initialize once at startup
with open('books_dataset_5000.json', 'r') as f:
    BOOKS = json.load(f)

engine = RecommendationEngine()
engine.analyze_dataset(BOOKS)  # Pre-analyze

# In your API endpoint:
def get_mood_recommendations(request):
    user_mood = request.POST.get('mood')
    
    recommendations = engine.get_recommendations(
        user_mood=user_mood,
        books=BOOKS,
        top_k=5,
        complementary_mode=True
    )
    
    return JsonResponse({'recommendations': recommendations})
```

## Testing

```bash
# Run comprehensive test suite
python test_sentiment_analyzer.py

# Tests include:
# - Emotion detection accuracy
# - Multi-mood recognition
# - Scoring calculations
# - Explanation generation
# - End-to-end integration
```

## Output Format

Each recommendation includes:

```python
{
    'book_id': 'unique_identifier',
    'title': 'Book Title',
    'author': 'Author Name',
    'genres': ['Genre1', 'Genre2'],
    'sentiment_score': 0.87,  # Match score 0-1
    'recommendation_reason': 'Detailed explanation...',
    'book_emotions': {'joy': 0.8, 'calm': 0.6},
    'average_rating': 4.5
}
```

## Performance

- **Analysis Speed**: ~5000 books in 20-30 minutes (first time)
- **Recommendation Latency**: < 2 seconds (with cache)
- **Memory Usage**: < 2GB RAM
- **Model Size**: ~450MB (transformer models)
- **Accuracy**: 80%+ mood-book alignment (manual evaluation)

## Configuration

### Change Models

```python
# Use different emotion detection model
from sentiment_analyzer import EmotionAnalyzer
analyzer = EmotionAnalyzer(
    model_name="distilbert-base-uncased-finetuned-sst-2-english"
)

# Use different embedding model
from sentiment_analyzer import SentimentScorer
scorer = SentimentScorer()
scorer.embedding_model = SentenceTransformer('all-mpnet-base-v2')
```

### Adjust Scoring Weights

Edit `SentimentScorer.calculate_match_score()`:
```python
final_score = (
    0.5 * emotion_sim +      # Change from 0.4
    0.3 * semantic_sim +     # Change from 0.4
    0.2 * complementary_score
)
```

## Troubleshooting

**Q: "transformers not installed" error**  
A: Install dependencies: `pip install transformers torch`

**Q: Slow first-time analysis**  
A: Models download ~450MB. Subsequent runs use cached models.

**Q: Out of memory**  
A: Reduce batch size or use smaller model (distilbert instead of roberta)

**Q: Poor recommendations**  
A: Try pre-analyzing dataset with `engine.analyze_dataset()` for better results

## Files

- `sentiment_analyzer.py` - Main module (all core classes)
- `example_usage.py` - Usage examples and demonstrations
- `train_sentiment_model.py` - Model training pipeline
- `test_sentiment_analyzer.py` - Comprehensive test suite
- `export_books_dataset.py` - Dataset generation from database
- `requirements.txt` - Python dependencies
- `books_dataset_5000.json` - 5000 books dataset (generated)

## Next Steps

1. **Integrate with your app**: Use `RecommendationEngine` in your backend
2. **Train custom model**: Fine-tune on your specific book collection
3. **Add features**: User preferences, reading history, collaborative filtering
4. **Optimize**: GPU acceleration, model quantization, batch processing
5. **Expand**: Multi-language support, audio books, articles

## License

This module is part of the Readwise book recommendation system.

## Support

For issues or questions, see the test suite for usage patterns or check the example scripts.

---

**Built with**: transformers, sentence-transformers, PyTorch, scikit-learn  
**Models**: RoBERTa, DistilBERT, Sentence-Transformers  
**Architecture**: Modular, scalable, production-ready

```
