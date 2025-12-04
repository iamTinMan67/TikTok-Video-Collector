\
        @echo off
        REM Sets up a Windows Scheduled Task to run the TikTok Collector daily at 09:00
        REM Edit the time below if needed.

        set TASKNAME=TikTokCollectorDaily
        set SCRIPT="%~dp0\tiktok_collector.py"
        set PYTHON=%~dp0\venv\Scripts\python.exe

        REM If you want to use system python, comment the PYTHON line above and set to python path:
        set PYTHON=python

        schtasks /Create /SC DAILY /TN "%TASKNAME%" /TR "%PYTHON% %SCRIPT%" /ST 09:00 /F
        echo Scheduled Task "%TASKNAME%" created to run daily at 09:00.
        pause
