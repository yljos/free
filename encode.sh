#!/bin/bash
cat 0 > temp.txt
cat temp.txt 
sleep 1
cat temp.txt | python -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip()))" > singbox.txt
# 使用 tr 命令移除可能的回车符，并使用 echo -n 避免添加换行符
echo -n "&app=clashmeta" | tr -d '\r' >> temp.txt 
cat temp.txt
sleep 1
# 使用strip()确保移除所有额外的空白字符
cat temp.txt | python -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip()))" > clash.txt
rm temp.txt

