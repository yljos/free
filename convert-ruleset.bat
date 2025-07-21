@echo off
chcp 65001 >nul
echo.
echo === Converting JSON to SRS format ===

.\sing-box.exe rule-set compile proxy.json
.\sing-box.exe rule-set compile direct.json
.\sing-box.exe rule-set compile direct-ip.json
.\sing-box.exe rule-set compile pikpak-download.json
.\sing-box.exe rule-set compile direct-cf.json

echo JSON files conversion completed

echo.
echo === Converting YAML to MRS format ===
.\mihomo.exe convert-ruleset domain yaml proxy.yaml proxy.mrs
.\mihomo.exe convert-ruleset domain yaml direct.yaml direct.mrs
.\mihomo.exe convert-ruleset ipcidr yaml direct-ip.yaml direct-ip.mrs
.\mihomo.exe convert-ruleset domain yaml direct-cf.yaml direct-cf.mrs

echo YAML files conversion completed

timeout /t 3 >nul
exit