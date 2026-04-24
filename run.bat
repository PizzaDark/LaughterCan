@echo off
chcp 65001 >nul
title 笑声罐头 - 自动安装脚本
color 0A

:: ============================================
:: 项目配置 (可根据实际项目修改)
:: ============================================
set "PROJECT_NAME=LaughterCan"
set "GITHUB_USER=PizzaDark"
set "GITHUB_REPO=%PROJECT_NAME%"
set "REPO_URL=https://github.com/%GITHUB_USER%/%GITHUB_REPO%.git"
set "REPO_ZIP_URL=https://github.com/%GITHUB_USER%/%GITHUB_REPO%/archive/refs/heads/main.zip"
set "REPO_DIR=%PROJECT_NAME%"

echo ========================================
echo   自动安装脚本
echo ========================================
echo.

:: ============================================
:: 第一步：检查 Python 3.10+ 环境
:: ============================================
echo [1/5] 正在检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python 环境！
    echo.
    echo 请从以下链接下载并安装 Python 3.10 或更高版本, 按住Ctrl点击或复制到浏览器打开:
    echo https://www.python.org/downloads/
    echo.
    echo 安装时请务必勾选 "Add Python to PATH" 选项！
    echo.
    pause
    exit /b 1
)

:: 获取 Python 版本号
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo 检测到 Python 版本: %PYTHON_VERSION%

:: 检查版本是否符合要求 (3.10+)
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% LSS 3 (
    goto :version_error
)
if %MAJOR% EQU 3 if %MINOR% LSS 10 (
    goto :version_error
)

echo [✓] Python 版本符合要求 (需要 3.10+)
echo.
goto :check_git

:version_error
echo [错误] Python 版本过低！当前版本: %PYTHON_VERSION%，需要 3.10 或更高版本
echo.
echo 请从以下链接下载3.10或以上版本, 按住Ctrl点击或复制到浏览器打开:
echo https://www.python.org/downloads/
echo.
pause
exit /b 1

:: ============================================
:: 第二步：检查 Git 环境
:: ============================================
:check_git
echo [2/5] 正在检查 Git 环境...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 未检测到 Git 环境
    echo.
    echo 您可以选择：
    echo 1. 手动从 GitHub 下载 ZIP 压缩包并解压, 按住Ctrl点击或复制到浏览器打开:
    echo    下载地址: %REPO_ZIP_URL%
    echo.
    echo 2. 或者安装 Git 后重新运行此脚本, 按住Ctrl点击或复制到浏览器打开:
    echo    Git 下载地址: https://git-scm.com/install
    echo.
    echo 如果您已经手动下载并解压了源代码，请按任意键继续...
    pause
    goto :setup_venv
) else (
    echo [✓] Git 环境正常
    echo.
    
    :: 检查当前目录名是否为项目名
    for %%I in (.) do set CURRENT_DIR=%%~nxI
    if "%CURRENT_DIR%"=="%PROJECT_NAME%" (
        echo [提示] 当前已在项目目录中，跳过克隆步骤
        echo.
        goto :setup_venv
    )
    
    :: 检查是否已经是 Git 仓库或已有项目文件
    if exist ".git" (
        echo [提示] 检测到现有 Git 仓库，跳过克隆步骤
        echo.
        goto :setup_venv
    ) else if exist "main.py" (
        echo [提示] 检测到现有项目文件，跳过克隆步骤
        echo.
        goto :setup_venv
    ) else (
        goto :clone_repo
    )
)
goto :setup_venv

:: ============================================
:: Git 克隆仓库（带重试机制）
:: ============================================
:clone_repo
set RETRIES=3
set COUNT=0

:clone_try
set /a COUNT+=1
echo 正在尝试克隆仓库 (尝试 %COUNT%/%RETRIES%)...
git clone "%REPO_URL%"
if %errorlevel% equ 0 (
    echo [✓] 克隆成功
    goto :enter_project_dir
) else (
    echo [警告] 第 %COUNT% 次克隆失败。
    if %COUNT% lss %RETRIES% (
        echo 等待 2 秒后重试...
        timeout /t 2 >nul
        goto :clone_try
    ) else (
        echo.
        echo [提示] Git 克隆失败，尝试使用 curl 下载 ZIP 压缩包...
        goto :download_zip
    )
)

:: ============================================
:: 下载并解压 ZIP（克隆失败后的备选方案）
:: ============================================
:download_zip
echo.
echo 正在下载项目压缩包...
curl -L -o project.zip "%REPO_ZIP_URL%"
if %errorlevel% neq 0 (
    echo [错误] 下载失败！
    echo.
    echo 请手动从以下地址下载 ZIP 并解压：
    echo %REPO_ZIP_URL%
    echo.
    pause
    exit /b 1
)

echo [✓] 下载成功，正在解压...
tar -xf project.zip
if %errorlevel% neq 0 (
    echo [错误] 解压失败！请手动解压 project.zip 文件。
    pause
    exit /b 1
)

echo [✓] 解压成功，正在重命名文件夹...
:: GitHub ZIP 解压后的文件夹名通常为 REPO-main 或 REPO-master
if exist "%PROJECT_NAME%-main" (
    ren "%PROJECT_NAME%-main" "%PROJECT_NAME%"
) else if exist "%PROJECT_NAME%-master" (
    ren "%PROJECT_NAME%-master" "%PROJECT_NAME%"
)

echo [✓] 正在清理临时文件...
del /f /q project.zip

echo [✓] 项目下载和解压完成
goto :enter_project_dir

:: ============================================
:: 进入项目目录
:: ============================================
:enter_project_dir
if exist "%REPO_DIR%\main.py" (
    pushd "%REPO_DIR%"
    if %errorlevel% equ 0 (
        echo.
        echo [✓] 已进入项目目录: %REPO_DIR%
        echo.
        goto :setup_venv
    ) else (
        echo [警告] 无法进入项目目录，将在当前目录检查文件。
        goto :setup_venv
    )
) else if exist "%REPO_DIR%" (
    echo [提示] 项目文件缺失 main.py，请重新下载项目。
    pause
    exit /b 1
) else (
    echo [提示] 未找到预期的项目目录，请重新下载项目。
    pause
    exit /b 1
)

:: ============================================
:: 第三步：创建虚拟环境
:: ============================================
:setup_venv
echo [3/5] 正在检查/创建虚拟环境...
if exist ".venv\" (
    echo [提示] 检测到现有虚拟环境
) else (
    echo 正在创建虚拟环境...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [错误] 虚拟环境创建失败！
        pause
        exit /b 1
    )
    echo [✓] 虚拟环境创建成功
)
echo.

:: ============================================
:: 第四步：激活虚拟环境
:: ============================================
echo [4/5] 正在激活虚拟环境...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [错误] 虚拟环境激活失败！
    pause
    exit /b 1
)
echo [✓] 虚拟环境已激活
echo.

:: ============================================
:: 第五步：安装依赖
:: ============================================
echo [5/5] 正在安装/更新依赖包...
if not exist "requirements.txt" (
    echo [警告] 未找到 requirements.txt 文件！
    echo 将尝试直接运行程序...
    echo.
    goto :run_program
)

echo 使用阿里云镜像源安装依赖，请稍候...
pip install pip -i https://mirrors.aliyun.com/pypi/simple/ >nul 2>&1
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败！
    echo.
    echo 您可以尝试手动执行：
    echo pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
    echo.
    pause
    exit /b 1
)
echo [✓] 依赖安装完成
echo.

:: ============================================
:: 运行主程序
:: ============================================
:run_program
echo ========================================
echo   环境准备完成，正在启动程序...
echo ========================================
echo.

if not exist "main.py" (
    echo [错误] 未找到 main.py 文件！
    echo.
    echo 请确保您在正确的项目目录中运行此脚本。
    echo.
    pause
    exit /b 1
)

python main.py

:: 程序结束后的处理
echo.
echo ========================================
echo   程序已退出
echo ========================================

:: 如果使用了 pushd，则恢复原目录
popd 2>nul

pause
