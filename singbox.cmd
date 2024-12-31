@echo off

:: 设置 web.txt 文件路径
set web_file=d:\sing-box\web.txt

:: 检查文件是否存在
if not exist "%web_file%" (
    echo 文件 %web_file% 不存在！
    exit /b
)

:: 读取并打印文件内容
echo 正在读取 %web_file% 的内容：
for /f "tokens=*" %%i in (%web_file%) do (
    echo %%i
)
pause
