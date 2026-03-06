# ============================================================================ #
#                              材料配置类                                      #
# ============================================================================ #
"""
材料相关的配置 dataclass，包括：
  - HyperelasticMaterialConfig: 超弹性材料参数（Mooney-Rivlin 模型）
  - YeohMaterialConfig: 超弹性材料参数（Yeoh 模型）
  - ElasticMaterialConfig: 通用线弹性材料参数

注意：所有配置均不指定默认值，需要显式构造。
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class HyperelasticMaterialConfig:
    """
    超弹性材料参数配置（Mooney-Rivlin 模型）。

    Attributes:
        name: 材料名称
        c1: Mooney-Rivlin 参数 C1
        c2: Mooney-Rivlin 参数 C2
        d: 体积模数参数 D
        density: 密度 (tonne/mm³)，动力学分析时必填
    """
    name: str
    c1: float
    c2: float
    d: float
    density: Optional[float] = None


@dataclass(frozen=True)
class YeohMaterialConfig:
    """
    超弹性材料参数配置（Yeoh 模型）。

    Attributes:
        name: 材料名称
        c10: Yeoh 参数 C10
        c20: Yeoh 参数 C20
        c30: Yeoh 参数 C30
        d1: 体积压缩性参数 D1
        density: 密度 (tonne/mm³)，动力学分析时必填
    """
    name: str
    c10: float
    c20: float
    c30: float
    d1: float
    density: Optional[float] = None


@dataclass(frozen=True)
class ElasticMaterialConfig:
    """
    弹性材料参数配置。

    Attributes:
        name: 材料名称
        youngs_modulus: 弹性模量 E (MPa)
        poissons_ratio: 泊松比 ν
        density: 密度 (tonne/mm³)，动力学分析时必填
    """
    name: str
    youngs_modulus: float
    poissons_ratio: float
    density: Optional[float] = None

