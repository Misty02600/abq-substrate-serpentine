# Tech Context

## Technologies Used

### Core Platform
- **ABAQUS**：有限元分析软件（**需要 2024+ 版本**）
- **ABAQUS Python API**：脚本接口

### Programming Language
- **Python 3.10**：ABAQUS 2024+ 内置 Python 3 解释器
- 使用 dataclass、类型注解等现代 Python 特性

### Key Libraries

#### 本地 Python (uv 管理) - 配置生成
```python
# Hydra 配置框架
import hydra
from hydra import main
from omegaconf import DictConfig, OmegaConf

# 类型验证
from pydantic import BaseModel, Field, field_validator

# 标准库
import json
from pathlib import Path
```

#### ABAQUS Python - 仿真运行
```python
# ABAQUS 专用模块
from abaqus import *
from abaqusConstants import *
from regionToolset import Region

# 标准库
import json
from pathlib import Path
from dataclasses import dataclass
import numpy as np
```

## Development Setup

### 依赖安装

```bash
# 配置生成依赖（本地 Python）
uv add --optional config hydra-core hydra-list-sweeper pydantic

# 或安装所有依赖
uv sync --all-extras
```

### 运行方式

#### 1. 生成参数文件（本地 Python）
```bash
uv run python generate_params.py --multirun
# → 生成 params/*.json
```

#### 2. 运行 ABAQUS 仿真
```bash
abaqus cae noGUI=run_abaqus.py -- params/model_001.json
```

### 目录结构
```
script/
├── *.py                      # 入口脚本
├── config.ini                # 旧配置文件（保留兼容）
├── conf/                     # 新配置目录
│   └── config.yaml           # Hydra YAML 配置
├── params/                   # 生成的 JSON 参数文件
│   └── *.json
├── src/
│   ├── config/               # 配置处理
│   │   ├── parse_config.py   # 旧：INI 解析
│   │   ├── process_config.py # 旧：派生值计算
│   │   ├── resolvers.py      # 新：OmegaConf resolver
│   │   └── models.py         # 新：Pydantic 模型
│   ├── model/                # 模型创建
│   │   ├── assembly.py
│   │   ├── configs/          # dataclass 配置（ABAQUS 用）
│   │   └── parts/            # 几何部件
│   ├── postprocess/          # 后处理
│   └── utils/                # 工具函数
├── generate_params.py        # 新：参数生成脚本
├── pyproject.toml            # 项目配置
└── uv.lock                   # 依赖锁定
```

## Technical Constraints

### 双进程架构
```
┌─────────────────────────┐     ┌─────────────────────────┐
│  本地 Python (uv)       │     │  ABAQUS Python          │
│  - Hydra + OmegaConf    │ ──> │  - 读取 JSON            │
│  - Pydantic 验证        │     │  - 构建 dataclass       │
│  - 生成 JSON            │     │  - 运行仿真             │
└─────────────────────────┘     └─────────────────────────┘
```

### ABAQUS Python 限制
- 不支持所有 Python 标准库
- 第三方库安装受限（因此采用双进程架构）
- 调试能力有限

### 几何建模约束
- 蛇形线需要精确的圆弧连接
- 多孔基底圆孔不能重叠
- 网格质量要求较高

## Dependencies

### pyproject.toml
```toml
[project.optional-dependencies]
# 配置生成依赖（本地 Python 使用，ABAQUS Python 不需要）
config = [
    "hydra-core>=1.3",
    "hydra-list-sweeper>=1.0",
    "pydantic>=2.0",
]
```

### 必需依赖
- ABAQUS 2024+（含 CAE 和 Solver）
- NumPy（ABAQUS 内置）
- uv（依赖管理）

## Configuration Files

### conf/config.yaml（新）
```yaml
defaults:
  - _self_
  - override hydra/sweeper: list

hydra:
  mode: MULTIRUN
  sweeper:
    grid_params:
      substrate.porosity: 0.2,0.3,0.4,0.5,0.6
      pores.T_delta: 0.02,0.06,0.1
      pores.random_seed: 1,2,3,4,5

substrate:
  n_rows: 16
  n_cols: ${imul:${substrate.n_rows},2}    # 派生值
  square_size: ${div:2,${substrate.n_rows}}
```

### 自定义 Resolver
```python
# src/config/resolvers.py
OmegaConf.register_new_resolver("imul", lambda x, y: int(float(x) * float(y)))
OmegaConf.register_new_resolver("div", lambda x, y: float(x) / float(y))
```

## Pydantic Configuration Models

### 配置模型层次
```python
# src/config/models.py
class Config(BaseModel):
    substrate: SubstrateConfig
    loading: LoadingConfig
    wire: WireConfig
    pores: PoresConfig
    computing: ComputingConfig
    analysis: AnalysisConfig
    interaction: InteractionConfig
    output: OutputConfig
    naming: NamingConfig
    modelname: str
```

### 派生值计算
- `n_cols`: `${imul:${substrate.n_rows},2}` → resolver 计算
- `square_size`: `${div:2,${substrate.n_rows}}` → resolver 计算
- `origin`: Pydantic `model_validator` 自动计算

**最后更新**：2026-01-27
