# ============================================================================ #
#                      蛇形导线-基底模型配置类                                  #
# ============================================================================ #
"""
蛇形导线-基底模型的完整配置 dataclass。

ModelConfig 聚合所有子配置：
  - substrate_config: 基底配置 (SubstrateConfig)
  - wire_config: 导线配置 (WireConfig)
  - loading: 加载配置 (LoadingConfig)
  - computing: 计算配置 (ComputingConfig)
  - interaction: 相互作用配置 (InteractionConfig)
  - output: 输出配置 (OutputConfig)
  - steps: 分析步配置列表 (tuple[AnalysisStepConfig, ...])
"""
from dataclasses import dataclass

from abq_serp_sub.core.context.substrate import SubstrateConfig
from abq_serp_sub.core.context.wire import WireConfig
from abq_serp_sub.core.context.step import AnalysisStepConfig


@dataclass(frozen=True)
class LoadingConfig:
    """加载条件配置。"""
    u1: float
    u2: float


@dataclass(frozen=True)
class ComputingConfig:
    """计算资源配置。"""
    num_cpus: int
    enable_restart: bool


@dataclass(frozen=True)
class InteractionConfig:
    """相互作用配置。"""
    use_cohesive: bool


@dataclass(frozen=True)
class OutputConfig:
    """输出配置。"""
    global_output: bool


@dataclass(frozen=True)
class ModelConfig:
    """
    蛇形导线-基底模型完整配置。

    Attributes:
        modelname: 模型名称
        substrate_config: 基底配置
        wire_config: 导线配置
        loading: 加载配置
        computing: 计算配置
        interaction: 相互作用配置
        output: 输出配置
        steps: 分析步配置列表，按顺序创建（空元组时使用默认两步配置）
    """
    modelname: str
    substrate_config: SubstrateConfig
    wire_config: WireConfig
    loading: LoadingConfig
    computing: ComputingConfig
    interaction: InteractionConfig
    output: OutputConfig
    steps: tuple[AnalysisStepConfig, ...] = ()

