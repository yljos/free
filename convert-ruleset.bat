@echo off
chcp 65001 >nul
echo.
echo === Converting JSON to SRS format ===

.\sing-box.exe rule-set compile proxy.json
.\sing-box.exe rule-set compile direct.json
.\sing-box.exe rule-set compile pass-ip.json
.\sing-box.exe rule-set compile direct-ip.json
.\sing-box.exe rule-set compile pikpak-download.json

echo JSON files conversion completed


timeout /t 3 >nul
exit