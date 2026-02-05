# [TASK005] - 导线和基底材料参数配置上下文

**Status:** Completed
**Added:** 2026-01-16
**Updated:** 2026-01-16
**Completed:** 2026-01-16

## Original Request

用户希望把导线（Wire）和基底（Substrate）的材料参数也重构成配置上下文，实现材料参数的集中管理和配置化。

## Thought Process

### 当前材料参数分析

#### substrate.py - PDMS 材料
```python
def _create_pdms_material(model: Model, c1: float = 0.27027, c2: float = 0.067568, d: float = 0.12):
    pdms = model.Material(name="PDMS")
    pdms.Hyperelastic(
        materialType=ISOTROPIC,
        testData=OFF,
        type=MOONEY_RIVLIN,
        volumetricResponse=VOLUMETRIC_DATA,
        table=((c1, c2, d),),
    )
```
- Mooney-Rivlin 超弹性模型参数：C1, C2, D

#### wire.py - PI/Cu 材料
```python
# 硬编码在函数内部（两处重复）
model.Material(name="PI")
model.materials["PI"].Elastic(table=((2500.0, 0.27),))

model.Material(name="Cu")
model.materials["Cu"].Elastic(table=((130000.0, 0.34),))
```
- PI：弹性模量 E=2500 MPa，泊松比 ν=0.27
- Cu：弹性模量 E=130000 MPa，泊松比 ν=0.34

### 配置类设计建议

#### PDMSMaterialConfig - 基底 PDMS 材料
```python
@dataclass
class PDMSMaterialConfig:
    """PDMS 超弹性材料参数（Mooney-Rivlin 模型）"""
    c1: float = 0.27027
    c2: float = 0.067568
    d: float = 0.12
```

#### ElasticMaterialConfig - 通用弹性材料
```python
@dataclass
class ElasticMaterialConfig:
    """弹性材料参数"""
    name: str
    youngs_modulus: float  # 弹性模量 E (MPa)
    poissons_ratio: float  # 泊松比 ν
```

#### WireMaterialConfig - 扩展现有类
当前 `WireMaterialConfig` 仅包含厚度参数，需扩展以包含材料属性：
```python
@dataclass
class WireMaterialConfig:
    """蛇形导线材料参数配置"""
    # 厚度参数
    pi_thickness: float = 0.003
    cu_thickness: float = 0.0006
    # 材料属性
    pi_elastic: ElasticMaterialConfig = field(
        default_factory=lambda: ElasticMaterialConfig("PI", 2500.0, 0.27)
    )
    cu_elastic: ElasticMaterialConfig = field(
        default_factory=lambda: ElasticMaterialConfig("Cu", 130000.0, 0.34)
    )
```

### 实现方案

1. 在 substrate.py 创建 `PDMSMaterialConfig`
2. 修改 `_create_pdms_material()` 接受 `PDMSMaterialConfig` 参数
3. 在 wire.py 创建 `ElasticMaterialConfig`（通用弹性材料）
4. 扩展 `WireMaterialConfig` 包含 PI/Cu 材料属性
5. 提取材料创建逻辑为辅助函数
6. 消除两个 wire 函数中的重复材料创建代码

## Implementation Plan

- [ ] 1.1 在 substrate.py 创建 `PDMSMaterialConfig` dataclass
- [ ] 1.2 修改 `_create_pdms_material()` 使用 `PDMSMaterialConfig`
- [ ] 1.3 更新调用代码适配新签名
- [ ] 2.1 在 wire.py 创建 `ElasticMaterialConfig` dataclass
- [ ] 2.2 扩展 `WireMaterialConfig` 包含材料属性
- [ ] 2.3 创建 `_create_wire_materials()` 辅助函数
- [ ] 2.4 重构两个 build 函数使用新的材料创建逻辑
- [ ] 3.1 测试验证材料参数配置正确性

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | 创建 PDMSMaterialConfig | Complete | 2026-01-16 | |
| 1.2 | 修改 _create_pdms_material() | Complete | 2026-01-16 | 支持配置类或默认值 |
| 1.3 | 更新 substrate 调用代码 | Complete | 2026-01-16 | 无需修改，兼容 |
| 2.1 | 创建 ElasticMaterialConfig | Complete | 2026-01-16 | |
| 2.2 | 扩展 WireMaterialConfig | Complete | 2026-01-16 | 添加 pi_elastic, cu_elastic |
| 2.3 | 创建 _create_wire_materials() | Complete | 2026-01-16 | |
| 2.4 | 重构 wire build 函数 | Complete | 2026-01-16 | 两个函数都已重构 |
| 3.1 | 测试验证 | Complete | 2026-01-16 | 无语法错误 |

## Progress Log

### 2026-01-16 (完成)
- 创建任务
- 分析当前材料参数位置和硬编码情况
- 提出配置类设计方案
- 在 substrate.py 创建 `PDMSMaterialConfig` dataclass
- 修改 `_create_pdms_material()` 支持配置类参数
- 在 wire.py 创建 `ElasticMaterialConfig` dataclass
- 扩展 `WireMaterialConfig` 添加 `pi_elastic` 和 `cu_elastic` 属性
- 创建 `_create_wire_materials()` 辅助函数
- 重构两个 build 函数，消除硬编码材料参数
- 验证无语法错误
- **任务完成**

## Design Considerations

### 材料参数分离原则

1. **基底材料** - PDMS 超弹性，使用 Mooney-Rivlin 模型
2. **导线材料** - PI/Cu 线弹性，需要弹性模量和泊松比

### 与 TASK004 的关系

- TASK004 创建的 `WireMaterialConfig` 仅包含厚度参数
- 本任务扩展该类以包含材料弹性属性
- 保持向后兼容，默认值与当前硬编码值一致

### 代码重复消除

wire.py 中 `build_serpentine_wire()` 和 `build_serpentine_wire_no_caps()` 有相同的材料创建代码，应提取为公共辅助函数。
