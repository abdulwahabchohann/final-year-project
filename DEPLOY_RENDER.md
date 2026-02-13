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
python manage.py shell -c "from django.contrib.sites.models import Site; Site.objects.update_or_create(id=1, defaults={'domain':'<service>.onrender.com','name':'final-year-project'})"
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
