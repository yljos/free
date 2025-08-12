import requests
import base64
import yaml
import json
import os
from urllib.parse import urlparse, parse_qs
import re

def fetch_and_decode_nodes(url):
    """
    从指定URL获取内容，进行base64解码，返回节点列表
    """
    try:
        # 设置Firefox User-Agent（恢复之前能正常工作的设置）
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0'
        }
        
        # 发送请求获取内容（启用证书验证）
        response = requests.get(url, headers=headers, timeout=30, verify=True)
        response.raise_for_status()
        
        # 获取响应内容
        content = response.text.strip()
        
        # 使用URL安全的base64解码
        try:
            decoded_content = base64.urlsafe_b64decode(content + '===').decode('utf-8')
            print(f"✅ 成功URL安全Base64解码，长度: {len(decoded_content)}")
        except Exception as e:
            print(f"URL安全Base64解码失败: {e}")
            print("⚠️ 解码失败，使用原始内容")
            decoded_content = content
        
        # 解析节点 - 假设是订阅链接格式
        nodes = []
        lines = decoded_content.strip().split('\n')
        
        total_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
        print(f"找到 {total_lines} 行非空内容")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith('#'):
                # 处理不同协议的节点
                if line.startswith(('vless://', 'ss://', 'hysteria2://', 'vmess://', 'trojan://')):
                    print(f"正在解析第 {i+1} 行: {line[:50]}...")
                    node_info = parse_node(line)
                    if node_info:
                        nodes.append(node_info)
                        print(f"  ✓ 成功解析: {node_info['name']}")
                    else:
                        print(f"  ✗ 解析失败")
                else:
                    print(f"跳过不支持的协议: {line[:30]}...")
        
        print(f"总共成功解析 {len(nodes)} 个节点")
        return nodes
    
    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return []
    except Exception as e:
        print(f"处理失败: {e}")
        return []

def parse_node(node_url):
    """
    解析单个节点URL，返回节点信息
    """
    try:
        if node_url.startswith('vless://'):
            return parse_vless(node_url)
        elif node_url.startswith('ss://'):
            return parse_shadowsocks(node_url)
        elif node_url.startswith('hysteria2://'):
            return parse_hysteria2(node_url)
        elif node_url.startswith('vmess://'):
            print(f"VMess协议暂不支持，跳过: {node_url[:50]}...")
            return None
        elif node_url.startswith('trojan://'):
            print(f"Trojan协议暂不支持，跳过: {node_url[:50]}...")
            return None
        else:
            print(f"未知协议类型: {node_url[:50]}...")
            return None
    except Exception as e:
        print(f"解析节点失败 [{node_url[:30]}...]: {e}")
        return None

def parse_vless(vless_url):
    """解析VLESS节点"""
    try:
        # 解析URL
        parsed = urlparse(vless_url)
        query = parse_qs(parsed.query)
        
        # 从fragment获取节点名称
        node_name = parsed.fragment if parsed.fragment else 'VLESS节点'
        # URL解码节点名称
        import urllib.parse
        node_name = urllib.parse.unquote(node_name)
        
        # 检查必要参数
        if not parsed.hostname or not parsed.port or not parsed.username:
            print(f"VLESS节点缺少必要信息: server={parsed.hostname}, port={parsed.port}, uuid={parsed.username}")
            return None
        
        # 基础配置
        node_config = {
            'name': node_name,
            'type': 'vless',
            'server': parsed.hostname,
            'port': parsed.port or 443,
            'uuid': parsed.username,
            'udp': True,
            'packet-encoding': 'xudp',
            'flow': query.get('flow', [''])[0],
            'network': query.get('type', ['tcp'])[0],
            'tls': query.get('security', [''])[0] in ['tls', 'reality'],
            'client-fingerprint': 'chrome',
            'skip-cert-verify': False,
        }
        
        # TLS相关配置
        security = query.get('security', [''])[0]
        if security == 'reality':
            node_config['reality-opts'] = {
                'public-key': query.get('pbk', [''])[0],
                'short-id': query.get('sid', [''])[0],
            }
            node_config['servername'] = query.get('sni', [''])[0]
        elif security == 'tls':
            node_config['servername'] = query.get('sni', [''])[0]
        
        # 传输协议相关配置
        network_type = query.get('type', ['tcp'])[0]
        
        if network_type == 'ws':
            node_config['ws-opts'] = {
                'path': query.get('path', ['/'])[0],
                'headers': {
                    'Host': query.get('host', [''])[0]
                }
            }
        elif network_type == 'grpc':
            node_config['grpc-opts'] = {
                'grpc-service-name': query.get('serviceName', [''])[0]
            }
        elif network_type == 'tcp':
            if query.get('headerType', [''])[0] == 'http':
                node_config['http-opts'] = {
                    'method': 'GET',
                    'path': query.get('path', ['/'])[0].split(','),
                    'headers': {
                        'Host': query.get('host', [''])[0].split(',')
                    }
                }
        
        # 清理空值
        cleaned_config = {}
        for key, value in node_config.items():
            if value or value == 0 or value is False:
                cleaned_config[key] = value
        
        print(f"成功解析VLESS节点: {node_name} - {parsed.hostname}:{parsed.port}")
        return cleaned_config
        
    except Exception as e:
        print(f"解析VLESS节点失败 [{vless_url[:50]}...]: {e}")
        return None

def parse_shadowsocks(ss_url):
    """解析Shadowsocks节点"""
    try:
        # 解析SS URL
        parsed = urlparse(ss_url)
        
        # 获取节点名称
        node_name = parsed.fragment if parsed.fragment else 'SS节点'
        # URL解码节点名称
        import urllib.parse
        node_name = urllib.parse.unquote(node_name)
        
        # 解码用户信息部分
        user_info = parsed.username
        try:
            # 尝试base64解码
            decoded_user = base64.b64decode(user_info + '==').decode('utf-8')  # 添加padding以防解码失败
            if ':' in decoded_user:
                method, password = decoded_user.split(':', 1)
            else:
                # 如果解码后没有冒号，说明格式不对，使用原始数据
                method, password = user_info.split(':', 1)
        except:
            # 如果不是base64编码，直接分割
            if ':' in user_info:
                method, password = user_info.split(':', 1)
            else:
                print(f"无法解析SS用户信息: {user_info}")
                return None
        
        # 获取服务器和端口
        server = parsed.hostname
        port = parsed.port
        
        if not server or not port:
            print(f"SS节点缺少必要信息: server={server}, port={port}")
            return None
        
        # 基础配置
        node_config = {
            'name': node_name,
            'type': 'ss',
            'server': server,
            'port': port,
            'cipher': method,
            'password': password,
            'udp': True
        }
        
        # 处理插件参数
        query_params = parse_qs(parsed.query)
        if 'plugin' in query_params:
            plugin_info = query_params['plugin'][0]
            # 解析插件信息，如 simple-obfs;obfs=http;obfs-host=xxx
            if 'simple-obfs' in plugin_info or 'obfs-local' in plugin_info:
                plugin_parts = plugin_info.split(';')
                obfs_mode = None
                obfs_host = None
                
                for part in plugin_parts:
                    if part.startswith('obfs='):
                        obfs_mode = part.split('=', 1)[1]
                    elif part.startswith('obfs-host='):
                        obfs_host = part.split('=', 1)[1]
                
                if obfs_mode:
                    node_config['plugin'] = 'obfs'
                    node_config['plugin-opts'] = {
                        'mode': obfs_mode
                    }
                    if obfs_host:
                        node_config['plugin-opts']['host'] = obfs_host
        
        print(f"成功解析SS节点: {node_name} - {server}:{port} ({method})")
        return node_config
        
    except Exception as e:
        print(f"解析Shadowsocks节点失败 [{ss_url[:50]}...]: {e}")
        return None

def parse_hysteria2(hy2_url):
    """解析Hysteria2节点"""
    try:
        # 解析URL
        parsed = urlparse(hy2_url)
        query = parse_qs(parsed.query)
        
        # 从fragment获取节点名称
        node_name = parsed.fragment if parsed.fragment else 'Hysteria2节点'
        # URL解码节点名称
        import urllib.parse
        node_name = urllib.parse.unquote(node_name)
        
        # 检查必要参数
        if not parsed.hostname or not parsed.port or not parsed.username:
            print(f"Hysteria2节点缺少必要信息: server={parsed.hostname}, port={parsed.port}, password={parsed.username}")
            return None
        
        # 确定端口配置
        port = parsed.port or 443
        # 根据端口生成端口范围（模拟原始配置的行为）
        if port < 2000:
            ports_range = f"{port//1000*1000}-{(port//1000+1)*1000}"
        elif port < 4000:
            ports_range = f"{port//1000*1000}-{(port//1000+1)*1000}"
        elif port < 6000:
            ports_range = f"{port//1000*1000}-{(port//1000+1)*1000}"
        elif port < 8000:
            ports_range = f"{port//1000*1000}-{(port//1000+1)*1000}"
        else:
            ports_range = f"{port//1000*1000}-{(port//1000+1)*1000}"
        
        # 基础配置
        node_config = {
            'name': node_name,
            'type': 'hysteria2',
            'server': parsed.hostname,
            'ports': ports_range,
            'password': parsed.username,
            'udp': True,
            'skip-cert-verify': query.get('insecure', ['false'])[0] == 'true',
            'up': '50 Mbps',
            'down': '200 Mbps',
            'sni': query.get('sni', [parsed.hostname])[0],
        }
        
        # 可选配置
        if query.get('obfs'):
            node_config['obfs'] = query.get('obfs')[0]
        if query.get('obfs-password'):
            node_config['obfs-password'] = query.get('obfs-password')[0]
        
        # 清理空值
        cleaned_config = {}
        for key, value in node_config.items():
            if value or value == 0 or value is False:
                cleaned_config[key] = value
        
        print(f"成功解析Hysteria2节点: {node_name} - {parsed.hostname}:{port}")
        return cleaned_config
        
    except Exception as e:
        print(f"解析Hysteria2节点失败 [{hy2_url[:50]}...]: {e}")
        return None

def write_to_config_yaml(nodes, config_file='config.yaml'):
    """
    将节点写入config.yaml文件
    """
    try:
        # 创建新的配置
        config = {
            'proxies': nodes
        }
        
        # 写入文件
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2, 
                     default_style=None, sort_keys=False)
        
        print(f"成功写入 {len(nodes)} 个节点到 {config_file}")
        return True
        
    except Exception as e:
        print(f"写入配置文件失败: {e}")
        return False

def main():
    """主函数"""
    # 提示用户输入URL
    url = input("请输入订阅链接URL: ").strip()
    
    if not url:
        print("URL不能为空")
        return
    
    print(f"正在从 {url} 获取内容...")
    
    # 获取并解析节点
    nodes = fetch_and_decode_nodes(url)
    
    if not nodes:
        print("未找到有效节点")
        return
    
    print(f"成功解析 {len(nodes)} 个节点:")
    for i, node in enumerate(nodes, 1):
        print(f"  {i}. {node['name']} ({node['type']})")
    
    # 写入配置文件
    config_file = 'config.yaml'
    
    if write_to_config_yaml(nodes, config_file):
        print("操作完成!")
    else:
        print("操作失败!")

if __name__ == "__main__":
    main()