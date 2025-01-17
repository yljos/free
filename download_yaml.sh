#!/bin/zsh

# 检查 web.txt 是否存在
if [[ ! -f "web.txt" ]]; then
  echo "Error: web.txt not found!"
  exit 1
fi

# 读取 web.txt 中的 URL
url=$(cat web.txt)

# 检查 URL 是否为空
if [[ -z "$url" ]]; then
  echo "Error: URL in web.txt is empty!"
  exit 1
fi

# 下载文件并保存为 a.yaml
output_file="a.yaml"
echo "Downloading $url to $output_file..."
curl -A "clash verge" -o "$output_file" "$url"

# 检查下载是否成功
if [[ $? -eq 0 ]]; then
  echo "Downloaded $url successfully to $output_file."
else
  echo "Failed to download $url."
  exit 1
fi

