# TASK009: 配置系统重构 - Hydra + OmegaConf + Pydantic

## 任务信息

| 字段         | 内容       |
| ------------ | ---------- |
| **ID**       | TASK009    |
| **状态**     | 🔄 进行中   |
| **创建日期** | 2026-01-26 |
| **更新日期** | 2026-01-27 |
| **优先级**   | 高         |

---

## 🎯 核心目标

### 架构设计：双进程解耦

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        本地 Python (uv 管理)                                 │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐          │
│  │config.yaml │ → │ 扫参展开   │ → │ 派生值计算 │ → │ 类型验证   │          │
│  │  (YAML)    │   │Grid + List │   │ Resolver   │   │ Pydantic   │          │
│  └────────────┘   └────────────┘   └────────────┘   └────────────┘          │
│        ↓                ↓                ↓                ↓                 │
│   hydra-core    hydra-list-sweeper   OmegaConf        Pydantic              │
└─────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │   params_001.json     │
                              │   params_002.json     │
                              │   params_003.json     │  ← 每个参数组合一个文件
                              │   ...                 │
                              └───────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ABAQUS Python (无额外依赖)                            │
│  ┌────────────────┐   ┌────────────────┐   ┌────────────────┐               │
│  │ 读取 JSON 文件 │ → │ 构建 Dataclass │ → │ 运行仿真脚本   │               │
│  │ (stdlib json)  │   │ 配置上下文     │   │ 创建模型/作业  │               │
│  └────────────────┘   └────────────────┘   └────────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 架构优势

| 优势             | 说明                             |
| ---------------- | -------------------------------- |
| ✅ **完全解耦**   | 配置处理与 ABAQUS 执行分离       |
| ✅ **无兼容问题** | ABAQUS Python 只需 `json` 标准库 |
| ✅ **可预览**     | JSON 文件可人工检查参数正确性    |
| ✅ **可复现**     | JSON 文件可版本控制和归档        |
| ✅ **批量提交**   | 预生成所有 JSON 后批量运行       |
| ✅ **灵活工具链** | 本地 Python 可使用任意现代工具   |

### 关键需求

| 需求             | 描述                     | 实现方式        | 运行环境      |
| ---------------- | ------------------------ | --------------- | ------------- |
| **笛卡尔积扫参** | 多参数完全组合           | `grid_params`   | 本地 Python   |
| **Zip 配对扫参** | 多参数一一对应           | `list_params`   | 本地 Python   |
| **派生值计算**   | `n_cols = n_rows * 2`    | 自定义 Resolver | 本地 Python   |
| **类型验证**     | 强类型，IDE 支持         | Pydantic        | 本地 Python   |
| **参数序列化**   | 每组参数保存为 JSON      | `json.dump()`   | 本地 Python   |
| **参数反序列化** | 读取 JSON 构建 dataclass | `json.load()`   | ABAQUS Python |

---

# 一、当前系统分析

## 1.1 现有配置示例 (INI)
```ini
[substrate]
n_rows = 16
porosity = 0.2,0.3,0.4,0.5,0.6   # 逗号分隔 = 笛卡尔积

[pores]
T_delta = 0.02,0.06,0.1
random_seed = 1,2,3,4,5

# 结果: 5 × 3 × 5 = 75 个模型组合
```

## 1.2 当前系统局限

| 问题                | 描述                         |
| ------------------- | ---------------------------- |
| ❌ 不支持 Zip 配对   | 所有多值参数都是笛卡尔积     |
| ❌ 派生值硬编码      | 在 Python 代码中而非配置文件 |
| ❌ 类型不安全        | 运行时手动检查               |
| ❌ 无 dataclass 输出 | 返回普通 dict                |

---

# 二、技术方案

## 2.1 技术栈

### 本地 Python (uv 管理)

```bash
# 添加依赖
uv add hydra-core hydra-list-sweeper pydantic
```

| 组件                   | 用途                     | 版本要求   |
| ---------------------- | ------------------------ | ---------- |
| **hydra-core**         | 配置管理、multirun 框架  | ≥1.3       |
| **hydra-list-sweeper** | Grid + List 扫参         | ≥1.0       |
| **OmegaConf**          | YAML 解析、resolver 插值 | Hydra 依赖 |
| **Pydantic**           | 类型验证、模型定义       | ≥2.0       |

### ABAQUS Python (无额外依赖)

| 组件            | 用途         | 说明             |
| --------------- | ------------ | ---------------- |
| **json**        | 读取参数文件 | Python 标准库    |
| **dataclasses** | 配置上下文   | Python 3.7+ 内置 |
| **pathlib**     | 路径处理     | Python 标准库    |

## 2.2 数据流

```python
# ==================== 本地 Python (generate_params.py) ====================
# 1. Hydra 加载 YAML → OmegaConf DictConfig
# 2. hydra-list-sweeper 展开 grid_params + list_params
# 3. OmegaConf resolver 计算派生值
# 4. Pydantic Model 类型验证
# 5. 序列化为 JSON 文件

from omegaconf import OmegaConf
from pydantic import BaseModel
import json

cfg_dict = OmegaConf.to_container(cfg, resolve=True)
config = Config(**cfg_dict)  # Pydantic 验证

# 输出 JSON
with open(f"params/{config.modelname}.json", "w") as f:
    json.dump(config.model_dump(), f, indent=2)

# ==================== ABAQUS Python (run_abaqus.py) ====================
# 1. 读取 JSON 文件
# 2. 构建 dataclass 配置上下文
# 3. 运行仿真脚本

import json
from dataclasses import dataclass

with open("params/model_001.json") as f:
    params = json.load(f)

config = SubstrateConfig(**params["substrate"])
# 运行仿真...
```

---

# 三、扫参展开：hydra-list-sweeper

## 3.1 Grid + List 组合

```yaml
# conf/config.yaml
defaults:
  - _self_
  - override hydra/sweeper: list   # 启用 list sweeper

hydra:
  mode: MULTIRUN
  sweeper:
    # 笛卡尔积参数
    grid_params:
      pores.porosity: 0.3,0.4,0.5         # 3 个值
      pores.random_seed: 1,2,3,4,5        # 5 个值

    # Zip 配对参数（一一对应）
    list_params:
      substrate.n_rows: 8,16,32           # 3 个值
      substrate.n_cols: 16,32,64          # 3 个值（与 n_rows 配对）

# 结果:
# grid_params: 3 × 5 = 15 个笛卡尔积
# list_params: 3 个 Zip 配对 (8,16), (16,32), (32,64)
# 总计: 15 × 3 = 45 组合
```

## 3.2 list_params 工作原理

```yaml
list_params:
  param_a: 1, 2, 3
  param_b: x, y, z
```

生成 **3 个** job（Zip 配对，而非 9 个笛卡尔积）:
- `param_a=1, param_b=x`
- `param_a=2, param_b=y`
- `param_a=3, param_b=z`

---

# 四、派生值计算：自定义 Resolver

## 4.1 定义 Resolver

```python
# src/resolvers.py
from omegaconf import OmegaConf

def register_resolvers():
    """注册自定义 OmegaConf resolver，必须在 Hydra 初始化前调用"""

    # 整数乘法: ${imul:${a},2}
    OmegaConf.register_new_resolver(
        "imul",
        lambda x, y: int(float(x) * float(y)),
        replace=True  # 允许重复注册
    )

    # 除法: ${div:${a},2}
    OmegaConf.register_new_resolver(
        "div",
        lambda x, y: float(x) / float(y),
        replace=True
    )

    # 整除: ${idiv:${a},2}
    OmegaConf.register_new_resolver(
        "idiv",
        lambda x, y: int(float(x) // float(y)),
        replace=True
    )

    # 加法: ${add:${a},1}
    OmegaConf.register_new_resolver(
        "add",
        lambda x, y: float(x) + float(y),
        replace=True
    )
```

## 4.2 在配置中使用

```yaml
# conf/config.yaml
substrate:
  n_rows: 16
  n_cols: ${imul:${substrate.n_rows},2}    # = 32

  square_size: ${div:2,${substrate.n_rows}}  # = 0.125

  seed_size: 0.009
  edge_seed_size: ${div:${substrate.seed_size},2}  # = 0.0045
```

## 4.3 Resolver 执行时机

OmegaConf resolver 是**惰性求值**的：
- 在 `OmegaConf.to_container(cfg, resolve=True)` 时解析
- 或者访问具体字段时解析

---

# 五、类型验证：Pydantic 模型

## 5.1 定义 Pydantic 模型

```python
# src/config_models.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Tuple

class SubstrateConfig(BaseModel):
    n_rows: int = Field(ge=1, description="网格行数")
    n_cols: int = Field(ge=1, description="网格列数")
    porosity: float = Field(ge=0, le=0.7854, description="孔隙率")
    depth: float = Field(gt=0, description="厚度")
    seed_size: float = Field(gt=0, description="布种尺寸")
    edge_seed_size: float = Field(gt=0, description="边缘布种尺寸")
    square_size: Optional[float] = None  # 派生值

    @field_validator('porosity')
    @classmethod
    def validate_porosity(cls, v):
        if v > 0.7854:
            raise ValueError(f"porosity {v} 超过理论最大值 π/4 ≈ 0.7854")
        return v

class WireConfig(BaseModel):
    w: float = Field(gt=0, description="导线宽度")
    l_1: float = Field(gt=0, description="水平节距")
    l_2: float = Field(gt=0, description="竖直长度")
    m: int = Field(ge=1, description="周期数")
    seed_size: float = Field(gt=0, description="布种尺寸")
    rotation_angle: float = Field(default=0, description="旋转角度")
    origin: Optional[Tuple[float, float, float]] = None

class PoresConfig(BaseModel):
    use_standard_circles: bool = False
    T_xi: float = Field(ge=0, description="坐标偏差截断")
    T_delta: float = Field(ge=0, description="直径偏差截断")
    random_seed: int = Field(ge=0, description="随机种子")

class ComputingConfig(BaseModel):
    num_cpus: int = Field(ge=1, default=1)
    enable_restart: bool = False

class Config(BaseModel):
    """完整配置模型"""
    substrate: SubstrateConfig
    wire: WireConfig
    pores: PoresConfig
    computing: ComputingConfig

    # 可以访问嵌套属性
    @property
    def model_params(self) -> dict:
        """返回用于模型命名的参数"""
        return {
            "n_rows": self.substrate.n_rows,
            "porosity": self.substrate.porosity,
            "T_delta": self.pores.T_delta,
            "random_seed": self.pores.random_seed,
        }
```

## 5.2 从 OmegaConf 转换

```python
from omegaconf import OmegaConf, DictConfig
from src.config_models import Config

def load_config(cfg: DictConfig) -> Config:
    """将 OmegaConf DictConfig 转换为 Pydantic Config"""
    # 解析所有 resolver
    cfg_dict = OmegaConf.to_container(cfg, resolve=True)

    # Pydantic 验证
    return Config(**cfg_dict)
```

---

# 六、完整入口脚本

```python
# run.py
import hydra
from omegaconf import DictConfig, OmegaConf
from src.resolvers import register_resolvers
from src.config_models import Config

# 注册自定义 resolver（必须在 @hydra.main 之前）
register_resolvers()

@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig):
    """Hydra multirun 会多次调用此函数，每次 cfg 是一个参数组合"""

    # 1. 解析 resolver，得到完整配置
    cfg_dict = OmegaConf.to_container(cfg, resolve=True)

    # 2. Pydantic 类型验证
    try:
        config = Config(**cfg_dict)
    except ValidationError as e:
        print(f"配置验证失败: {e}")
        return

    # 3. 使用类型安全的 config
    print(f"n_rows = {config.substrate.n_rows}")
    print(f"n_cols = {config.substrate.n_cols}")  # 派生值
    print(f"porosity = {config.substrate.porosity}")

    # 4. 传递给业务逻辑
    run_simulation(config)

if __name__ == "__main__":
    main()
```

---

# 七、Hydra 工作目录行为

## 7.1 问题说明

Hydra 默认会**自动切换工作目录**到 `outputs/<date>/<time>/` 或 `multirun/<date>/<time>/<job_id>/`。

这意味着：
- `os.getcwd()` 返回的是 Hydra 创建的输出目录，不是脚本所在目录
- 相对路径引用（如 `./data/input.txt`）会失效
- 每次运行都会创建新的输出目录

## 7.2 解决方案

### 方案 A：禁用工作目录切换（推荐）

```yaml
# conf/config.yaml
hydra:
  job:
    chdir: false  # 禁用自动切换工作目录
  run:
    dir: .        # 单次运行时输出到当前目录
  sweep:
    dir: outputs  # multirun 时输出目录
    subdir: ${hydra.job.id}  # 子目录使用 job ID
```

### 方案 B：使用绝对路径

```python
import hydra
from pathlib import Path

@hydra.main(...)
def main(cfg):
    # 获取原始工作目录（脚本启动时的目录）
    original_cwd = Path(hydra.utils.get_original_cwd())

    # 使用绝对路径
    data_file = original_cwd / "data" / "input.txt"
```

### 方案 C：配置固定输出目录

```yaml
hydra:
  run:
    dir: ./outputs/${now:%Y-%m-%d}/${now:%H-%M-%S}
  sweep:
    dir: ./outputs/multirun/${now:%Y-%m-%d}
    subdir: ${hydra.job.num}
```

## 7.3 推荐配置

```yaml
# conf/config.yaml
hydra:
  job:
    chdir: false  # 不切换工作目录

  output_subdir: null  # 不创建 .hydra 子目录

  run:
    dir: .  # 输出到当前目录
```

---

# 八、项目目录结构

```
project/
├── conf/
│   └── config.yaml               # 主配置（含 sweeper 配置）
├── params/                        # 生成的参数文件目录
│   ├── uni_n16_phi0p3_seed1.json
│   ├── uni_n16_phi0p3_seed2.json
│   └── ...
├── src/
│   ├── config/                    # 配置处理（本地 Python）
│   │   ├── resolvers.py           # 自定义 OmegaConf resolver
│   │   └── models.py              # Pydantic 配置模型
│   └── model/                     # ABAQUS 模型（ABAQUS Python）
│       └── configs/               # dataclass 配置上下文
├── generate_params.py             # 本地 Python：生成 JSON 参数文件
├── run_abaqus.py                  # ABAQUS Python：读取 JSON 并运行仿真
└── pyproject.toml                 # uv 依赖管理
```

---

# 九、使用流程

```bash
# 1. 生成参数文件（本地 Python，使用 uv）
uv run python generate_params.py --multirun

# 2. 查看生成的参数文件
ls params/
# uni_n16_phi0p3_seed1.json
# uni_n16_phi0p3_seed2.json
# ...

# 3. 运行 ABAQUS 仿真（可串行或并行）
abaqus cae noGUI=run_abaqus.py -- params/uni_n16_phi0p3_seed1.json

# 或批量运行
for f in params/*.json; do
    abaqus cae noGUI=run_abaqus.py -- "$f"
done
```

---

# 十、待办事项

## 本地 Python 部分 ✅ 已完成 (2026-01-27)
- [x] 使用 uv 管理依赖：`uv add hydra-core hydra-list-sweeper pydantic`
- [x] 创建 `src/config/resolvers.py`：定义 imul, div 等 resolver
- [x] 创建 `src/config/models.py`：定义 Pydantic 配置模型
- [x] 创建 `conf/config.yaml`：迁移现有 INI 配置到 YAML
- [x] 创建 `generate_params.py`：Hydra 入口脚本，输出 JSON
- [x] 验证生成 75 个 JSON 参数文件

## ABAQUS Python 部分 ⏳ 待完成
- [ ] 创建 `run_abaqus.py`：读取 JSON，构建 dataclass，运行仿真
- [ ] 验证 dataclass 配置与现有 `src/model/configs/` 兼容

## 集成测试 ⏳ 待完成
- [ ] 测试完整流程：YAML → 扫参 → 派生 → JSON → dataclass → 仿真
- [ ] 验证批量运行脚本

---

# 十一、相关文件

| 文件                           | 用途                                        |
| ------------------------------ | ------------------------------------------- |
| `src/config/parse_config.py`   | 当前配置解析（待替换）                      |
| `src/config/process_config.py` | 当前派生值计算（迁移到 resolver）           |
| `src/model/configs/`           | 已有的 dataclass 配置（ABAQUS Python 使用） |
| `config.ini`                   | 当前配置文件（迁移到 YAML）                 |
