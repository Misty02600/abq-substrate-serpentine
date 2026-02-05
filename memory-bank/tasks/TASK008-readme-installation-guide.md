# [TASK008] - README 安装与使用指南

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request

用户希望在 README 中添加库的安装和使用说明。需要解决如何将库安装到 ABAQUS 的 Python 环境中的问题。

用户倾向于使用 pip 本地安装（editable install），而非打包上传到 PyPI，以避免 abqpy 等开发依赖污染 ABAQUS 原生环境。

## Thought Process

### ABAQUS Python 环境特点

1. **独立的 Python 解释器**：ABAQUS 自带 Python（2024+ 版本为 Python 3.10）
2. **位置**：通常在 `<ABAQUS安装目录>/Commands/` 或类似路径
3. **限制**：不支持所有第三方库，部分 C 扩展可能不兼容

### 安装策略分析

#### 方案 A：pip editable install（推荐）

```bash
# 找到 ABAQUS 的 Python
# Windows: C:\SIMULIA\EstProducts\2024\win_b64\code\bin\python3.exe
# 或通过 abaqus python -c "import sys; print(sys.executable)"

# 本地可编辑安装（不安装 abqpy 等开发依赖）
abaqus python -m pip install -e . --no-deps
```

**优点：**
- 代码修改立即生效，无需重新安装
- `--no-deps` 避免安装 abqpy 等仅用于类型提示的依赖
- 保持 ABAQUS 原生环境干净

**缺点：**
- 需要手动确保 numpy 等运行时依赖已存在

#### 方案 B：PYTHONPATH 方式

```bash
# 设置环境变量
set PYTHONPATH=D:\Projects\ABAQUS\serpentine interface\script;%PYTHONPATH%
abaqus cae noGUI=main.py
```

**优点：**
- 最简单，无需安装
- 完全不修改 ABAQUS 环境

**缺点：**
- 每次运行都需设置
- 相对导入可能有问题

#### 方案 C：sys.path 动态添加

在入口脚本中：
```python
import sys
sys.path.insert(0, r"D:\Projects\ABAQUS\serpentine interface\script")
```

**优点：**
- 自包含，不依赖外部配置

**缺点：**
- 硬编码路径
- 每个入口脚本都需要添加

### 推荐方案

**方案 A（pip editable install + --no-deps）**是最佳选择：
- 一次安装，永久生效
- 开发时代码修改立即可用
- 不污染 ABAQUS 环境

### pyproject.toml 调整

当前 `dependencies` 包含 `abqpy`，这是开发时类型提示用的，不应安装到 ABAQUS 环境。

建议拆分为：
- `dependencies`: 仅运行时必需（numpy 等，ABAQUS 自带）
- `optional-dependencies.dev`: 开发依赖（abqpy, pandas 等）


## Implementation Plan

- [ ] 1.1 调整 pyproject.toml 依赖分组
- [ ] 1.2 编写 README 安装说明
  - ABAQUS Python 路径查找方法
  - pip editable install 命令
  - 验证安装成功的方法
- [ ] 1.3 编写 README 使用说明
  - 配置文件说明
  - 运行命令示例
  - 常见问题解答
- [ ] 1.4 测试安装流程

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | 调整 pyproject.toml | Complete | 2026-01-17 | dependencies=[], dev 依赖分离 |
| 1.2 | 编写安装说明 | Complete | 2026-01-17 | pip editable install --no-deps |
| 1.3 | 编写使用说明 | Complete | 2026-01-17 | 配置文件说明、运行命令、FAQ |
| 1.4 | 测试安装流程 | Skipped | 2026-01-17 | 需用户在实际环境验证 |

## Progress Log

### 2026-01-17
- 创建任务
- 分析三种安装方案
- 推荐 pip editable install + --no-deps

### 2026-01-17 - Implementation
- 更新 pyproject.toml：dependencies=[]，dev 依赖分离
- 重写 README.md：安装说明、使用方法、项目结构、FAQ
- 任务完成

## Technical Notes

### 查找 ABAQUS Python 路径

```bash
# 方法1：通过 abaqus 命令
abaqus python -c "import sys; print(sys.executable)"

# 方法2：常见位置
# Windows: C:\SIMULIA\EstProducts\2024\win_b64\code\bin\python3.exe
# Linux: /opt/SIMULIA/EstProducts/2024/linux_a64/code/bin/python3
```

### 验证安装

```bash
abaqus python -c "from src.model.assembly import create_porous_model; print('OK')"
```
