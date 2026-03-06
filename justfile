# Justfile for ABAQUS serpentine-substrate project

# Windows 使用 PowerShell
set shell := ["powershell.exe", "-c"]

# --- 路径定义 ---
# 项目根目录（硬编码）
root := "D:/Projects/ABAQUS/abq-substrate-serpentine"
# 源代码目录（硬编码）
src := "D:/Projects/ABAQUS/abq-substrate-serpentine/src/abq_serp_sub"

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

# 从 JSON 配置文件创建模型（noGUI）
build JSON_PATH:
    abaqus cae noGUI="{{src}}/processes/assembly.py" -- {{JSON_PATH}}

# 从 JSON 配置文件创建模型（GUI 交互式选择文件）
build-json:
    abaqus cae script="{{root}}/generate_from_json.py"

# --- uv 环境命令 ---

# 生成参数文件
generate *ARGS:
    uv run python generate_params.py {{ARGS}}

# 交互式选择 YAML 配置并生成参数文件
generate-select *ARGS:
    uv run python generate_params.py --select-config {{ARGS}}

# 运行测试
test *ARGS:
    uv run pytest tests/ {{ARGS}}

# 安装/更新依赖
install:
    uv sync

# --- ABAQUS 环境初始化 ---

# 将本包和 pandas 安装到 ABAQUS Python（换机器/升级 ABAQUS 后运行一次）
setup-abaqus:
    abaqus python -m pip install -e .
