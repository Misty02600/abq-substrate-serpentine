# Tech Context

## Technologies Used

### Core Platform
- **ABAQUS**：有限元分析软件（主要版本 2020+）
- **ABAQUS Python API**：脚本接口

### Programming Language
- **Python**：ABAQUS 内置 Python 解释器
  - ABAQUS 2020 及之前：Python 2.7
  - ABAQUS 2021+：Python 3.x
- 脚本需兼容两种 Python 版本

### Key Libraries
```python
# ABAQUS 专用模块
from abaqus import *
from abaqusConstants import *
from regionToolset import Region

# 标准库
import numpy as np
from pathlib import Path
import configparser
import json
import os
import sys
```

## Development Setup

### 运行方式
1. **ABAQUS CAE GUI**：File → Run Script
2. **ABAQUS noGUI**：`abaqus cae noGUI=script.py`
3. **ABAQUS Python**：`abaqus python script.py`

### 目录结构
```
script/
├── *.py                  # 入口脚本
├── config.ini            # 配置文件
├── src/                  # 源代码模块
│   ├── config/           # 配置处理
│   ├── model/            # 模型创建
│   ├── postprocess/      # 后处理
│   └── utils/            # 工具函数
├── common_scripts/       # 通用脚本
└── memory-bank/          # 项目文档
```

### 脚本路径处理
```python
# 兼容 GUI 和 noGUI 模式
try:
    SCRIPT_DIR = Path(__file__).parent.resolve()
except NameError:
    fname = inspect.getfile(inspect.currentframe())
    SCRIPT_DIR = Path(fname).parent.resolve()
```

## Technical Constraints

### ABAQUS Python 限制
- 不支持所有 Python 标准库
- 部分第三方库不可用
- 调试能力有限

### 几何建模约束
- 蛇形线需要精确的圆弧连接
- 多孔基底圆孔不能重叠
- 网格质量要求较高

### 计算资源
- 支持多 CPU 并行计算
- 通过 `num_cpus` 配置控制
- 作业队列管理

## Dependencies

### 必需依赖
- ABAQUS（含 CAE 和 Solver）
- NumPy（ABAQUS 内置）

### 可选依赖
- JSON 输出支持
- 批处理脚本

## Configuration Files

### config.ini 主要配置段
```ini
[substrate]   # 基底几何参数
[loading]     # 加载条件
[wire]        # 蛇形线参数
[pores]       # 孔隙配置
[computing]   # 计算资源
[analysis]    # 分析步配置
[interaction] # 相互作用配置
[output]      # 输出配置
[naming]      # 模型命名配置
```

### 多值参数语法
```ini
porosity = 0.3,0.5,0.7        # 生成 3 个模型
random_seed = 1,2,3           # 生成 3 个模型
# 组合后生成 3×3=9 个模型
```
