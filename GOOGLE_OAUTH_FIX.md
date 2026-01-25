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
