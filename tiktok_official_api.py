"""TikTok Collector using Official TikTok API (OAuth 2.0 + Data Portability API)

This uses TikTok's official third-party access API, which requires:
1. TikTok Developer account: https://developers.tiktok.com/
2. Registered application with Data Portability API access
3. OAuth 2.0 authorization flow

Setup steps:
1. Create account at https://developers.tiktok.com/
2. Register a new app
3. Add "Data Portability API" product to your app
4. Get Client Key and Client Secret
5. Set redirect URI (e.g., http://localhost:8080/callback)
6. Update config.ini with your credentials
"""

import os
import json
import re
import time
import sqlite3
import configparser
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from yt_dlp import YoutubeDL
from ai_tagging import tag_video
from tqdm import tqdm
import requests

# Load config
cfg = configparser.ConfigParser()
cfg.read('config.ini')
BASE_DIR = cfg['DEFAULT'].get('BASE_DIR', 'TikTok_Downloads')
HISTORY_FILE = cfg['DEFAULT'].get('HISTORY_FILE', 'download_history.json')
USE_AI = cfg['DEFAULT'].getboolean('USE_AI', True)
CATALOG_DB = cfg['DEFAULT'].get('CATALOG_DB', 'catalog.db')

# TikTok OAuth settings
TIKTOK_CLIENT_KEY = cfg['DEFAULT'].get('awa1s9ztranr6fdy', '').strip()
TIKTOK_CLIENT_SECRET = cfg['DEFAULT'].get('ibbdnaAcjkJ5251hL01olnitEeYONR6c', '').strip()
TIKTOK_REDIRECT_URI = cfg['DEFAULT'].get('TIKTOK_REDIRECT_URI', 'http://localhost:8080/callback')
TIKTOK_SCOPE = cfg['DEFAULT'].get('TIKTOK_SCOPE', 'user.info.basic,video.list')  # Add data.portability if available
TOKEN_FILE = cfg['DEFAULT'].get('TOKEN_FILE', 'tiktok_access_token.json')

os.makedirs(BASE_DIR, exist_ok=True)

# Utilities
def safe(name):
    return re.sub(r'[^a-zA-Z0-9 _-]', '', name).strip()

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_history(h):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(h, f, indent=2)

def extract_video_id(url):
    try:
        return url.strip('/').split('/')[-1].split('?')[0]
    except:
        return None

def download_video(url, out_folder):
    ydl_opts = {
        'outtmpl': os.path.join(out_folder, '%(uploader)s - %(id)s - %(title)s.%(ext)s'),
        'format': 'mp4',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def load_access_token():
    """Load saved access token from file."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('access_token'), data.get('expires_at', 0)
    return None, 0

def save_access_token(access_token, expires_in):
    """Save access token to file."""
    expires_at = time.time() + expires_in if expires_in else 0
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'access_token': access_token,
            'expires_at': expires_at,
            'saved_at': time.time()
        }, f, indent=2)

def get_authorization_url():
    """Generate TikTok OAuth authorization URL."""
    if not TIKTOK_CLIENT_KEY:
        raise RuntimeError(
            "TIKTOK_CLIENT_KEY not set in config.ini. "
            "Get it from https://developers.tiktok.com/ after registering your app."
        )
    
    base_url = "https://www.tiktok.com/v2/auth/authorize/"
    params = {
        'client_key': TIKTOK_CLIENT_KEY,
        'scope': TIKTOK_SCOPE,
        'response_type': 'code',
        'redirect_uri': TIKTOK_REDIRECT_URI,
        'state': 'tiktok_collector_auth'
    }
    
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query_string}"

def exchange_code_for_token(auth_code):
    """Exchange authorization code for access token."""
    if not TIKTOK_CLIENT_SECRET:
        raise RuntimeError(
            "TIKTOK_CLIENT_SECRET not set in config.ini. "
            "Get it from https://developers.tiktok.com/ after registering your app."
        )
    
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    data = {
        'client_key': TIKTOK_CLIENT_KEY,
        'client_secret': TIKTOK_CLIENT_SECRET,
        'code': auth_code,
        'grant_type': 'authorization_code',
        'redirect_uri': TIKTOK_REDIRECT_URI
    }
    
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    result = response.json()
    
    if 'data' in result and 'access_token' in result['data']:
        access_token = result['data']['access_token']
        expires_in = result['data'].get('expires_in', 3600)
        save_access_token(access_token, expires_in)
        return access_token
    else:
        raise RuntimeError(f"Failed to get access token: {result}")

class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP server to catch OAuth callback."""
    auth_code = None
    
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/callback':
            query = parse_qs(parsed.query)
            if 'code' in query:
                CallbackHandler.auth_code = query['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"""
                    <html><body>
                    <h1>Authorization successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    </body></html>
                """)
            else:
                error = query.get('error', ['Unknown error'])[0]
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(f"""
                    <html><body>
                    <h1>Authorization failed</h1>
                    <p>Error: {error}</p>
                    </body></html>
                """.encode())
        else:
            self.send_response(404)
            self.end_headers()

def authorize():
    """Run OAuth authorization flow."""
    access_token, expires_at = load_access_token()
    
    if access_token and expires_at > time.time():
        print(f"Using existing access token (expires in {int(expires_at - time.time())} seconds)")
        return access_token
    
    print("Starting OAuth authorization flow...")
    print(f"Opening browser for authorization...")
    
    auth_url = get_authorization_url()
    webbrowser.open(auth_url)
    
    # Start local server to catch callback
    port = urlparse(TIKTOK_REDIRECT_URI).port or 8080
    server = HTTPServer(('localhost', port), CallbackHandler)
    
    print(f"Waiting for authorization callback on http://localhost:{port}/callback")
    print("Please authorize the app in your browser...")
    
    # Wait for callback (timeout after 5 minutes)
    server.timeout = 300
    server.handle_request()
    
    if CallbackHandler.auth_code:
        print("Authorization code received, exchanging for access token...")
        access_token = exchange_code_for_token(CallbackHandler.auth_code)
        print("Access token obtained successfully!")
        return access_token
    else:
        raise RuntimeError("Authorization failed: No code received")

def fetch_saved_videos(access_token):
    """
    Fetch saved/favorite videos using TikTok's official API.
    
    Note: The exact endpoint depends on which API products you have access to.
    This is a template that may need adjustment based on TikTok's current API.
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Try Data Portability API endpoint (if you have access)
    # This endpoint may vary - check TikTok's latest API docs
    api_url = "https://open.tiktokapis.com/v2/research/user/favorites/"
    
    videos = []
    cursor = None
    
    while True:
        params = {
            'max_count': 20
        }
        if cursor:
            params['cursor'] = cursor
        
        try:
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and 'videos' in data['data']:
                for video in data['data']['videos']:
                    video_id = video.get('id')
                    author = video.get('author', {}).get('username', 'unknown')
                    if video_id:
                        url = f"https://www.tiktok.com/@{author}/video/{video_id}"
                        videos.append(url)
                
                # Check for pagination
                if 'has_more' in data['data'] and data['data']['has_more']:
                    cursor = data['data'].get('cursor')
                else:
                    break
            else:
                # Fallback: try alternative endpoint or method
                print("Note: Direct favorites API may not be available.")
                print("You may need to use the Data Portability API differently.")
                print("Check TikTok's API documentation for the correct endpoint.")
                break
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print("API access denied. Make sure:")
                print("1. Your app has 'Data Portability API' product enabled")
                print("2. Your app has been approved by TikTok")
                print("3. You're requesting the correct scopes")
            raise
    
    return videos

def scrape_collections_with_official_api():
    """
    Use TikTok's official API to fetch saved/favorite videos.
    """
    access_token = authorize()
    videos = fetch_saved_videos(access_token)
    
    # Return as a single collection
    return {"Saved": list(dict.fromkeys(videos))}

def init_catalog(db_path=CATALOG_DB):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            collection TEXT,
            file_path TEXT,
            title TEXT,
            tags TEXT,
            summary TEXT,
            downloaded_at TEXT
        )
    ''')
    conn.commit()
    return conn

def main():
    print("TikTok Collector - Official API Mode")
    print("=" * 50)
    
    history = load_history()
    
    try:
        collections = scrape_collections_with_official_api()
    except Exception as e:
        print(f"Error fetching videos: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET are set in config.ini")
        print("2. Register your app at https://developers.tiktok.com/")
        print("3. Add 'Data Portability API' product to your app")
        print("4. Set TIKTOK_REDIRECT_URI to match your app's redirect URI")
        return
    
    conn = init_catalog()
    cur = conn.cursor()
    
    total_new = 0
    for col_name, videos in collections.items():
        folder = os.path.join(BASE_DIR, safe(col_name))
        os.makedirs(folder, exist_ok=True)
        
        print(f"\nFound {len(videos)} videos in '{col_name}'")
        
        for url in tqdm(videos, desc=f'Processing {col_name}'):
            vid = extract_video_id(url)
            if not vid:
                continue
            if vid in history:
                continue
            
            print(f'Downloading new video {vid} into {folder}')
            try:
                download_video(url, folder)
                total_new += 1
                
                # AI tagging (optional)
                tags = []
                title = ''
                summary = ''
                try:
                    if USE_AI:
                        tags, title, summary = tag_video(url)
                except Exception as e:
                    print('AI tagging failed:', e)
                
                # Save metadata
                meta = {
                    'id': vid,
                    'collection': col_name,
                    'url': url,
                    'title': title,
                    'tags': tags,
                    'summary': summary,
                    'downloaded_at': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                with open(os.path.join(folder, f"{vid}.metadata.json"), 'w', encoding='utf-8') as f:
                    json.dump(meta, f, indent=2)
                
                # Insert into sqlite catalog
                cur.execute('INSERT OR REPLACE INTO videos (id, collection, file_path, title, tags, summary, downloaded_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                            (vid, col_name, folder, title, ','.join(tags), summary, meta['downloaded_at']))
                conn.commit()
                
                # update history
                history[vid] = col_name
                save_history(history)
                
            except Exception as e:
                print('Failed to download', url, e)
    
    conn.close()
    print(f'\nDone. New downloads: {total_new}')

if __name__ == '__main__':
    main()

