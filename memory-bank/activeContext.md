# Active Context

## Current Work Focus
- **配置系统重构完成**：assembly.py 采用 ModelConfig 类，支持类型安全的配置传递

## Recent Changes
- 2026-02-04：**assembly.py 重构**
  - **新增配置类**（`core/context/model.py`）：
    - `LoadingConfig` - 加载条件配置
    - `ComputingConfig` - 计算资源配置
    - `InteractionConfig` - 相互作用配置
    - `OutputConfig` - 输出配置
    - `ModelConfig` - 完整模型配置（聚合所有子配置）
  - **新增构建函数**（`core/builders.py`）：
    - `build_substrate_config(cfg)` - 从 dict 构建基底配置
    - `build_wire_config(cfg)` - 从 dict 构建导线配置
    - `build_model_config(cfg)` - 从 dict 构建完整模型配置
  - **迁移 pores.py**：从 `processes/parts/substrate/` 迁移到 `core/pores.py`
  - **简化 substrate**：从包结构变回单模块 `processes/parts/substrate.py`
  - **更新配置类字段**：
    - `WireGeomConfig` 新增 `rotation_angle`
    - `SubstrateMeshConfig` 新增 `edge_seed_size`
  - **函数签名变更**：
    - `create_model(config: ModelConfig)` - 核心函数，接受配置类
    - `create_model_from_dict(cfg: dict)` - 便捷函数，从 dict 创建
    - `create_model_from_json(json_path: str)` - 从 JSON 文件创建

## Next Steps
1. **测试**：在 ABAQUS 环境验证重构后的 assembly.py
2. **扩展**：根据需要添加新的配置字段控制流程

## Active Decisions and Considerations

### 当前架构（2026-02-04）

```
core/                          # 纯计算和数据定义层
├── pores.py                   # 孔隙生成纯函数
├── builders.py                # dict → dataclass 构建函数
└── context/                   # 配置 dataclass
    ├── material.py
    ├── substrate.py
    ├── wire.py
    ├── step.py
    └── model.py               # 完整模型配置

processes/                     # ABAQUS 操作层
├── assembly.py                # 模型组装入口
├── steps.py                   # 分析步创建
└── parts/
    ├── substrate.py           # 基底构建
    ├── wire.py                # 导线构建
    └── material_instances.py  # 预定义材料
```

### 配置类层次结构

```
ModelConfig
├── modelname: str
├── substrate_config: SubstrateConfig (SolidSubstrateConfig | PorousSubstrateConfig)
│   ├── geom: GeomConfig
│   ├── material: HyperelasticMaterialConfig
│   └── mesh: SubstrateMeshConfig
├── wire_config: WireConfig
│   ├── geom: WireGeomConfig (含 rotation_angle)
│   ├── section: WireSectionConfig
│   └── mesh: WireMeshConfig
├── loading: LoadingConfig (u1, u2)
├── computing: ComputingConfig (num_cpus, enable_restart)
├── interaction: InteractionConfig (use_cohesive)
└── output: OutputConfig (global_output)
```

### 添加新配置字段的流程

> 如果需要添加新配置来控制流程，步骤如下：

1. **在相应的配置类中添加字段**（`core/context/*.py`）
2. **更新构建函数**（`core/builders.py`）从 dict 读取新字段
3. **在使用处访问配置属性**（如 `config.computing.new_field`）

**示例：添加 `memory_limit` 配置**

```python
# 1. core/context/model.py
@dataclass
class ComputingConfig:
    num_cpus: int
    enable_restart: bool
    memory_limit: int  # 新增字段

# 2. core/builders.py
def build_model_config(cfg: dict) -> ModelConfig:
    computing=ComputingConfig(
        num_cpus=cfg["computing"]["num_cpus"],
        enable_restart=cfg["computing"]["enable_restart"],
        memory_limit=cfg["computing"]["memory_limit"],  # 读取新字段
    ),

# 3. processes/assembly.py
memory = config.computing.memory_limit  # 使用新字段
```

**最后更新**：2026-02-04
