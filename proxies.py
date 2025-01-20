import yaml
import os

def load_yaml(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} not found")
    with open(filename, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

class ProxiesDumper(yaml.SafeDumper):
    def represent_dict(self, data):
        return self.represent_mapping('tag:yaml.org,2002:map', data, flow_style=False)
    
    def represent_list(self, data):
        # 将 proxies 数组中的元素设置为 flow 格式
        return self.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

def save_yaml(filename, data):
    ProxiesDumper.add_representer(dict, ProxiesDumper.represent_dict)
    ProxiesDumper.add_representer(list, ProxiesDumper.represent_list)
    
    with open(filename, "w", encoding="utf-8") as file:
        yaml.dump(data, file, Dumper=ProxiesDumper, allow_unicode=True, sort_keys=False)

def merge_proxies(a_file, b_file, output_file):
    try:
        # 加载配置文件
        a_data = load_yaml(a_file)
        b_data = load_yaml(b_file)

        # 验证数据格式
        if not isinstance(a_data, dict) or not isinstance(b_data, dict):
            raise ValueError("Invalid YAML format - root must be a dictionary")

        # 检查并合并 proxies 字段
        if "proxies" not in a_data:
            raise KeyError("'proxies' field not found in a.yaml")
            
        # 保留b文件中原有的proxies(如果存在)
        if "proxies" in b_data:
            print(f"Warning: Overwriting existing proxies in {b_file}")
            
        # 设置新的 proxies
        b_data["proxies"] = a_data["proxies"]

        # 保存合并后的文件
        save_yaml(output_file, b_data)
        print(f"Proxies from {a_file} have been successfully merged into {b_file}. Output saved as {output_file}.")

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    a_yaml_path = "a.yaml"
    b_yaml_path = "b.yaml" 
    output_yaml_path = "config.yaml"

    merge_proxies(a_yaml_path, b_yaml_path, output_yaml_path)
