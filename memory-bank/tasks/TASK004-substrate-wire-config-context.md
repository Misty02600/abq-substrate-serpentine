# [TASK004] - 为基底和导线部件创建配置上下文

**Status:** Completed
**Added:** 2026-01-16
**Updated:** 2026-01-16
**Completed:** 2026-01-16

## Original Request

用户认为创建 wire 和 substrate 时需要大量相关的参数，希望分别整理成创建部件的配置上下文（dataclass），来减少传参。

## Thought Process

### 当前参数分析

#### build_porous_substrate
```python
def build_porous_substrate(
    modelname: str,
    partname: str,
    circles: np.ndarray,
    square_size: float,
    depth: float = 0.25,
    substrate_seed_size: float = 0.01,
):
```
共 6 个参数，其中 4 个有默认值。

#### build_serpentine_wire
```python
def build_serpentine_wire(
    modelname: str,
    partname: str,
    w: float = 0.05,
    l_1: float = 0.5,
    l_2: float = 0.5,
    m: int = 4,
    wire_seed_size: float = 0.005,
    pi_thickness: float = 0.003,
    cu_thickness: float = 0.0006,
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
):
```
共 10 个参数，其中 8 个有默认值。

### 配置类设计建议

#### substrate.py

**SubstrateGeomConfig** - 基底几何参数
- `square_size: float` - 正方形单元边长
- `depth: float = 0.25` - 部件厚度
- `circles: np.ndarray | None = None` - 圆孔数据（可选，多孔基底需要）

**SubstratePartConfig** - 基底部件参数
- `modelname: str` - 模型名称
- `partname: str` - 部件名称
- `substrate_seed_size: float = 0.01` - 布种尺寸

**建议函数签名变化：**
```python
def build_porous_substrate(
    geom_config: SubstrateGeomConfig,
    part_config: SubstratePartConfig,
):
```

#### wire.py

**WireGeomConfig** - 导线几何参数
- `w: float = 0.05` - 导线宽度
- `l_1: float = 0.5` - 周期水平节距
- `l_2: float = 0.5` - 竖直直线段长度
- `m: int = 4` - 周期数
- `origin: tuple[float, float, float] = (0.0, 0.0, 0.0)` - 草图原点

**WireMaterialConfig** - 导线材料参数
- `pi_thickness: float = 0.003` - PI 单层厚度
- `cu_thickness: float = 0.0006` - Cu 单层厚度

**WirePartConfig** - 导线部件参数
- `modelname: str` - 模型名称
- `partname: str` - 部件名称
- `wire_seed_size: float = 0.005` - 布种尺寸

**建议函数签名变化：**
```python
def build_serpentine_wire(
    geom_config: WireGeomConfig,
    material_config: WireMaterialConfig,
    part_config: WirePartConfig,
):
```

## Implementation Plan

- [ ] 1.1 在 substrate.py 中创建 `SubstrateGeomConfig` dataclass
- [ ] 1.2 在 substrate.py 中创建 `SubstratePartConfig` dataclass
- [ ] 1.3 在 substrate.py 中创建 `SubstrateConfig` 包装类（可选）
- [ ] 1.4 在 substrate.py 中重构 `build_porous_substrate()` 使用新配置类
- [ ] 1.5 在 substrate.py 中重构 `build_solid_substrate()` 使用新配置类
- [ ] 2.1 在 wire.py 中创建 `WireGeomConfig` dataclass
- [ ] 2.2 在 wire.py 中创建 `WireMaterialConfig` dataclass
- [ ] 2.3 在 wire.py 中创建 `WirePartConfig` dataclass
- [ ] 2.4 在 wire.py 中创建 `WireConfig` 包装类（可选）
- [ ] 2.5 在 wire.py 中重构 `build_serpentine_wire()` 使用新配置类
- [ ] 2.6 在 wire.py 中重构 `build_serpentine_wire_no_caps()` 使用新配置类
- [ ] 3.1 更新 assembly.py 中的调用代码
- [ ] 3.2 测试配置上下文功能

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | 创建 SubstrateGeomConfig | Complete | 2026-01-16 | |
| 1.2 | 创建 SubstratePartConfig | Complete | 2026-01-16 | |
| 1.3 | 创建 SubstrateConfig 包装类 | Complete | 2026-01-16 | 已实现 |
| 1.4 | 重构 build_porous_substrate() | Complete | 2026-01-16 | |
| 1.5 | 重构 build_solid_substrate() | Complete | 2026-01-16 | |
| 2.1 | 创建 WireGeomConfig | Complete | 2026-01-16 | |
| 2.2 | 创建 WireMaterialConfig | Complete | 2026-01-16 | |
| 2.3 | 创建 WirePartConfig | Complete | 2026-01-16 | |
| 2.4 | 创建 WireConfig 包装类 | Complete | 2026-01-16 | 已实现 |
| 2.5 | 重构 build_serpentine_wire() | Complete | 2026-01-16 | |
| 2.6 | 重构 build_serpentine_wire_no_caps() | Complete | 2026-01-16 | |
| 3.1 | 更新 assembly.py 调用 | Complete | 2026-01-16 | |
| 3.2 | 测试验证 | Complete | 2026-01-16 | 无语法错误 |

## Progress Log

### 2026-01-16 (完成)
- 创建任务
- 分析当前两个函数的参数结构
- 提出三层配置类设计方案（几何、材料、部件）
- 在 substrate.py 创建 SubstrateGeomConfig, SubstratePartConfig, SubstrateConfig
- 重构 build_porous_substrate() 和 build_solid_substrate() 使用 SubstrateConfig
- 在 wire.py 创建 WireGeomConfig, WireMaterialConfig, WirePartConfig, WireConfig
- 重构 build_serpentine_wire() 和 build_serpentine_wire_no_caps() 使用 WireConfig
- 更新 assembly.py 导入和调用代码
- 验证无语法错误
- **任务完成**

## Design Considerations

### 参数分层原则

1. **几何参数 (GeomConfig)** - 影响部件形状和拓扑的参数
2. **材料参数 (MaterialConfig)** - 仅 wire.py 需要，定义材料厚度
3. **部件参数 (PartConfig)** - 模型名、部件名、网格参数等通用配置

### dataclass 选择

使用 `@dataclass` 而不是继承 StepIncrementConfig 的原因：
- 参数含义不同，不应强行继承关系
- dataclass 提供自动 `__init__`, `__eq__`, `__repr__`
- 支持默认值和 `field()` 进行精细控制

### 可选的包装类

考虑创建 `SubstrateConfig` 和 `WireConfig` 作为三层配置的聚合，方便一次性传递所有参数：

```python
@dataclass
class SubstrateConfig:
    geom: SubstrateGeomConfig
    part: SubstratePartConfig

    @classmethod
    def default_porous(cls, circles, modelname, partname):
        return cls(
            geom=SubstrateGeomConfig(circles=circles, ...),
            part=SubstratePartConfig(modelname=modelname, partname=partname, ...)
        )
```

### 向后兼容性

需要考虑在 assembly.py 中更新调用代码，并验证参数传递的正确性。
