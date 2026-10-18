@echo off
echo Starting Cloudflare Tunnel for LinkPulse...
echo Flask should be running on http://127.0.0.1:5000
echo.
.\cloudflared.exe tunnel --url http://127.0.0.1:5000
pause
