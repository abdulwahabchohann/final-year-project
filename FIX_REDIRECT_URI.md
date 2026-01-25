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
GOOGLE_CLIENT_SECRET=your-client-secret
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
Agar `http://127.0.0.1:8000` se access kar rahe hain, to Google login bhi wahi se karein.

## Why This Happens:
- Google OAuth redirect URI ko EXACT match chahiye
- `localhost` aur `127.0.0.1` technically same hain but Google unhein different treat karta hai
- Isliye dono add karna safe hai

