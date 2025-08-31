import json
from deepdiff import DeepDiff
import yaml
import os
import sys

f1 = "0.json"
f2 = "1.json"

def print_diff(diff):
    import json
    print(json.dumps(diff, indent=2, ensure_ascii=False))

def compare_json(file1, file2):
    with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
        obj1 = json.load(f1)
        obj2 = json.load(f2)
    diff = DeepDiff(obj1, obj2, ignore_order=True)
    if not diff:
        print(f"{file1} 和 {file2} 内容完全一致（忽略格式和顺序）")
    else:
        print(f"{file1} 和 {file2} 内容有如下不同：")
        print_diff(diff)

def compare_yaml(file1, file2):
    with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
        obj1 = yaml.safe_load(f1)
        obj2 = yaml.safe_load(f2)
    diff = DeepDiff(obj1, obj2, ignore_order=True)
    if not diff:
        print(f"{file1} 和 {file2} YAML 内容完全一致（忽略格式和顺序）")
    else:
        print(f"{file1} 和 {file2} YAML 内容有如下不同：")
        print_diff(diff)

def auto_compare(file1, file2):
    ext1 = os.path.splitext(file1)[1].lower()
    ext2 = os.path.splitext(file2)[1].lower()
    if ext1 == ext2:
        if ext1 in ['.json']:
            compare_json(file1, file2)
        elif ext1 in ['.yaml', '.yml']:
            compare_yaml(file1, file2)
        else:
            print(f"暂不支持的文件类型: {ext1}")
    else:
        print(f"文件类型不一致: {file1}({ext1}) vs {file2}({ext2})")

if __name__ == "__main__":
    if len(sys.argv) == 3:
        auto_compare(sys.argv[1], sys.argv[2])
    else:
        auto_compare(f1, f2)
    # 示例：auto_compare('a.yaml', 'b.yaml')