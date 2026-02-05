# [TASK003] - 提取基底构建公共代码

**Status:** In Progress
**Added:** 2026-01-16
**Updated:** 2026-01-16

## Original Request

用户认为 `build_porous_substrate` 和 `build_solid_substrate` 两个函数有公共部分需要提取，提高代码复用性和可维护性。

## Thought Process

分析两个函数后，发现以下公共模式：

### 1. 模型获取/创建逻辑
两个函数都使用相同的 try/except 模式获取或创建模型：
```python
try:
    model = mdb.models[modelname]
except KeyError:
    model = mdb.Model(name=modelname)
```
**建议：** 提取为 `get_or_create_model(modelname: str) -> Model`

### 2. 材料定义（用户已确认）
两个函数都创建相同的 PDMS 材料：
```python
pdms = model.Material(name="PDMS")
pdms.Hyperelastic(
    materialType=ISOTROPIC,
    testData=OFF,
    type=MOONEY_RIVLIN,
    volumetricResponse=VOLUMETRIC_DATA,
    table=((0.27027, 0.067568, 0.12),),
)
```
**建议：** 提取为 `create_pdms_material(model: Model, name: str = "PDMS")`

### 3. 截面创建与赋予（用户已确认）
两个函数都创建并赋予相同的截面：
```python
model.HomogeneousSolidSection(name="PDMS-section", material="PDMS")
cells = part.cells
region = Region(cells=cells)
part.SectionAssignment(region=region, sectionName="PDMS-section")
```
**建议：** 提取为 `assign_section_to_part(model, part, material_name: str, section_name: str)`

### 4. 基础集合创建
两个函数都创建以下相同的集合：
- `BottomFace`, `LeftFace`, `RightFace`, `TopFace` (Surface)
- `ThicknessEdges`
- `TPC_A`, `TPC_B` (三点约束控制点)
- `TopEdges`, `TopLineEdges`

**建议：** 提取为 `create_substrate_sets(part, length, width, depth)` 返回包含所有集合引用的字典

### 5. 网格布种逻辑
两个函数都使用相同的布种模式：
```python
part.seedPart(size=substrate_seed_size, deviationFactor=0.1, minSizeFactor=0.1)
thickness_edges = part.sets["ThicknessEdges"].edges
part.seedEdgeByBias(
    biasMethod=SINGLE,
    end2Edges=thickness_edges,
    ratio=2,
    number=7,
    constraint=FINER,
)
```
**建议：** 提取为 `seed_substrate_part(part, seed_size: float)`

## Implementation Plan

- [x] 1.1 创建 `_get_or_create_model()` 辅助函数
- [x] 1.2 创建 `_create_pdms_material()` 辅助函数
- [x] 1.3 创建 `_assign_section_to_part()` 辅助函数
- [ ] 1.4 创建 `_create_substrate_sets()` 辅助函数 (暂缓，待用户确认)
- [x] 1.5 创建 `_seed_substrate_part()` 辅助函数
- [x] 2.1 重构 `build_porous_substrate()` 使用新辅助函数
- [x] 2.2 重构 `build_solid_substrate()` 使用新辅助函数
- [ ] 3.1 测试重构后的函数功能

## Progress Tracking

**Overall Status:** In Progress - 75%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | 创建 _get_or_create_model() | Complete | 2026-01-16 | |
| 1.2 | 创建 _create_pdms_material() | Complete | 2026-01-16 | |
| 1.3 | 创建 _assign_section_to_part() | Complete | 2026-01-16 | |
| 1.4 | 创建 _create_substrate_sets() | Not Started | - | 暂缓，待用户确认 |
| 1.5 | 创建 _seed_substrate_part() | Complete | 2026-01-16 | |
| 2.1 | 重构 build_porous_substrate() | Complete | 2026-01-16 | |
| 2.2 | 重构 build_solid_substrate() | Complete | 2026-01-16 | |
| 3.1 | 测试验证 | Not Started | - | 需在 ABAQUS 环境中测试 |

## Progress Log

### 2026-01-16
- 创建任务
- 分析两个函数的公共代码模式
- 确定5个可提取的辅助函数
- 实现 4 个辅助函数（跳过 1.4 等待用户确认）
- 重构两个基底构建函数使用新辅助函数
- 代码无错误

## Design Considerations

### 辅助函数放置位置
有两种选择：
1. **在 substrate.py 顶部**：作为模块私有函数（以 `_` 开头）
2. **在 utils/abaqus_utils.py 中**：如果其他模块也可能使用

**建议：** 先放在 substrate.py 中作为私有函数，如果后续发现 wire.py 等也需要，再迁移到 utils。

### 函数命名规范
- 使用 `_` 前缀表示模块私有函数
- 例如：`_get_or_create_model()`, `_create_pdms_material()`

### 向后兼容
- 保持 `build_porous_substrate()` 和 `build_solid_substrate()` 的 API 不变
- 仅改变内部实现
