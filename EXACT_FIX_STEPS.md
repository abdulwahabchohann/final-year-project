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

