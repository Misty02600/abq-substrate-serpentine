# [TASK006] - 网格布种参数配置化

**Status:** Pending
**Added:** 2026-01-16
**Updated:** 2026-01-16

## Original Request

用户计划将厚度边偏置布种的 `ratio` 和 `number` 参数也作为可配置参数。后续可能还要优化一些网格划分的组织。

## Thought Process

### 当前硬编码参数

```python
def _seed_substrate_part(sub_part: Part, seed_size: float) -> None:
    # 全局布种
    sub_part.seedPart(size=seed_size, deviationFactor=0.1, minSizeFactor=0.1)

    # 厚度边使用偏置布种
    thickness_edges = sub_part.sets["ThicknessEdges"].edges
    sub_part.seedEdgeByBias(
        biasMethod=SINGLE,
        end2Edges=thickness_edges,
        ratio=2,          # 硬编码
        number=7,         # 硬编码
        constraint=FINER,
    )
```

### 可配置化的参数

1. **厚度边偏置布种参数：**
   - `ratio: float = 2` - 偏置比
   - `number: int = 7` - 单元数量

2. **全局布种参数（可选扩展）：**
   - `deviationFactor: float = 0.1`
   - `minSizeFactor: float = 0.1`

### 设计建议

#### 方案 A：扩展 SubstratePartConfig

```python
@dataclass
class SubstratePartConfig:
    modelname: str = "Model-1"
    partname: str = "Substrate"
    seed_size: float = 0.01
    # 新增
    thickness_bias_ratio: float = 2.0
    thickness_bias_number: int = 7
```

#### 方案 B：独立 MeshSeedingConfig

```python
@dataclass
class MeshSeedingConfig:
    """网格布种配置"""
    global_seed_size: float = 0.01
    deviation_factor: float = 0.1
    min_size_factor: float = 0.1
    thickness_bias_ratio: float = 2.0
    thickness_bias_number: int = 7
```

### 后续优化方向

- 网格划分逻辑重组
- 不同区域使用不同布种策略
- 自适应网格细化参数

## Implementation Plan

- [ ] 1.1 确定配置方案（A 或 B）
- [ ] 1.2 创建或扩展配置类
- [ ] 1.3 修改 `_seed_substrate_part()` 接受配置参数
- [ ] 1.4 更新调用代码
- [ ] 2.1 考虑其他网格划分参数配置化
- [ ] 2.2 测试验证

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | 确定配置方案 | Not Started | - | 待讨论 |
| 1.2 | 创建配置类 | Not Started | - | |
| 1.3 | 修改 _seed_substrate_part() | Not Started | - | |
| 1.4 | 更新调用代码 | Not Started | - | |
| 2.1 | 其他网格参数配置化 | Not Started | - | 可选 |
| 2.2 | 测试验证 | Not Started | - | |

## Progress Log

### 2026-01-16
- 创建任务
- 分析当前硬编码参数
- 提出两种配置方案

## Design Considerations

### 参数归属问题

- 方案 A 简单，但 `SubstratePartConfig` 职责变重
- 方案 B 更清晰，但增加配置类数量

### 与现有配置的关系

- 当前 `SubstratePartConfig.seed_size` 已存在
- 新参数是否应与 `seed_size` 同级，还是独立分组

### 兼容性

- 新增参数应有合理默认值，保持向后兼容
