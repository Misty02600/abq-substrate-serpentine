# System Patterns

## System Architecture

本项目采用**双进程解耦架构**，将配置处理（本地 Python）与仿真执行（ABAQUS Python）完全分离。

### 组件分工

| 组件              | 运行环境         | 职责                             |
| ----------------- | ---------------- | -------------------------------- |
| **Hydra**         | 本地 Python (uv) | 配置加载、参数扫描、多次运行调度 |
| **OmegaConf**     | 本地 Python (uv) | 配置插值、派生值计算（resolver） |
| **Pydantic**      | 本地 Python (uv) | 类型验证、默认值、复杂校验       |
| **JSON 文件**     | 中间格式         | 参数传递接口                     |
| **ABAQUS Python** | ABAQUS 内置      | 读取 JSON、构建模型、运行仿真    |

---

## Hydra 工作原理

### 核心功能

**Hydra** 是配置管理框架，负责：
1. **配置加载**：从 `conf/config.yaml` 读取 YAML 配置
2. **参数扫描**：根据 `hydra.sweeper` 配置生成参数组合
3. **多次调用**：在 `--multirun` 模式下，对每个参数组合调用一次 `main()` 函数

### 参数扫描类型

使用 `hydra-list-sweeper` 插件支持两种扫描模式：

**Grid（笛卡尔积）**：所有参数值的排列组合
```yaml
hydra:
  sweeper:
    grid_params:
      substrate.porosity: 0.2,0.3,0.4,0.5,0.6   # 5 个值
      pores.T_delta: 0.02,0.06,0.1              # 3 个值
      pores.random_seed: 1,2,3,4,5              # 5 个值
      # 总计: 5 × 3 × 5 = 75 组合
```

**List（Zip 配对）**：对应位置参数配对
```yaml
hydra:
  sweeper:
    list_params:
      substrate.n_rows: 8,16,32
      substrate.n_cols: 16,32,64
      # 生成: (8,16), (16,32), (32,64) 共 3 组
```

### 执行流程

运行 `uv run python generate_params.py --multirun` 时：

1. Hydra 加载 `conf/config.yaml`
2. 解析 `hydra.sweeper` 配置，计算所有参数组合
3. 对每个组合调用 `main(cfg)`，其中 `cfg` 包含该组合的参数值
4. Hydra 还会在 `cfg` 中注入自己的运行时配置（`cfg.hydra`），包括输出目录、作业信息等

---

## OmegaConf 工作原理

### 核心功能

**OmegaConf** 是 Hydra 的底层配置库，负责：
1. **配置插值**：支持 `${section.key}` 语法引用其他配置值
2. **派生值计算**：通过自定义 resolver 计算依赖其他值的配置

### 自定义 Resolver

在 `src/config/resolvers.py` 中注册的 resolver：

```python
# 整数乘法 resolver
OmegaConf.register_new_resolver("imul", lambda a, b: int(a) * int(b))

# 除法 resolver
OmegaConf.register_new_resolver("div", lambda a, b: float(a) / float(b))
```

### 在 YAML 中使用

```yaml
substrate:
  n_rows: 16
  n_cols: ${imul:${substrate.n_rows},2}        # → 32 (16 × 2)
  square_size: ${div:2,${substrate.n_rows}}    # → 0.125 (2 / 16)
```

### 解析时机

Resolver 在调用 `OmegaConf.to_container(cfg, resolve=True)` 时执行，将 `${...}` 替换为计算后的实际值。

---

## Pydantic 工作原理

### 核心功能

**Pydantic** 负责：
1. **类型验证**：确保配置值类型正确
2. **约束检查**：如 `porosity` 必须在 0 到 0.7854 之间
3. **默认值填充**：未提供的可选配置使用默认值
4. **复杂计算**：通过 `model_validator` 执行依赖多个字段的计算（如自动计算 `origin`）
5. **忽略多余键**：配置 `extra="ignore"` 自动忽略 Hydra 注入的运行时配置

### 关键配置

```python
class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")  # 忽略 hydra 等多余键

    @model_validator(mode="after")
    def compute_origin_if_missing(self) -> "Config":
        """如果未指定 origin，根据基底几何自动计算"""
        if self.wire.origin is None:
            self.wire.origin = (
                substrate_width / 4,
                substrate_height / 2,
                self.substrate.depth,
            )
        return self
```

---

## 完整数据流

1. **Hydra 加载配置**
   - 读取 `conf/config.yaml`
   - 根据 sweeper 配置生成参数组合
   - 对每个组合调用 `main(cfg)`

2. **OmegaConf 解析派生值**
   - `cfg` 是 OmegaConf 的 `DictConfig` 对象
   - 调用 `OmegaConf.to_container(cfg, resolve=True)`
   - 所有 `${...}` resolver 被执行，得到纯 Python 字典

3. **Pydantic 验证**
   - 将字典传入 `Config(**cfg_dict)`
   - 类型检查、约束验证、自动计算 origin
   - 多余的键（如 `hydra`）被自动忽略

4. **生成模型名称**
   - `generate_modelname(config)` 根据参数值生成唯一名称
   - 如 `uni_n16_phi0p5_xi0p0_delta0p06_seed1`

5. **输出 JSON**
   - `config.model_dump()` 序列化为字典
   - 写入 `params/<modelname>.json`

6. **ABAQUS 读取**
   - ABAQUS Python 使用标准库 `json` 读取文件
   - 构建 dataclass 配置上下文
   - 执行模型构建和仿真

---

## Directory Structure

```
script/
├── conf/
│   └── config.yaml           # Hydra YAML 配置
├── params/                   # 生成的 JSON 参数文件
│   └── *.json
├── generate_params.py        # 参数生成入口（Hydra）
├── generate_from_json.py     # ABAQUS 模型生成入口
├── src/
│   └── abq_serp_sub/
│       ├── config/           # 配置处理模块
│       │   ├── models.py     # Pydantic 模型
│       │   ├── resolvers.py  # OmegaConf resolver
│       │   └── naming.py     # 模型命名函数
│       ├── core/context/     # 配置 dataclass
│       ├── processes/parts/  # 部件构建
│       └── utils/            # 工具函数
└── memory-bank/              # 项目文档
```

---

## abqpy 命令行用法

> 官方文档：https://haiiliin.github.io/abqpy/

### 概述

`abqpy` 是一个为 Abaqus Python 脚本提供类型提示的 Python 包。它允许你在本地 Python 环境中编写 Abaqus 脚本，然后通过命令行将脚本提交到 Abaqus Python 解释器执行。

**核心优势**：
- 使用本地 Python 3 环境编写脚本，获得完整的类型提示和代码补全
- 无需打开 Abaqus/CAE 即可运行脚本
- 一个脚本完成建模、提交作业、提取结果

### 安装

```bash
# 使用 pip（推荐匹配 Abaqus 版本）
pip install -U abqpy==2025.*  # 根据你的 Abaqus 版本调整

# 使用 conda
conda install conda-forge::abqpy=2025
```

> ⚠️ **警告**：不要在 Abaqus 内置的 Python 解释器中安装 abqpy，可能导致 Abaqus/CAE 无法打开。

### 命令行用法

#### 基本语法

```bash
# 使用 abqpy 命令
abqpy COMMAND SCRIPT <flags> [ARGS]...

# 或者使用 python -m 运行（推荐）
python -m abqpy COMMAND SCRIPT <flags> [ARGS]...
```

其中 `COMMAND` 可以是：
- `cae` - Abaqus/CAE 执行模式
- `python` - Abaqus Python 执行模式
- `run` - 自定义命令
- 其他 Abaqus 命令（如 `viewer`, `optimization` 等）

#### Abaqus/CAE 模式 (`cae`)

用于需要 `abaqus` 模块的脚本（建模、装配等）。

```bash
# 基本用法（noGUI 模式，默认）
abqpy cae script.py [args ...]

# 等价于：abaqus cae noGUI=script.py -- [args ...]
```

**可用选项**：

| 选项                | 类型 | 说明                        |
| ------------------- | ---- | --------------------------- |
| `--gui` / `--nogui` | bool | 是否使用 GUI 模式           |
| `-d, --database`    | str  | 打开的数据库文件 (.odb)     |
| `--replay`          | str  | 回放文件                    |
| `--recover`         | str  | 恢复的日志文件              |
| `--startup`         | str  | 启动文件                    |
| `-e, --envstartup`  | bool | 执行环境启动文件            |
| `--savedOptions`    | bool | 使用保存的选项              |
| `--savedGuiPrefs`   | bool | 使用保存的 GUI 偏好         |
| `--startupDialog`   | bool | 显示启动对话框              |
| `-c, --custom`      | str  | 自定义 GUI Toolkit 命令文件 |
| `--guiTester`       | str  | 启动 Python 开发环境        |
| `--guiRecord`       | bool | 记录 GUI 命令               |

**示例**：

```bash
# noGUI 模式运行脚本
abqpy cae script.py

# GUI 模式，打开数据库文件
abqpy cae script.py --gui --database=file.odb

# 传递额外参数给脚本
abqpy cae script.py -- arg1 arg2
```

#### Abaqus Python 模式 (`python`)

用于只需要 `odbAccess` 模块的脚本（后处理、数据提取等）。

```bash
# 基本用法
abqpy python script.py [args ...]

# 等价于：abaqus python script.py [args ...]
```

**可用选项**：

| 选项        | 类型 | 说明       |
| ----------- | ---- | ---------- |
| `-s, --sim` | str  | 仿真文件名 |
| `-l, --log` | str  | 日志文件名 |

### 自动执行机制

当你在脚本中导入 `abaqus` 或 `odbAccess` 模块时，abqpy 会自动调用 Abaqus 命令：

```python
# 导入 abaqus 模块时，自动执行：
# abaqus cae noGUI=script.py -- [args ...]
from abaqus import *

# 导入 odbAccess 模块时，自动执行：
# abaqus python script.py [args ...]
from odbAccess import *
```

这意味着你可以直接运行脚本：

```bash
python script.py
```

### 在 Python 脚本中使用 CLI

```python
from abqpy.cli import abaqus

# 运行 CAE 脚本
abaqus.cae("script.py", gui=True, database="file.odb")

# 运行 Python 脚本
abaqus.python("script.py")
```

### 环境变量配置

#### `ABAQUS_BAT_PATH`

指定 Abaqus 命令的路径。**这是指定 Abaqus 版本的关键方法**。

当系统安装了多个 Abaqus 版本时，通过设置这个环境变量指向特定版本的 `abaqus.bat` 文件：

```powershell
# Windows - 指定 Abaqus 2024
$env:ABAQUS_BAT_PATH = "C:/SIMULIA/EstProducts/2024/win_b64/code/bin/ABQLauncher.exe"
# 或者使用 Commands 目录
$env:ABAQUS_BAT_PATH = "C:/SIMULIA/Commands/abaqus.bat"

# 常见路径格式：
# C:/SIMULIA/EstProducts/<版本号>/win_b64/code/bin/ABQLauncher.exe
# C:/Program Files/Dassault Systemes/SimulationServices/V6R<版本>/win_b64/code/bin/ABQLauncher.exe
```

**在脚本中动态切换版本**：

```python
import os

# 使用 Abaqus 2024
os.environ["ABAQUS_BAT_PATH"] = "C:/SIMULIA/EstProducts/2024/win_b64/code/bin/ABQLauncher.exe"

# 或使用 Abaqus 2023
# os.environ["ABAQUS_BAT_PATH"] = "C:/SIMULIA/EstProducts/2023/win_b64/code/bin/ABQLauncher.exe"

from abaqus import *
```

#### `ABAQUS_COMMAND_OPTIONS`

设置默认的命令行选项（Python 字典格式）：

```python
import os
os.environ["ABAQUS_COMMAND_OPTIONS"] = str({"gui": True, "database": "file.odb"})
from abaqus import *
```

#### 快捷环境变量

| 变量                     | 类型 | 说明                           |
| ------------------------ | ---- | ------------------------------ |
| `ABAQUS_CAE_GUI`         | bool | 设置 gui 选项                  |
| `ABAQUS_CAE_DATABASE`    | str  | 设置 database 选项             |
| `ABAQUS_CAE_STARTUP`     | str  | 设置 startup 选项              |
| `ABQPY_DEBUG`            | bool | 启用调试模式                   |
| `ABQPY_SKIP_ABAQUS`      | bool | 跳过 Abaqus 命令执行           |
| `ABQPY_EXECUTION_METHOD` | str  | 执行方法：`os` 或 `subprocess` |

> 布尔值可使用：`true/false`, `on/off`, `yes/no`, `1/0`

### VS Code 集成

在 VS Code 设置中配置默认启动参数：

```json
{
    "python.terminal.launchArgs": ["-m", "abqpy", "cae", "--gui=True"]
}
```

这样在终端运行 Python 文件时会自动使用 abqpy：

```bash
python -m abqpy cae --gui=True script.py
```

### 实际使用场景

#### 场景 1：本地开发 + Abaqus 执行

```bash
# 1. 在本地 Python 环境开发脚本（获得类型提示）
# 2. 使用 abqpy 提交到 Abaqus
python -m abqpy cae build_model.py
```

#### 场景 2：批量运行仿真

```bash
# 遍历参数文件运行
for file in params/*.json; do
    python -m abqpy cae run_simulation.py -- "$file"
done
```

#### 场景 3：后处理提取数据

```bash
# 使用 python 模式（不需要 CAE 许可证）
python -m abqpy python extract_results.py
```

### 注意事项

1. **Python 版本兼容性**：
   - Abaqus 2024 之前使用 Python 2.7
   - Abaqus 2024 及以后使用 Python 3.10.5
   - 编写脚本时注意兼容性

2. **调试限制**：abqpy 不支持直接调试，调试时会在 Abaqus PDE 中打开

3. **许可证**：
   - `cae` 模式需要 Abaqus/CAE 许可证
   - `python` 模式只需要 Abaqus Python 解释器

**最后更新**：2026-01-27
