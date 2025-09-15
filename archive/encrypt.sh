#!/usr/bin/env bash

# 使用 find 命令递归查找所有 .sh 文件
find . -type f -name "*.sh" | while read -r file; do
	# 提取文件名（不含后缀）
	base_name=$(basename "$file" .sh)
	# 获取文件所在目录
	dir_name=$(dirname "$file")
	# 使用 shc 对脚本进行加密并生成可执行文件，允许运行时移植
	shc -r -f "$file" -o "$dir_name/$base_name"
	# 删除生成的 .x.c 文件
	rm "$file.x.c"
done
