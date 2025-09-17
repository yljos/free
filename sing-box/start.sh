#!/bin/sh
# 启动脚本 - 安装依赖并运行 Python 应用

echo "正在安装 Python 依赖..."
pip install -r requirements.txt

echo "启动 Python 应用..."
exec python app.py
