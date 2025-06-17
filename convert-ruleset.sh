#!/bin/bash

echo "===== 开始执行所有规则转换 ====="

# 第一部分：JSON到SRS格式转换
echo -e "\n>>> 执行JSON到SRS格式转换..."
./sing-box rule-set compile proxy.json
./sing-box rule-set compile direct.json
./sing-box rule-set compile pass-ip.json
./sing-box rule-set compile direct-ip.json
./sing-box rule-set compile pikpak-download.json
echo "JSON文件转换完成"

# # 第二部分：YAML到MRS格式转换
# echo -e "\n>>> 执行YAML到MRS格式转换..."
# ./mihomo convert-ruleset "domain" yaml "proxy.yaml" "proxy.mrs"
# ./mihomo convert-ruleset "domain" yaml "direct.yaml" "direct.mrs"
# ./mihomo convert-ruleset "ipcidr" yaml "direct-ip.yaml" "direct-ip.mrs"
# echo "YAML文件转换完成"

echo -e "\n===== 所有转换操作已完成！ ====="