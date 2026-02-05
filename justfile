# Justfile for ABAQUS serpentine-substrate project

# Windows 使用 PowerShell
set shell := ["powershell.exe", "-c"]

# --- 路径定义 ---
# 源代码目录（绝对路径）
src := "D:/Projects/ABAQUS/abq-serp-sub/src/abq_serp_sub"

# --- Conda 配置 ---
# Conda 环境名称
conda_env := "abaqus"
# conda run 前缀（用于在 conda 环境中运行命令）
cr := "conda run -n " + conda_env

# 默认命令
default:
    @just --list

# --- ABAQUS 脚本命令 ---

# 运行 wire.py 测试脚本
wire:
    abaqus cae noGUI="{{src}}/processes/parts/wire.py"

# 运行 substrate 包测试脚本（使用 __main__.py）
substrate:
    abaqus cae noGUI="{{src}}/processes/parts/substrate/__main__.py"

# 在 GUI 模式下运行 wire.py（方便调试）
wire-gui:
    abaqus cae script="{{src}}/processes/parts/wire.py"

# 在 GUI 模式下运行 substrate 包（方便调试）
substrate-gui:
    abaqus cae script="{{src}}/processes/parts/substrate/__main__.py"

# 运行 assembly 模块测试
assembly:
    abaqus cae noGUI="{{src}}/processes/assembly.py"

# 在 GUI 模式下运行 assembly 模块测试（方便调试）
assembly-gui:
    abaqus cae script="{{src}}/processes/assembly.py"

# 从 JSON 配置文件创建模型
build JSON_PATH:
    abaqus cae noGUI="{{src}}/processes/assembly.py" -- {{JSON_PATH}}

# --- Conda 环境命令 ---

# 生成参数文件（在 conda 环境中运行）
generate *ARGS:
    {{cr}} python generate_params.py {{ARGS}}

# 在 conda 环境中运行任意 Python 命令
py *ARGS:
    {{cr}} python {{ARGS}}

# 安装/更新本项目到 conda 环境（可编辑模式）
install:
    {{cr}} pip install -e .

