# [TASK002] - 统一分析步创建函数

**Status:** In Progress
**Added:** 2026-01-16
**Updated:** 2026-01-16

## Original Request

创建分析步用一个统一的函数创建，为了区别是第几个分析步，要保存函数调用次数。
- 在函数内部加一个属性保存调用次数
- 通过 `getattr` 获取属性，默认值为 0（避免外部变量）
- 如果是第 1 次调用，自动设置 `name="Step-1"` 和 `previous="Initial"`
- 以此类推，第 n 次调用设置 `name=f"Step-{n}"` 和 `previous=f"Step-{n-1}"`

## Thought Process

### 当前问题
目前有两个独立的函数：
- `create_preload_step()` - 创建 Step-1
- `create_stretch_step()` - 创建 Step-2

这种设计的问题：
1. 如果需要更多分析步，需要创建更多函数
2. 步骤命名需要手动指定，容易出错
3. 代码重复

### 解决方案

使用函数属性（function attribute）来跟踪调用次数：

```python
def create_step(model, config=None, ...):
    # 获取并递增调用计数器
    call_count = getattr(create_step, '_call_count', 0) + 1
    create_step._call_count = call_count

    # 自动设置 name 和 previous
    name = f"Step-{call_count}"
    previous = "Initial" if call_count == 1 else f"Step-{call_count - 1}"

    # 创建分析步...
```

### 需要考虑的问题
1. **计数器重置**：需要提供重置计数器的机制，以便创建新模型时从头开始。
2. **灵活性**：用户仍然可以手动指定 `name` 和 `previous` 来覆盖自动值。
3. **彻底迁移**：不保留原有函数 `create_preload_step` 和 `create_stretch_step`，直接删除并更新所有调用。

## Implementation Plan

- [x] 1.1 创建统一的 `create_step()` 函数，实现自动计数和命名逻辑
- [x] 1.2 实现 `reset_step_counter()` 用于重置计数器
- [x] 1.3 在 `assembly.py` 中移除旧函数，更新 `create_analysis_steps()`
- [x] 1.4 在 `create_analysis_steps()` 中调用 `reset_step_counter()`
- [x] 1.5 添加 `create_stretch_config()` 辅助函数计算拉伸步配置
- [ ] 1.6 测试验证

## Progress Tracking

**Overall Status:** In Progress - 90%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | 创建统一的 create_step() 函数 | Complete | 2026-01-16 | 核心计数与命名逻辑 |
| 1.2 | 实现 reset_step_counter() | Complete | 2026-01-16 | 防止不同模型间计数干扰 |
| 1.3 | 移除旧函数并更新内部调用 | Complete | 2026-01-16 | 移除 create_preload_step 等 |
| 1.4 | 在 create_analysis_steps() 加入重置逻辑 | Complete | 2026-01-16 | 确保计数从1开始 |
| 1.5 | 添加 create_stretch_config() | Complete | 2026-01-16 | 辅助计算拉伸步配置 |
| 1.6 | 测试验证 | Not Started | 2026-01-16 | 待 Abaqus 环境测试 |

## Progress Log

### 2026-01-16
- 创建任务文件
- 分析当前代码结构
- 确定实现方案：使用函数属性存储调用次数
- 实现 `create_step()` 统一函数，支持自动计数和命名
- 实现 `reset_step_counter()` 重置计数器
- 添加 `create_stretch_config()` 辅助函数，用于计算拉伸步的增量配置
- 更新 `create_analysis_steps()` 使用新函数，内部调用 `reset_step_counter()`
- 移除旧函数 `create_preload_step` 和 `create_stretch_step`
- 将 `DEFAULT_PRELOAD_CONFIG` 重命名为 `DEFAULT_STEP_CONFIG`
