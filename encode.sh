#!/bin/bash

# URL编码函数
encode_url() {
    cat "$1" | tr -d '\r' | python -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip()), end='')"
}

# 检查源文件
if [ ! -f "0.txt" ]; then
    echo "错误：找不到源文件 0.txt"
    exit 1
fi

# 生成 singbox URL (使用LF)
printf "http://nas:5000/" > singbox.txt
encode_url "0.txt" >> singbox.txt
printf "\n" >> singbox.txt

# 生成 clash URL (使用LF) 
printf "https://clash.suckless.top:8443/" > clash.txt
encode_url "0.txt" >> clash.txt
printf "\n" >> clash.txt

# 验证文件格式
echo "=== 文件格式检查 ==="
file singbox.txt
file clash.txt

# 显示结果
printf "\n=== Singbox URL ===\n"
cat singbox.txt
printf "\n=== Clash URL ===\n"
cat clash.txt

