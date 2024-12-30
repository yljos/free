@echo off

:: 设置下载地址和保存路径
set download_url=http://nas:9999/config.json
set save_path=d:\sing-box
set sing_box_path=d:\sing-box\sing-box.exe

:: 使用 PowerShell 下载文件
powershell -Command "Invoke-WebRequest '%download_url%' -OutFile '%save_path%\config.json'"

:: 启动 sing-box 程序，指定完整路径
"%sing_box_path%" -D "%save_path%" run -c config.json
