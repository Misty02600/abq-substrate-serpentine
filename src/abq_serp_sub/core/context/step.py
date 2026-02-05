# ============================================================================ #
#                            分析步配置类                                      #
# ============================================================================ #
"""
分析步相关的配置 dataclass，包括：
  - StepType: 分析步类型枚举（静态/隐式动力学/显式动力学）
  - StepIncrementConfig: 静态分析步增量控制配置（向后兼容）
  - StaticStepConfig: 静态分析步配置（StepIncrementConfig 别名）
  - ImplicitDynamicsStepConfig: 隐式动力学分析步配置
  - ExplicitDynamicsStepConfig: 显式动力学分析步配置

注意：所有配置均不指定默认值，需要显式构造。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StepType(Enum):
    """分析步类型枚举"""
    STATIC = "static"
    IMPLICIT_DYNAMICS = "implicit"
    EXPLICIT_DYNAMICS = "explicit"


# region 静态分析步配置


@dataclass(frozen=True)
class StepIncrementConfig:
    """
    静态分析步增量控制配置（向后兼容）。

    Attributes:
        max_num_inc: 最大增量步数
        initial_inc: 初始增量
        min_inc: 最小增量
        max_inc: 最大增量
    """
    max_num_inc: int
    initial_inc: float
    min_inc: float
    max_inc: float


# 别名，语义更清晰
StaticStepConfig = StepIncrementConfig


# endregion


# region 隐式动力学分析步配置


class ImplicitApplication(Enum):
    """隐式动力学应用类型"""
    QUASI_STATIC = "QUASI_STATIC"
    MODERATE_DISSIPATION = "MODERATE_DISSIPATION"
    TRANSIENT_FIDELITY = "TRANSIENT_FIDELITY"


class AmplitudeType(Enum):
    """加载幅值类型"""
    RAMP = "RAMP"
    STEP = "STEP"


@dataclass(frozen=True)
class ImplicitDynamicsStepConfig:
    """
    隐式动力学分析步配置。

    Attributes:
        max_num_inc: 最大增量步数
        initial_inc: 初始增量
        min_inc: 最小增量
        time_period: 分析时间周期
        application: 应用类型 (QUASI_STATIC, MODERATE_DISSIPATION, TRANSIENT_FIDELITY)
        amplitude: 加载幅值类型 (RAMP, STEP)
        alpha: 数值阻尼参数 (DEFAULT 或 -0.41421 ~ 0)
        nohaf: 是否禁用 half-increment residual
        initial_conditions: 是否从 ODB 读取初始条件
        nlgeom: 是否启用几何非线性
    """
    max_num_inc: int
    initial_inc: float
    min_inc: float
    time_period: float = 1.0
    application: ImplicitApplication = ImplicitApplication.QUASI_STATIC
    amplitude: AmplitudeType = AmplitudeType.RAMP
    alpha: Optional[float] = None  # None 表示 DEFAULT
    nohaf: bool = False
    initial_conditions: bool = False
    nlgeom: bool = True


# endregion


# region 显式动力学分析步配置


class TimeIncrementationMethod(Enum):
    """时间增量方法"""
    AUTOMATIC_GLOBAL = "AUTOMATIC_GLOBAL"
    AUTOMATIC_EBE = "AUTOMATIC_EBE"
    FIXED_USER_DEFINED_INC = "FIXED_USER_DEFINED_INC"
    FIXED_EBE = "FIXED_EBE"


@dataclass(frozen=True)
class ExplicitDynamicsStepConfig:
    """
    显式动力学分析步配置。

    Attributes:
        time_period: 分析时间周期
        time_incrementation_method: 时间增量方法
        improved_dt_method: 是否使用改进的时间步长方法
        scale_factor: 稳定时间增量的缩放因子
        linear_bulk_viscosity: 线性体积粘性（默认 0.06）
        quad_bulk_viscosity: 二次体积粘性（默认 1.2）
        nlgeom: 是否启用几何非线性
        adiabatic: 绝热分析
        user_defined_inc: 用户定义的时间增量（仅当 time_incrementation_method 为 FIXED_USER_DEFINED_INC 时使用）
    """
    time_period: float = 1.0
    time_incrementation_method: TimeIncrementationMethod = TimeIncrementationMethod.AUTOMATIC_GLOBAL
    improved_dt_method: bool = True
    scale_factor: float = 1.0
    linear_bulk_viscosity: float = 0.06
    quad_bulk_viscosity: float = 1.2
    nlgeom: bool = True
    adiabatic: bool = False
    user_defined_inc: Optional[float] = None


# endregion


# region 默认配置实例


def get_default_static_config() -> StaticStepConfig:
    """获取默认静态分析步配置"""
    return StaticStepConfig(
        max_num_inc=150,
        initial_inc=0.1,
        min_inc=1e-08,
        max_inc=0.5,
    )


def get_default_implicit_dynamics_config() -> ImplicitDynamicsStepConfig:
    """获取默认隐式动力学分析步配置"""
    return ImplicitDynamicsStepConfig(
        max_num_inc=10000,
        initial_inc=0.001,
        min_inc=1e-09,
        time_period=1.0,
        application=ImplicitApplication.QUASI_STATIC,
        amplitude=AmplitudeType.RAMP,
        nlgeom=True,
    )


def get_default_explicit_dynamics_config() -> ExplicitDynamicsStepConfig:
    """获取默认显式动力学分析步配置"""
    return ExplicitDynamicsStepConfig(
        time_period=1.0,
        time_incrementation_method=TimeIncrementationMethod.AUTOMATIC_GLOBAL,
        improved_dt_method=True,
        nlgeom=True,
    )


# endregion


# region 分析步序列配置

# 统一的 StepConfig 类型别名
StepConfigType = StepIncrementConfig | ImplicitDynamicsStepConfig | ExplicitDynamicsStepConfig


@dataclass(frozen=True)
class AnalysisStepConfig:
    """
    单个分析步配置。

    用于在 ModelConfig 中以列表形式管理多个分析步。

    Attributes:
        step_type: 分析步类型（静态/隐式动力学/显式动力学）
        config: 对应类型的配置，None 时使用默认值
        enable_restart: 是否启用重启动功能
        restart_intervals: 重启动间隔数
        set_time_incrementation: 是否设置时间增量控制（仅适用于静态步）
    """
    step_type: StepType = StepType.STATIC
    config: StepConfigType | None = None
    enable_restart: bool = False
    restart_intervals: int = 1
    set_time_incrementation: bool = False


# endregion
