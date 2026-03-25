"""
Diagnostic script to check Google OAuth redirect URI configuration
"""
import os
from pathlib import Path

# Load .env file manually
env_file = Path('.env')
if env_file.exists():
    content = env_file.read_text(encoding='utf-8')
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Get configuration
site_base = os.getenv('SITE_BASE_URL', 'http://localhost:8000').rstrip('/')
redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', f'{site_base}/accounts/oauth2callback/')
client_id = os.getenv('GOOGLE_CLIENT_ID', '')
client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')

print("=" * 70)
print("GOOGLE OAUTH REDIRECT URI DIAGNOSTIC")
print("=" * 70)

print(f"\n1. Current Configuration:")
print(f"   SITE_BASE_URL: {site_base}")
print(f"   GOOGLE_REDIRECT_URI: {redirect_uri}")
print(f"   GOOGLE_CLIENT_ID: {'✓ Set' if client_id else '✗ NOT SET'}")
print(f"   GOOGLE_CLIENT_SECRET: {'✓ Set' if client_secret else '✗ NOT SET'}")

print(f"\n2. EXACT Redirect URI being sent to Google:")
print(f"   {redirect_uri}")

print(f"\n3. What to register in Google Cloud Console:")
print(f"   You MUST register EXACTLY this URI (copy-paste it):")
print(f"   → {redirect_uri}")

# Check for common variations
print(f"\n4. Also register these alternatives (if applicable):")
if 'localhost' in redirect_uri:
    alt_uri = redirect_uri.replace('localhost', '127.0.0.1')
    print(f"   → {alt_uri}")
elif '127.0.0.1' in redirect_uri:
    alt_uri = redirect_uri.replace('127.0.0.1', 'localhost')
    print(f"   → {alt_uri}")

# Check for common issues
print(f"\n5. Common Issues to Check:")
issues = []

if not redirect_uri.endswith('/'):
    issues.append("   ⚠ Redirect URI should end with '/'")
if redirect_uri.startswith('https://localhost'):
    issues.append("   ⚠ Using https://localhost (should be http://)")
if ' ' in redirect_uri:
    issues.append("   ⚠ Redirect URI contains spaces (should not)")
if redirect_uri != redirect_uri.strip():
    issues.append("   ⚠ Redirect URI has leading/trailing whitespace")

if not issues:
    print("   ✓ No obvious issues detected")
else:
    for issue in issues:
        print(issue)

print(f"\n6. Step-by-Step Fix Instructions:")
print(f"   a) Go to: https://console.cloud.google.com/apis/credentials")
print(f"   b) Click on your OAuth 2.0 Client ID")
print(f"   c) Scroll to 'Authorized redirect URIs'")
print(f"   d) Click '+ ADD URI'")
print(f"   e) Paste EXACTLY: {redirect_uri}")
print(f"   f) If using localhost, also add: {redirect_uri.replace('localhost', '127.0.0.1')}")
print(f"   g) Click 'SAVE'")
print(f"   h) Wait 1-2 minutes for changes to propagate")
print(f"   i) Try logging in again")

print(f"\n7. Important Notes:")
print(f"   • The URI must match EXACTLY (case-sensitive, including trailing slash)")
print(f"   • No extra spaces before or after")
print(f"   • Use http:// (not https://) for localhost")
print(f"   • Changes in Google Cloud Console can take 1-2 minutes to take effect")
print(f"   • Make sure you're editing the correct OAuth client (check Client ID matches)")

print("\n" + "=" * 70)

