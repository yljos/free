#!/bin/bash

# 检查并安装 dos2unix 如果它尚未安装
if ! command -v dos2unix &> /dev/null; then
  echo "dos2unix 未找到，正在安装..."
  sudo pacman -S dos2unix
fi

# 使用 find 命令递归查找所有 .sh 文件并转换为 Unix 格式
find . -type f -name "*.sh" -exec dos2unix {} \;

echo "所有 .sh 文件已转换为 Unix 格式 (LF)。"
