#!/usr/bin/env bash

# 检查参数
[ $# -ne 2 ] && { echo "用法: <解压密码> <压缩密码>"; exit 1; }

# 保存当前工作目录
CURRENT_DIR=$(pwd)

# 检查0.zip是否存在
[ ! -f "0.zip" ] && { echo "错误: 找不到 0.zip"; exit 1; }

# 创建临时目录
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# 使用unzip解压0.zip到临时目录，使用第一个参数作为密码
unzip -P "$1" -q 0.zip -d "$TEMP_DIR" || { echo "错误: 解压失败，请检查密码是否正确"; exit 1; }

# 读取所有URL并合并
URLS=$(grep -o '[^:]*:.*' "$TEMP_DIR/0.txt" | cut -d' ' -f2)
[ -z "$URLS" ] && { echo "错误: 在解压的文件中找不到URL"; exit 1; }

# 合并所有URL
MERGED_URL=$(echo "$URLS" | tr '\n' '|')

# 读取URL并逐行处理
while IFS=': ' read -r name url || [[ -n "$url" ]]; do
    if [[ -n "$name" && -n "$url" ]]; then
        # 生成 Singbox URL
        echo "$name: https://singbox.202309.xyz/$url" >> "$TEMP_DIR/singbox.txt"
        
        # 生成 Clash URL
        echo "$name: https://clash.202309.xyz/$url" >> "$TEMP_DIR/clash.txt"
    fi
done < "$TEMP_DIR/0.txt"

# 确保文件末尾有换行
printf "\n" >> "$TEMP_DIR/singbox.txt"
printf "\n" >> "$TEMP_DIR/clash.txt"

# 显示结果
printf "\n=== Singbox URL ===\n"
cat "$TEMP_DIR/singbox.txt"
printf "\n=== Clash URL ===\n"
cat "$TEMP_DIR/clash.txt"

# 定义压缩函数
compress_file() {
    local input="$1"
    local output="$2"
    local password="$3"
    
    # 确保输入文件存在
    [ ! -f "$input" ] && { echo "错误: 输入文件 $input 不存在"; return 1; }
    
    # 删除已存在的输出文件（使用完整路径）
    [ -f "$CURRENT_DIR/$output" ] && rm -f "$CURRENT_DIR/$output"
    
    # 在临时目录中压缩文件
    cd "$TEMP_DIR" || return 1
    
    # 使用zip命令创建加密压缩文件
    if ! zip -j -P "$password" "$TEMP_DIR/$output" "$(basename $input)" >/dev/null 2>&1; then
        echo "错误: 压缩 $output 失败"
        echo "详细错误信息:"
        zip -j -P "$password" "$TEMP_DIR/$output" "$(basename $input)" 2>&1
        return 1
    fi
    
    # 将压缩文件移动到当前目录
    mv "$TEMP_DIR/$output" "$CURRENT_DIR/$output" || { echo "错误: 移动文件失败"; return 1; }
    
    return 0
}

# 压缩 Singbox 文件
if ! compress_file "$TEMP_DIR/singbox.txt" "singbox.zip" "$2"; then
    exit 1
fi

# 压缩 Clash 文件
if ! compress_file "$TEMP_DIR/clash.txt" "clash.zip" "$2"; then
    exit 1
fi

# 显示结果
echo "文件已加密保存为 singbox.zip 和 clash.zip"
echo "使用密码 '$2' 可以解压文件"
