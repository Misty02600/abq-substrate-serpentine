# [TASK007] - 分离配置类到独立模块

**Status:** Completed
**Added:** 2026-01-16
**Updated:** 2026-01-16

## Original Request

用户希望将各模块中的 dataclass 配置类分离出去，形成独立的配置模块，便于集中管理和维护。

## Thought Process

### 当前配置类分布

| 文件 | 配置类 |
|------|--------|
| substrate.py | `PDMSMaterialConfig`, `SubstratePartConfig`, `SolidSubstrateGeomConfig`, `SolidSubstrateConfig`, `PorousSubstrateGeomConfig`, `PorousSubstrateConfig` |
| wire.py | `ElasticMaterialConfig`, `WireGeomConfig`, `WireMaterialConfig`, `WirePartConfig`, `WireConfig` |
| assembly.py | `StepIncrementConfig` |

共 12 个配置类，分散在 3 个文件中。

### 设计方案

#### 方案 A：单一配置文件

```
src/model/
    configs.py          # 所有配置类
    substrate.py
    wire.py
    assembly.py
```

**优点：** 简单，一个文件搞定
**缺点：** 文件可能变大，不同领域混在一起

#### 方案 B：按领域分文件

```
src/model/
    configs/
        __init__.py     # 导出所有配置类
        material.py     # PDMSMaterialConfig, ElasticMaterialConfig
        substrate.py    # SubstratePartConfig, SolidSubstrate*, PorousSubstrate*
        wire.py         # WireGeomConfig, WireMaterialConfig, WirePartConfig, WireConfig
        step.py         # StepIncrementConfig
    substrate.py
    wire.py
    assembly.py
```

**优点：** 职责清晰，易于扩展
**缺点：** 文件较多，需要维护 `__init__.py`

#### 方案 C：按层次分文件（推荐）

```
src/model/
    configs/
        __init__.py     # 导出所有配置类
        geom.py         # 几何配置：SolidSubstrateGeomConfig, PorousSubstrateGeomConfig, WireGeomConfig
        material.py     # 材料配置：PDMSMaterialConfig, ElasticMaterialConfig, WireMaterialConfig
        part.py         # 部件配置：SubstratePartConfig, WirePartConfig
        composite.py    # 聚合配置：SolidSubstrateConfig, PorousSubstrateConfig, WireConfig
        step.py         # 分析步配置：StepIncrementConfig
    substrate.py
    wire.py
    assembly.py
```

**优点：** 按配置层次组织，符合 TASK004 的三层设计
**缺点：** 可能过度拆分

### 推荐方案

**方案 B** 较为平衡：
- 按领域（substrate/wire/step）分文件
- 材料配置可以共享一个文件（material.py）
- `__init__.py` 统一导出，外部使用简单

### 导入方式变化

**重构前：**
```python
from .substrate import PorousSubstrateConfig, SubstratePartConfig
from .wire import WireConfig, WireGeomConfig
```

**重构后：**
```python
from .configs import (
    PorousSubstrateConfig,
    SubstratePartConfig,
    WireConfig,
    WireGeomConfig,
)
```

## Implementation Plan

- [ ] 1.1 确定最终目录结构方案
- [ ] 1.2 创建 configs/ 子包
- [ ] 1.3 将 substrate.py 的配置类移至 configs/substrate.py
- [ ] 1.4 将 wire.py 的配置类移至 configs/wire.py
- [ ] 1.5 将 assembly.py 的配置类移至 configs/step.py
- [ ] 1.6 创建 configs/material.py 放置共享材料配置
- [ ] 1.7 创建 configs/__init__.py 统一导出
- [ ] 2.1 更新 substrate.py 的导入
- [ ] 2.2 更新 wire.py 的导入
- [ ] 2.3 更新 assembly.py 的导入
- [ ] 3.1 测试验证无导入错误

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | 确定目录结构 | Complete | 2026-01-16 | 采用方案 B |
| 1.2 | 创建 configs/ 子包 | Complete | 2026-01-16 | |
| 1.3 | 移动 substrate 配置类 | Complete | 2026-01-16 | 6 个类 |
| 1.4 | 移动 wire 配置类 | Complete | 2026-01-16 | 5 个类 |
| 1.5 | 移动 step 配置类 | Complete | 2026-01-16 | 1 个类 + DEFAULT |
| 1.6 | 创建 material.py | Complete | 2026-01-16 | PDMSMaterialConfig + ElasticMaterialConfig |
| 1.7 | 创建 __init__.py | Complete | 2026-01-16 | 统一导出 12 个类 |
| 2.1 | 更新 substrate.py 导入 | Complete | 2026-01-16 | |
| 2.2 | 更新 wire.py 导入 | Complete | 2026-01-16 | |
| 2.3 | 更新 assembly.py 导入 | Complete | 2026-01-16 | |
| 3.1 | 测试验证 | Complete | 2026-01-16 | 无错误 |

## Progress Log

### 2026-01-16
- 创建任务
- 分析当前配置类分布（12 个类，3 个文件）
- 提出 3 种目录结构方案，推荐方案 B

### 2026-01-16 - Implementation
- 创建 `src/model/configs/` 子包
- 创建 `material.py`：PDMSMaterialConfig, ElasticMaterialConfig
- 创建 `substrate.py`：SubstratePartConfig, Solid/Porous 配置
- 创建 `wire.py`：WireGeomConfig, WireMaterialConfig, WirePartConfig, WireConfig
- 创建 `step.py`：StepIncrementConfig, DEFAULT_STEP_CONFIG
- 创建 `__init__.py`：统一导出所有配置类
- 更新 substrate.py、wire.py、assembly.py 的导入
- 验证无语法错误
- 任务完成

## Design Considerations

### 循环导入风险

configs 模块应只包含纯数据类，不依赖其他模块（如 abaqus），避免循环导入。

### TYPE_CHECKING 处理

部分配置类使用了 `np.ndarray` 类型注解，需要保留 numpy 导入。

### 向后兼容

可以在原文件保留导入并重新导出，保持旧代码兼容：
```python
# substrate.py
from .configs import PorousSubstrateConfig, SolidSubstrateConfig  # re-export
```

### 与 src/config/ 的关系

注意项目已有 `src/config/` 目录（用于解析配置文件），新的 configs 子包应放在 `src/model/configs/`，避免混淆。
