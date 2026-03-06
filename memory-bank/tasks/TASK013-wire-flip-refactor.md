# [TASK013] - Wire 部件翻转方案重构

**Status:** In Progress
**Added:** 2026-02-06
**Updated:** 2026-02-06

## Original Request

当前 wire 部件的翻转不令人满意，需要新实现方案。

## 问题描述

当前的翻转实现（`flip_vertical`）通过绕 X 轴旋转 180° 实现，存在以下问题：

1. **集合颠倒**：旋转后 `Top` 和 `Bottom` 边集合的位置会颠倒
2. **复合层参考方向失效**：`ReferenceOrientation` 依赖 `Top` surface 和 `Bottom` 集合
3. **临时修复**：当前通过旋转后重新调整 Z 位置来解决，但集合问题无法解决

## Thought Process

### 当前实现（assembly.py 第 149-165 行）

```python
if wire_config.geom.flip_vertical:
    asm.rotate(
        instanceList=('Wire-1',),
        axisPoint=wire_center,
        axisDirection=(1.0, 0.0, 0.0),  # 绕 X 轴
        angle=180.0
    )
    # 旋转后重新调整 Z 位置
    wire_bbox_new = get_bounding_box(wire_inst)
    z_offset = sub_bbox['high'][2] - wire_bbox_new['low'][2]
    asm.translate(instanceList=('Wire-1',), vector=(0.0, 0.0, z_offset))
```

### 方案讨论（2026-02-06）

讨论了四种方案：

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A | 草图阶段 Y 坐标翻转 | 集合正确；Z方向不变 | 需修改草图逻辑 |
| B | 旋转后交换集合 | 不改几何代码 | 复杂；易遗漏 |
| C | 语义中性命名 | 兼容翻转 | 改命名约定 |
| D | Part 级别镜像 | ABAQUS 原生 | 可能影响网格 |

**最终决定：采用方案 A**

### 方案 A 实现细节

在草图坐标计算阶段，如果 `flip_vertical=True`，将 Y 坐标取负：

```python
# 翻转逻辑（应用于坐标计算之后）
if flip_vertical:
    y_bot, y_top = -y_top, -y_bot  # 交换并取负
```

**关键保证**：
- 外边界（Top 集合）始终在几何外侧
- 内边界（Bottom 集合）始终在几何内侧
- PI-Cu-PI 层叠顺序不变（Z 方向不变）
- 无需在 assembly 阶段做任何翻转操作

## Implementation Plan

- [x] 1. 分析当前草图生成逻辑
- [x] 2. 确定最佳翻转实现方案（方案 A）
- [x] 3. 修改 `build_serpentine_wire` 函数（带端盘）
- [x] 4. 修改 `build_serpentine_wire_no_caps` 函数（无端盘）
- [x] 5. 移除 `assembly.py` 中的旧翻转逻辑
- [ ] 6. 测试验证

## Progress Tracking

**Overall Status:** In Progress - 85%

### Subtasks
| ID  | Description                       | Status      | Updated    | Notes                        |
| --- | --------------------------------- | ----------- | ---------- | ---------------------------- |
| 1   | 分析草图生成逻辑                  | Complete    | 2026-02-06 | 已完成代码分析               |
| 2   | 确定翻转方案                      | Complete    | 2026-02-06 | 采用方案 A                   |
| 3   | 修改 build_serpentine_wire        | Complete    | 2026-02-06 | 添加 Y 坐标翻转逻辑          |
| 4   | 修改 build_serpentine_wire_no_caps| Complete    | 2026-02-06 | 添加 Y 坐标翻转逻辑          |
| 5   | 移除 assembly.py 旧翻转逻辑       | Complete    | 2026-02-06 | 改为注释说明                 |
| 6   | 测试验证                          | Not Started | -          | 需在 ABAQUS 环境验证         |

## Progress Log

### 2026-02-06
- 任务创建
- 分析了四种可能的翻转方案
- 与用户讨论后确定采用方案 A：草图阶段 Y 坐标翻转
- 确认方案 A 可以保证集创建不出错
- 实施代码修改：
  - `wire.py`: 在 `build_serpentine_wire` 中添加 `flip_vertical` Y 坐标翻转逻辑
  - `wire.py`: 在 `build_serpentine_wire_no_caps` 中添加相同逻辑
  - `assembly.py`: 移除旧的绕 X 轴旋转 180° 翻转代码，改为注释说明
- 待用户在 ABAQUS 环境验证
