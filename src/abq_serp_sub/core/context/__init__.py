# ============================================================================ #
#                          配置类统一导出                                      #
# ============================================================================ #
"""
core/context 子包

集中管理所有模型构建相关的配置 dataclass，按领域分文件组织：
  - material.py: 材料配置（HyperelasticMaterialConfig, ElasticMaterialConfig）
  - substrate.py: 基底配置（GeomConfig, MeshConfig, 完整配置）
  - wire.py: 导线配置（GeomConfig, SectionConfig, MeshConfig, 完整配置）
  - step.py: 分析步配置（StepType, StepIncrementConfig, ImplicitDynamicsStepConfig, ExplicitDynamicsStepConfig）

使用方式：
    from abq_serp_sub.core.context import PorousSubstrateConfig, WireConfig, StepType
"""

# 材料配置
from abq_serp_sub.core.context.material import (
    HyperelasticMaterialConfig,
    ElasticMaterialConfig,
)

# 基底配置
from abq_serp_sub.core.context.substrate import (
    SolidSubstrateGeomConfig,
    PorousSubstrateGeomConfig,
    SubstrateMeshConfig,
    SubstrateConfig,
    SolidSubstrateConfig,
    PorousSubstrateConfig,
)

# 导线配置
from abq_serp_sub.core.context.wire import (
    RotationCenter,
    WireGeomConfig,
    WireSectionConfig,
    WireMeshConfig,
    WireConfig,
)

# 分析步配置
from abq_serp_sub.core.context.step import (
    # 枚举
    StepType,
    ImplicitApplication,
    AmplitudeType,
    TimeIncrementationMethod,
    # 配置类
    StepIncrementConfig,
    StaticStepConfig,
    ImplicitDynamicsStepConfig,
    ExplicitDynamicsStepConfig,
    # 分析步序列配置
    StepConfigType,
    AnalysisStepConfig,
    # 默认配置工厂函数
    get_default_static_config,
    get_default_implicit_dynamics_config,
    get_default_explicit_dynamics_config,
)

# 模型配置
from abq_serp_sub.core.context.model import (
    LoadingConfig,
    ComputingConfig,
    InteractionConfig,
    OutputConfig,
    ModelConfig,
)

__all__ = [
    # 材料
    "HyperelasticMaterialConfig",
    "ElasticMaterialConfig",
    # 基底
    "SolidSubstrateGeomConfig",
    "PorousSubstrateGeomConfig",
    "SubstrateMeshConfig",
    "SubstrateConfig",
    "SolidSubstrateConfig",
    "PorousSubstrateConfig",
    # 导线
    "RotationCenter",
    "WireGeomConfig",
    "WireSectionConfig",
    "WireMeshConfig",
    "WireConfig",
    # 分析步 - 枚举
    "StepType",
    "ImplicitApplication",
    "AmplitudeType",
    "TimeIncrementationMethod",
    # 分析步 - 配置类
    "StepIncrementConfig",
    "StaticStepConfig",
    "ImplicitDynamicsStepConfig",
    "ExplicitDynamicsStepConfig",
    # 分析步 - 序列配置
    "StepConfigType",
    "AnalysisStepConfig",
    # 分析步 - 默认配置
    "get_default_static_config",
    "get_default_implicit_dynamics_config",
    "get_default_explicit_dynamics_config",
    # 模型配置
    "LoadingConfig",
    "ComputingConfig",
    "InteractionConfig",
    "OutputConfig",
    "ModelConfig",
]
