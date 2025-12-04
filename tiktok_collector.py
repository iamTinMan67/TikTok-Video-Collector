"""TikTok Collector — main script (TikTokApi + OpenAI tagging)"""
import os
import json
import re
import time
import sqlite3
import asyncio
import configparser
from yt_dlp import YoutubeDL
from TikTokApi import TikTokApi
from ai_tagging import tag_video
from tqdm import tqdm

# Load config
cfg = configparser.ConfigParser()
cfg.read('config.ini')
BASE_DIR = cfg['DEFAULT'].get('BASE_DIR', 'TikTok_Downloads')
HISTORY_FILE = cfg['DEFAULT'].get('HISTORY_FILE', 'download_history.json')
USE_AI = cfg['DEFAULT'].getboolean('USE_AI', True)
CATALOG_DB = cfg['DEFAULT'].get('CATALOG_DB', 'catalog.db')
COOKIES_FILE = cfg['DEFAULT'].get('TIKTOK_COOKIES', 'tiktok_cookies.json')
MAX_PER_FOLDER = cfg['DEFAULT'].getint('TIKTOKAPI_MAX_PER_FOLDER', 500)
TIKTOK_USERNAME = cfg['DEFAULT'].get('TIKTOK_USERNAME', '').strip()
EXPORT_JSON = cfg['DEFAULT'].get('EXPORT_JSON', 'user_data_tiktok.json')

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

# Download using yt-dlp
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

def scrape_from_export(export_path: str = EXPORT_JSON) -> dict:
    """
    Read TikTok's official user data export JSON and pull out all video links.

    We treat them as a single logical collection called 'Export'.
    """
    if not os.path.exists(export_path):
        raise FileNotFoundError(
            f"Export JSON not found: {export_path}. Put your TikTok export JSON there "
            "or update EXPORT_JSON in config.ini."
        )

    with open(export_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    urls_with_dates: list[tuple[str, str | None]] = []

    def walk(node):
        if isinstance(node, dict):
            link = node.get("Link")
            if isinstance(link, str) and (
                "tiktokv.com/share/video" in link or "/video/" in link
            ):
                urls_with_dates.append((link, node.get("Date")))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)

    # Deduplicate by video id while keeping first seen URL
    seen_ids = set()
    final_urls: list[str] = []
    for url, _date in urls_with_dates:
        vid = extract_video_id(url)
        if not vid or vid in seen_ids:
            continue
        seen_ids.add(vid)
        final_urls.append(url)

    return {"Export": final_urls}

# Simple SQLite catalog (optional)
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
    history = load_history()
    # Use local export JSON instead of live TikTokApi (more stable, no bot detection).
    collections = scrape_from_export()

    conn = init_catalog()
    cur = conn.cursor()

    total_new = 0
    for col_name, videos in collections.items():
        folder = os.path.join(BASE_DIR, safe(col_name))
        os.makedirs(folder, exist_ok=True)

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

                # Save metadata next to files
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
    print('Done. New downloads:', total_new)

if __name__ == '__main__':
    main()
