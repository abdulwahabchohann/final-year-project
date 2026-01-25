# Google OAuth Redirect URI Fix Guide

## Problem: redirect_uri_mismatch Error

This error occurs when the redirect URI in your code doesn't match what's configured in Google Cloud Console.

## Solution Steps:

### Step 1: Add BOTH redirect URIs in Google Cloud Console

Go to: **Google Cloud Console → APIs & Services → Credentials → Your OAuth Client**

In the **"Authorized redirect URIs"** section, add BOTH of these (exactly as shown):

```
http://localhost:8000/accounts/oauth2callback/
http://127.0.0.1:8000/accounts/oauth2callback/
```

**Important Notes:**
- Include the trailing slash `/` at the end
- Use `http://` not `https://` for local development
- Both `localhost` and `127.0.0.1` must be added separately
- Click **"Save"** after adding

### Step 2: Verify your .env file

Make sure your `.env` file has the correct redirect URI. It should match what you're using to access your site:

If accessing via `http://localhost:8000`, use:
```
GOOGLE_REDIRECT_URI=http://localhost:8000/accounts/oauth2callback/
```

If accessing via `http://127.0.0.1:8000`, use:
```
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/accounts/oauth2callback/
```

Or you can leave it empty and let the code use the default (recommended):
```
# Leave GOOGLE_REDIRECT_URI empty to use default
# GOOGLE_REDIRECT_URI=
```

### Step 3: Restart your Django server

After making changes:
1. Stop your Django server (Ctrl+C)
2. Start it again: `python manage.py runserver`
3. Try Google login again

### Step 4: Wait for Google to update (if needed)

Google says: "It may take 5 minutes to a few hours for settings to take effect"

Usually it's instant, but if it still doesn't work, wait a few minutes and try again.

## Common Mistakes to Avoid:

❌ **Wrong:** `http://localhost:8000/accounts/oauth2callback` (missing trailing slash)
✅ **Correct:** `http://localhost:8000/accounts/oauth2callback/` (with trailing slash)

❌ **Wrong:** `https://localhost:8000/accounts/oauth2callback/` (using https for local)
✅ **Correct:** `http://localhost:8000/accounts/oauth2callback/` (using http for local)

❌ **Wrong:** Only adding one URI (localhost OR 127.0.0.1)
✅ **Correct:** Add BOTH localhost AND 127.0.0.1

## Quick Checklist:

- [ ] Added `http://localhost:8000/accounts/oauth2callback/` in Google Console
- [ ] Added `http://127.0.0.1:8000/accounts/oauth2callback/` in Google Console
- [ ] Both URIs have trailing slash `/`
- [ ] Clicked "Save" in Google Console
- [ ] Verified .env file has correct values (or is empty for default)
- [ ] Restarted Django server
- [ ] Tried accessing via the same URL you configured (localhost or 127.0.0.1)





