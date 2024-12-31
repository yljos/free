@echo off

:: 设置文件路径
set web_file=d:\sing-box\web.txt
set save_path=d:\sing-box
set sing_box_path=d:\sing-box\sing-box.exe

:: 从 web.txt 文件中读取下载地址
for /f "tokens=*" %%i in (%web_file%) do set download_url=%%i

:: 使用 PowerShell 下载文件
powershell -Command "Invoke-WebRequest '%download_url%' -OutFile '%save_path%\config.json'"

:: 启动 sing-box 程序，指定完整路径
"%sing_box_path%" -D "%save_path%" run -c config.json

