# TikTok Collector (TikTokApi + OpenAI)

Local tool to download newly-bookmarked TikTok videos into folders that mirror your TikTok Collections, plus OpenAI auto-tagging.

## Quick setup (Windows)

1. Install Python 3.10+ from https://www.python.org
2. Extract the `TikTokCollector` folder somewhere (e.g. `C:\Tools\TikTokCollector`).
3. Open a PowerShell or CMD and run:

   ```powershell
   cd C:\Tools\TikTokCollector
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   python -m playwright install
   ```

4. Export your TikTok cookies once (instructions below) and save them as `tiktok_cookies.json` in the project folder.

5. Set your OpenAI API key (required for auto-tagging):

   ```powershell
   setx OPENAI_API_KEY "your_api_key_here"
   ```

6. Configure `config.ini` if you want to change model or folders.

7. Run the script directly (recommended for first tests):

   ```powershell
   python tiktok_collector.py
   ```

8. Optional: build a single-file EXE (requires PyInstaller):

   ```powershell
   pip install pyinstaller
   build_exe.bat
   ```

## How to export cookies (one-time)
- Use a browser cookie export extension that can export JSON compatible with TikTokApi (or use Playwright to grab cookies once). Save the cookies JSON as `tiktok_cookies.json` in project root.

## Files created automatically
- `download_history.json` — record of downloaded video IDs and their collection
- `TikTok_Downloads/` — base folder where videos are saved
- `catalog.db` — SQLite file with metadata

## Notes & Safety
- This tool downloads videos to your PC for personal archival and analysis. Respect creator rights and platform policies. Do not redistribute copyrighted content without permission.
- Keep your `download_history.json` safe to prevent re-downloading duplicates.
