import yaml

# 加载 YAML 文件内容
def load_yaml(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

# 保存 YAML 文件内容
def save_yaml(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        yaml.dump(data, file, allow_unicode=True, sort_keys=False)

# 主逻辑
def merge_proxies(a_file, b_file, output_file):
    # 加载 a.yaml 和 b.yaml
    a_data = load_yaml(a_file)
    b_data = load_yaml(b_file)

    # 检查并提取 proxies 字段
    if "proxies" in a_data:
        b_data["proxies"] = a_data["proxies"]
    else:
        print("Error: 'proxies' field not found in a.yaml")
        return

    # 保存合并后的文件
    save_yaml(output_file, b_data)
    print(f"Proxies from {a_file} have been successfully merged into {b_file}. Output saved as {output_file}.")

# 输入文件和输出文件路径
a_yaml_path = "a.yaml"
b_yaml_path = "b.yaml"
output_yaml_path = "config.yaml"

merge_proxies(a_yaml_path, b_yaml_path, output_yaml_path)
