#!/bin/bash
cat 0.txt > temp.txt
cat temp.txt | python -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip()))" > singbox.txt
# 使用 tr 命令移除可能的回车符，并使用 echo -n 避免添加换行符
echo -n "&app=clashmeta" | tr -d '\r' >> temp.txt 
# 使用strip()确保移除所有额外的空白字符
cat temp.txt | python -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip()))" > temp2.txt
# 添加基础URL并与编码后的内容合并
echo -n "https://clash.suckless.top:8443/" > clash.txt
cat temp2.txt >> clash.txt
cat singbox.txt
cat clash.txt
rm temp.txt temp2.txt

