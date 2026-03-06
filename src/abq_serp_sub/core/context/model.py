# ============================================================================ #
#                      蛇形导线-基底模型配置类                                  #
# ============================================================================ #
"""
蛇形导线-基底模型的完整配置 dataclass。

ModelConfig 聚合所有子配置：
  - substrate_config: 基底配置 (SubstrateConfig)
  - wire_config: 导线配置 (WireConfig)
  - computing: 计算配置 (ComputingConfig)
  - interaction: 相互作用配置 (InteractionConfig)
  - steps: 分析步配置列表 (tuple[AnalysisStepConfig, ...])

位移加载现在直接通过 AnalysisStepConfig.displacement 配置到每个分析步中。
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from abq_serp_sub.core.context.substrate import SubstrateConfig
from abq_serp_sub.core.context.wire import WireConfig
from abq_serp_sub.core.context.step import AnalysisStepConfig


class MasterSurface(Enum):
    """主面选择枚举"""
    SUBSTRATE_TOP = "substrate_top"
    WIRE_BOTTOM = "wire_bottom"


class SlidingType(Enum):
    """接触滑移类型枚举"""
    FINITE = "finite"  # 有限滑移（默认）
    SMALL = "small"    # 小滑移


@dataclass(frozen=True)
class ComputingConfig:
    """计算资源配置。"""
    num_cpus: int
    enable_restart: bool


@dataclass(frozen=True)
class CohesiveConfig:
    """Cohesive 接触参数配置。"""
    # 刚度 (Knn, Kss, Ktt)
    stiffness_normal: float = 1.0e6
    stiffness_shear_1: float = 1.0e6
    stiffness_shear_2: float = 1.0e6
    # 损伤起始准则 - 最大应力
    max_stress_normal: float = 1.0
    max_stress_shear_1: float = 1.0
    max_stress_shear_2: float = 1.0
    # 损伤演化
    fracture_energy: float = 0.1
    # 粘性稳定系数
    viscosity_coef: float = 5e-6


@dataclass(frozen=True)
class InteractionConfig:
    """相互作用配置。

    注意: Cohesive 接触仅支持 SMALL 滑移。
    """
    use_cohesive: bool
    master_surface: MasterSurface = MasterSurface.SUBSTRATE_TOP
    sliding: SlidingType = SlidingType.SMALL
    cohesive: Optional[CohesiveConfig] = None


@dataclass(frozen=True)
class ModelConfig:
    """
    蛇形导线-基底模型完整配置。

    Attributes:
        modelname: 模型名称
        substrate_config: 基底配置
        wire_config: 导线配置
        computing: 计算配置
        interaction: 相互作用配置
        steps: 分析步配置列表，按顺序创建（空元组表示不创建分析步）
    """
    modelname: str
    substrate_config: SubstrateConfig
    wire_config: WireConfig
    computing: ComputingConfig
    interaction: InteractionConfig
    steps: tuple[AnalysisStepConfig, ...] = ()
    fix_substrate_bottom_z: bool = False

