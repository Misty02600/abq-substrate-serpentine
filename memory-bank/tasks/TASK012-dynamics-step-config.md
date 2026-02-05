# [TASK012] - 动力学分析步配置

**Status:** In Progress
**Added:** 2026-02-02
**Updated:** 2026-02-02

## Original Request

为装配流程提供可选的动力学方法，包括显式（Explicit）和隐式（Implicit）动力学。用户录制的 CAE 脚本参考：

### 隐式动力学（ImplicitDynamicsStep）
```python
mdb.models['Solid-Serpentine-impdy'].ImplicitDynamicsStep(
    name='Step-1',
    previous='Initial',
    maintainAttributes=True,
    maxNumInc=10000,
    application=QUASI_STATIC,  # 关键参数
    initialInc=0.001,
    minInc=1e-09,
    nohaf=OFF,
    amplitude=RAMP,            # 关键参数
    alpha=DEFAULT,
    initialConditions=OFF,
    nlgeom=ON
)
```

### 显式动力学（ExplicitDynamicsStep）
```python
mdb.models['Solid-Serpentine-3-exp-1'].ExplicitDynamicsStep(
    name='Step-1',
    previous='Initial',
    maintainAttributes=True,
    improvedDtMethod=ON
)

# 注意：timeIncrementationMethod 枚举值转换
# AUTOMATIC -> AUTOMATIC_GLOBAL
# 可选值: AUTOMATIC_GLOBAL, FIXED_USER_DEFINED_INC, FIXED_EBE, AUTOMATIC_EBE
```

### 作业配置差异
显式/隐式分析的作业配置基本一致，但 `explicitPrecision` 参数在显式分析中更为重要。

## Thought Process

### 当前状态
- 现有 `create_step()` 函数只支持 **StaticStep**（静态步）
- `StepIncrementConfig` 只包含静态步相关的增量参数
- 需要扩展以支持三种分析步类型：Static、ImplicitDynamics、ExplicitDynamics

### 设计思路

#### 1. 分析步类型枚举
```python
from enum import Enum

class StepType(Enum):
    STATIC = "static"
    IMPLICIT_DYNAMICS = "implicit"
    EXPLICIT_DYNAMICS = "explicit"
```

#### 2. 配置类设计

**方案 A：继承层次结构**
```python
@dataclass
class BaseStepConfig:
    max_num_inc: int
    initial_inc: float
    min_inc: float
    nlgeom: bool = True

@dataclass
class StaticStepConfig(BaseStepConfig):
    max_inc: float
    stabilization_magnitude: float = 0.002
    adaptive_damping_ratio: float = 0.2

@dataclass
class ImplicitDynamicsStepConfig(BaseStepConfig):
    application: str = "QUASI_STATIC"  # QUASI_STATIC, MODERATE_DISSIPATION, TRANSIENT_FIDELITY
    amplitude: str = "RAMP"            # RAMP, STEP
    alpha: str = "DEFAULT"
    nohaf: bool = False
    initial_conditions: bool = False

@dataclass
class ExplicitDynamicsStepConfig:
    time_period: float = 1.0
    time_incrementation_method: str = "AUTOMATIC_GLOBAL"
    improved_dt_method: bool = True
    linear_bulk_viscosity: float = 0.06
    quad_bulk_viscosity: float = 1.2
```

**方案 B：联合配置类（Tagged Union）**
```python
@dataclass
class DynamicsStepConfig:
    step_type: StepType
    # 公共参数
    max_num_inc: int = 10000
    initial_inc: float = 0.001
    min_inc: float = 1e-08
    nlgeom: bool = True

    # 隐式动力学专用
    application: str | None = None      # QUASI_STATIC, etc.
    amplitude: str | None = None        # RAMP, STEP

    # 显式动力学专用
    time_period: float | None = None
    time_incrementation_method: str | None = None
    improved_dt_method: bool | None = None
```

#### 3. 推荐方案

采用 **方案 A（继承结构）**，原因：
- 类型安全，每种步类型有明确的参数集
- 避免可选字段的 None 检查
- 与现有 `StepIncrementConfig` 保持一致的风格
- 更易于 IDE 自动补全和类型检查

#### 4. 函数接口设计

```python
def create_dynamics_step(
    model: "Model",
    step_type: StepType,
    config: BaseStepConfig | None = None,
    name: str | None = None,
    previous: str | None = None,
) -> Step:
    """创建动力学分析步（支持静态、隐式、显式）"""

    if step_type == StepType.STATIC:
        return _create_static_step(model, config, name, previous)
    elif step_type == StepType.IMPLICIT_DYNAMICS:
        return _create_implicit_dynamics_step(model, config, name, previous)
    elif step_type == StepType.EXPLICIT_DYNAMICS:
        return _create_explicit_dynamics_step(model, config, name, previous)
```

### 需要考虑的问题

1. **向后兼容性**：保留现有 `create_step()` 作为默认静态步创建
2. **配置文件集成**：需要在 Pydantic 模型（`models.py`）中添加对应配置
3. **作业类型**：显式分析可能需要不同的作业参数

## Implementation Plan

- [ ] 1.1 创建 `StepType` 枚举（`core/context/step.py`）
- [ ] 1.2 创建 `ImplicitDynamicsStepConfig` 配置类
- [ ] 1.3 创建 `ExplicitDynamicsStepConfig` 配置类
- [ ] 1.4 实现 `_create_implicit_dynamics_step()` 内部函数
- [ ] 1.5 实现 `_create_explicit_dynamics_step()` 内部函数
- [ ] 1.6 创建统一的 `create_dynamics_step()` 函数
- [ ] 1.7 更新 `assembly.py` 支持动力学步骤选项
- [ ] 1.8 在 Pydantic `models.py` 中添加动力学配置模型
- [ ] 1.9 更新 `create_analysis_steps()` 支持 step_type 参数
- [ ] 1.10 测试验证

## Progress Tracking

**Overall Status:** In Progress - 90%

### Subtasks
| ID   | Description                     | Status      | Updated    | Notes                           |
| ---- | ------------------------------- | ----------- | ---------- | ------------------------------- |
| 1.1  | 创建 StepType 枚举              | Complete    | 2026-02-02 | 静态/隐式/显式                  |
| 1.2  | 创建 ImplicitDynamicsStepConfig | Complete    | 2026-02-02 | 隐式动力学配置类                |
| 1.3  | 创建 ExplicitDynamicsStepConfig | Complete    | 2026-02-02 | 显式动力学配置类                |
| 1.4  | 实现隐式动力学步创建函数        | Complete    | 2026-02-02 | create_implicit_dynamics_step() |
| 1.5  | 实现显式动力学步创建函数        | Complete    | 2026-02-02 | create_explicit_dynamics_step() |
| 1.6  | 创建统一入口函数                | Complete    | 2026-02-02 | create_dynamics_step()          |
| 1.7  | 更新 assembly.py                | Complete    | 2026-02-02 | 导入路径修复 + 新函数           |
| 1.8  | 更新 Pydantic models.py         | Complete    | 2026-02-02 | 4 个枚举 + 4 个配置类           |
| 1.9  | 更新 create_analysis_steps()    | Complete    | 2026-02-02 | 支持 step_type 参数             |
| 1.10 | 测试验证                        | Not Started | 2026-02-02 | 待 ABAQUS 环境测试              |

## Progress Log

### 2026-02-02
- 任务创建
- 分析用户录制的 CAE 脚本
- 识别 ImplicitDynamicsStep 和 ExplicitDynamicsStep 的关键参数
- 设计配置类继承结构方案
- 制定实施计划（10 个子任务）
- ✅ 实现 `StepType` 枚举（STATIC, IMPLICIT_DYNAMICS, EXPLICIT_DYNAMICS）
- ✅ 实现辅助枚举：`ImplicitApplication`, `AmplitudeType`, `TimeIncrementationMethod`
- ✅ 创建 `ImplicitDynamicsStepConfig` 配置类
- ✅ 创建 `ExplicitDynamicsStepConfig` 配置类
- ✅ 添加默认配置工厂函数
- ✅ 更新 `core/context/__init__.py` 导出所有新类型
- ✅ 实现 `create_implicit_dynamics_step()` 函数
- ✅ 实现 `create_explicit_dynamics_step()` 函数
- ✅ 实现 `create_dynamics_step()` 统一入口函数
- ✅ 添加 `reset_all_step_counters()` 重置所有计数器
- ✅ 修复 assembly.py 的导入路径（`.configs` → `..core.context`）
- ✅ 更新 `create_analysis_steps()` 支持 `step_type` 参数
- ✅ 在 Pydantic `models.py` 添加动力学配置模型

## References

### ABAQUS API 参考

**ImplicitDynamicsStep 参数**:
- `application`: QUASI_STATIC, MODERATE_DISSIPATION, TRANSIENT_FIDELITY
- `amplitude`: RAMP, STEP
- `alpha`: DEFAULT, -0.41421 ~ 0
- `nohaf`: 是否禁用 half-increment residual
- `initialConditions`: 是否从 ODB 读取初始条件

**ExplicitDynamicsStep 参数**:
- `timeIncrementationMethod`: AUTOMATIC_GLOBAL, FIXED_USER_DEFINED_INC, FIXED_EBE, AUTOMATIC_EBE
- `improvedDtMethod`: 改进的时间步长方法
- `linearBulkViscosity`: 线性体积粘性（默认 0.06）
- `quadBulkViscosity`: 二次体积粘性（默认 1.2）
- `scaleFactor`: 稳定时间增量的缩放因子
