"""
Verify Google OAuth configuration matches between .env and what should be in Google Cloud Console
"""
import os
from pathlib import Path

# Load .env file
env_file = Path('.env')
if env_file.exists():
    content = env_file.read_text(encoding='utf-8')
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Get values
client_id = os.getenv('GOOGLE_CLIENT_ID', '')
client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')
redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', '')
site_base = os.getenv('SITE_BASE_URL', 'http://localhost:8000').rstrip('/')

if not redirect_uri:
    redirect_uri = f'{site_base}/accounts/oauth2callback/'

print("=" * 70)
print("GOOGLE OAUTH CONFIGURATION VERIFICATION")
print("=" * 70)

print(f"\n✓ Configuration from .env file:")
print(f"  Client ID: {client_id[:20]}..." if len(client_id) > 20 else f"  Client ID: {client_id}")
print(f"  Client Secret: {'***' + client_secret[-5:] if len(client_secret) > 5 else '***'}")
print(f"  Redirect URI: {redirect_uri}")

print(f"\n✓ What to verify in Google Cloud Console:")
print(f"  1. Go to: https://console.cloud.google.com/apis/credentials")
print(f"  2. Find the OAuth 2.0 Client ID that matches:")
print(f"     Client ID: {client_id[:20]}..." if len(client_id) > 20 else f"     Client ID: {client_id}")
print(f"  3. In that client, check 'Authorized redirect URIs' contains:")
print(f"     → {redirect_uri}")
print(f"     → {redirect_uri.replace('localhost', '127.0.0.1')}")

print(f"\n✓ Quick Checklist:")
checks = []
checks.append(("Client ID in .env", bool(client_id)))
checks.append(("Client Secret in .env", bool(client_secret)))
checks.append(("Redirect URI in .env", bool(redirect_uri) or redirect_uri == f'{site_base}/accounts/oauth2callback/'))

for check_name, status in checks:
    status_icon = "✓" if status else "✗"
    print(f"  {status_icon} {check_name}")

print(f"\n✓ Next Steps:")
print(f"  1. Open Google Cloud Console")
print(f"  2. Go to APIs & Services > Credentials")
print(f"  3. Click on your OAuth 2.0 Client ID")
print(f"  4. Add this EXACT URI to 'Authorized redirect URIs':")
print(f"     {redirect_uri}")
print(f"  5. Also add: {redirect_uri.replace('localhost', '127.0.0.1')}")
print(f"  6. Click SAVE")
print(f"  7. Wait 1-2 minutes")
print(f"  8. Try logging in again")

print("\n" + "=" * 70)

