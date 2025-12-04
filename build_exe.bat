\
        @echo off
        REM Build a single-file exe using PyInstaller
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller
        REM Include tiktok_cookies.json and config.ini as data files if necessary
        pyinstaller --onefile --noconsole --add-data "config.ini;." --add-data "tiktok_cookies.json;." tiktok_collector.py

        echo Build complete. Check the `dist` folder for tiktok_collector.exe
        pause
