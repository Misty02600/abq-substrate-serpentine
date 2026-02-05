# ============================================================================ #
#                              材料配置类                                      #
# ============================================================================ #
"""
材料相关的配置 dataclass，包括：
  - HyperelasticMaterialConfig: 超弹性材料参数（Mooney-Rivlin 模型）
  - ElasticMaterialConfig: 通用线弹性材料参数

注意：所有配置均不指定默认值，需要显式构造。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class HyperelasticMaterialConfig:
    """
    超弹性材料参数配置（Mooney-Rivlin 模型）。

    Attributes:
        name: 材料名称
        c1: Mooney-Rivlin 参数 C1
        c2: Mooney-Rivlin 参数 C2
        d: 体积模数参数 D
    """
    name: str
    c1: float
    c2: float
    d: float


@dataclass(frozen=True)
class ElasticMaterialConfig:
    """
    弹性材料参数配置。

    Attributes:
        name: 材料名称
        youngs_modulus: 弹性模量 E (MPa)
        poissons_ratio: 泊松比 ν
    """
    name: str
    youngs_modulus: float
    poissons_ratio: float
