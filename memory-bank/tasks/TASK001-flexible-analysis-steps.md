# [TASK001] - 灵活创建分析步

**Status:** Completed
**Added:** 2026-01-15
**Updated:** 2026-01-15

## Original Request
希望把创建分析步独立开来，可以选择创建分析步1和2，而不是固定创建两个步骤。
同时整理参数，区分用户关心的（增量控制）和不关心的（稳定化等固定参数）。

## Thought Process
当前 `create_analysis_steps()` 函数总是同时创建 Step-1 和 Step-2，但实际使用中可能需要：
- 只创建 Step-1（预加载阶段）
- 只创建 Step-2（拉伸阶段）
- 创建两者
- 未来可能需要更多步骤

### 参数分类
**用户关心的（可配置）**：
- `max_num_inc` - 最大增量步数
- `initial_inc` - 初始增量
- `min_inc` - 最小增量
- `max_inc` - 最大增量

**不关心的（固定值）**：
- `name`, `previous` - 步骤标识
- `nlgeom=ON` - 几何非线性
- `stabilizationMagnitude`, `stabilizationMethod`, `continueDampingFactors`, `adaptiveDampingRatio` - 稳定化相关

### 最终方案
使用 `@dataclass` 封装用户关心的参数：
```python
@dataclass
class StepIncrementConfig:
    max_num_inc: int = 150
    initial_inc: float = 0.1
    min_inc: float = 1e-08
    max_inc: float = 0.5
```

## Implementation Plan
- [x] 1. 创建 `StepIncrementConfig` 数据类
- [x] 2. 创建 `create_preload_step()` 函数
- [x] 3. 创建 `create_stretch_step()` 函数
- [x] 4. 保留 `create_analysis_steps()` 作为便捷函数
- [x] 5. 更新 `create_porous_model()` 移除过时参数

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | 创建 `StepIncrementConfig` 数据类 | Complete | 2026-01-15 | 封装用户关心的增量参数 |
| 1.2 | 创建 `create_preload_step()` 函数 | Complete | 2026-01-15 | Step-1 逻辑 |
| 1.3 | 创建 `create_stretch_step()` 函数 | Complete | 2026-01-15 | Step-2 逻辑，含增量自动计算 |
| 1.4 | 保留 `create_analysis_steps()` | Complete | 2026-01-15 | 向后兼容的便捷函数 |
| 1.5 | 更新 `create_porous_model()` | Complete | 2026-01-15 | 移除 stabilization_magnitude 等参数 |

## Progress Log
### 2026-01-15
- 任务创建
- 分析了三种可能的设计方案
- 决定采用方案A：拆分为独立函数
- 根据用户反馈，增加了参数分类的设计
- 创建了 `StepIncrementConfig` 数据类
- 实现了 `create_preload_step()` 和 `create_stretch_step()`
- 保留了 `create_analysis_steps()` 作为便捷函数
- 更新了 `create_porous_model()` 移除过时参数
- 任务完成
