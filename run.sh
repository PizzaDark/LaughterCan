#!/bin/bash

# 设置 UTF-8 编码
export LANG=en_US.UTF-8

echo "========================================"
echo "  自动安装脚本 (macOS & Linux)"
echo "========================================"
echo

# ============================================
# 项目配置 (可根据实际项目修改)
# ============================================
PROJECT_NAME="LaughterCan"
GITHUB_USER="PizzaDark"
GITHUB_REPO="$PROJECT_NAME"
REPO_URL="https://github.com/$GITHUB_USER/$GITHUB_REPO.git"
REPO_ZIP_URL="https://github.com/$GITHUB_USER/$GITHUB_REPO/archive/refs/heads/main.zip"
REPO_DIR="$PROJECT_NAME"

# ============================================
# 第一步：检查 Python 3.10+ 环境
# ============================================
echo "[1/5] 正在检查 Python 环境..."

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[错误] 未检测到 Python 环境！"
    echo
    echo "请下载并安装 Python 3.10 或更高版本: https://www.python.org/downloads/"
    echo
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info[0])')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info[1])')

echo "检测到 Python 版本: $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "[错误] Python 版本过低！当前版本: $PYTHON_VERSION，需要 3.10 或更高版本"
    echo "请下载3.10或以上版本: https://www.python.org/downloads/"
    exit 1
fi

echo "[✓] Python 版本符合要求 (需要 3.10+)"
echo

# ============================================
# 第二步：检查 Git 环境
# ============================================
echo "[2/5] 正在检查 Git 环境..."
if ! command -v git &>/dev/null; then
    echo "[提示] 未检测到 Git 环境"
    echo
    echo "正在尝试下载项目压缩包..."
    if command -v curl &>/dev/null && command -v unzip &>/dev/null; then
        curl -L -o project.zip "$REPO_ZIP_URL"
        if [ $? -ne 0 ]; then
            echo "[错误] 下载失败！"
            exit 1
        fi
        unzip -q project.zip
        
        if [ -d "${PROJECT_NAME}-main" ]; then
            mv "${PROJECT_NAME}-main" "$PROJECT_NAME"
        elif [ -d "${PROJECT_NAME}-master" ]; then
            mv "${PROJECT_NAME}-master" "$PROJECT_NAME"
        fi
        
        rm project.zip
        cd "$PROJECT_NAME" || exit 1
    else
        echo "[错误] 未检测到 curl 或 unzip，请先安装 Git、curl 和 unzip 手动下载: ${REPO_ZIP_URL}"
        exit 1
    fi
else
    echo "[✓] Git 环境正常"
    echo
    
    CURRENT_DIR=$(basename "$PWD")
    if [ "$CURRENT_DIR" == "$PROJECT_NAME" ] || [ -d ".git" ] || [ -f "main.py" ]; then
        echo "[提示] 当前已在项目目录中，跳过克隆步骤"
    else
        echo "正在克隆仓库..."
        git clone "$REPO_URL"
        if [ $? -ne 0 ]; then
            echo "[错误] 克隆失败！尝试使用 curl 下载 ZIP 压缩包..."
            if command -v curl &>/dev/null && command -v unzip &>/dev/null; then
                curl -L -o project.zip "$REPO_ZIP_URL"
                unzip -q project.zip
                if [ -d "${PROJECT_NAME}-main" ]; then
                    mv "${PROJECT_NAME}-main" "$PROJECT_NAME"
                fi
                rm project.zip
            else
                echo "[错误] 克隆失败且未找到 curl/unzip。请手动下载。"
                exit 1
            fi
        fi
        cd "$PROJECT_NAME" || exit 1
    fi
fi
echo

# ============================================
# 第三步：创建虚拟环境
# ============================================
echo "[3/5] 正在检查/创建虚拟环境..."
if [ -d ".venv" ]; then
    echo "[提示] 检测到现有虚拟环境"
else
    echo "正在创建虚拟环境..."
    $PYTHON_CMD -m venv .venv
    if [ $? -ne 0 ]; then
        echo "[错误] 虚拟环境创建失败！可能是因为缺少 python3-venv 模块。"
        echo "在 Ubuntu/Debian 上可以使用: sudo apt install python3-venv 安装"
        exit 1
    fi
    echo "[✓] 虚拟环境创建成功"
fi
echo

# ============================================
# 第四步：激活虚拟环境
# ============================================
echo "[4/5] 正在激活虚拟环境..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "[错误] 虚拟环境激活失败！"
    exit 1
fi
echo "[✓] 虚拟环境已激活"
echo

# ============================================
# 第五步：安装依赖
# ============================================
echo "[5/5] 正在安装/更新依赖包..."
if [ ! -f "requirements.txt" ]; then
    echo "[警告] 未找到 requirements.txt 文件！"
    echo "将尝试直接运行程序..."
    echo
else
    echo "使用阿里云镜像源安装依赖，请稍候..."
    pip install pip -i https://mirrors.aliyun.com/pypi/simple/ >/dev/null 2>&1
    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败！"
        echo
        echo "您可以尝试手动执行："
        echo "pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/"
        echo
        exit 1
    fi
    echo "[✓] 依赖安装完成"
    echo
fi

# ============================================
# 运行主程序
# ============================================
echo "========================================"
echo "  环境准备完成，正在启动程序..."
echo "========================================"
echo

if [ ! -f "main.py" ]; then
    echo "[错误] 未找到 main.py 文件！"
    echo
    echo "请确保您在正确的项目目录中运行此脚本。"
    echo
    exit 1
fi

python main.py

# 程序结束后的处理
echo
echo "========================================"
echo "  程序已退出"
echo "========================================"
