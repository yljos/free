# 询问用户选择规则集类型（这个部分保留以便后续逻辑）
Write-Host "请选择规则集类型（输入 1 选择 domain，输入 2 选择 ipcidr）："
$choice = Read-Host

# 根据选择的规则集类型设置备注（不直接用于输出文件名）
if ($choice -eq "1") {
    $RULESET_DESC = "domain"
} elseif ($choice -eq "2") {
    $RULESET_DESC = "ipcidr"
} else {
    Write-Host "无效选择，请输入 1 或 2。"
    exit
}

# 询问用户输入文件名称
Write-Host "请输入输入文件的名称（例如 zidingyi.yaml）："
$INPUT_FILE = Read-Host

# 检查输入文件是否存在
if (-Not (Test-Path $INPUT_FILE)) {
    Write-Host "输入文件不存在，请检查文件名。"
    exit
}

# 自定义输出文件名，根据输入文件名称生成
$OUTPUT_FILE = [System.IO.Path]::ChangeExtension($INPUT_FILE, ".mrs")

# 执行转换
& mihomo convert-ruleset $RULESET_DESC yaml $INPUT_FILE $OUTPUT_FILE

Write-Host "转换完成：$OUTPUT_FILE"
