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
