#!/bin/zsh

# 询问用户选择规则集类型
echo "请选择规则集类型（输入 1 选择 domain，输入 2 选择 ipcidr）："
read choice

# 根据选择的规则集类型设置备注（不直接用于输出文件名）
if [[ "$choice" == "1" ]]; then
    RULESET_DESC="domain"
elif [[ "$choice" == "2" ]]; then
    RULESET_DESC="ipcidr"
else
    echo "无效选择，请输入 1 或 2。"
    exit 1
fi

# 询问用户输入文件名称
echo "请输入输入文件的名称（例如 zidingyi.yaml）："
read INPUT_FILE

# 检查输入文件是否存在
if [[ ! -f "$INPUT_FILE" ]]; then
    echo "输入文件不存在，请检查文件名。"
    exit 1
fi

# 自定义输出文件名，根据输入文件名称生成
OUTPUT_FILE="${INPUT_FILE%.*}.mrs"

# 执行转换（替换为你的具体命令）
mihomo convert-ruleset "$RULESET_DESC" yaml "$INPUT_FILE" "$OUTPUT_FILE"

echo "转换完成：$OUTPUT_FILE"

