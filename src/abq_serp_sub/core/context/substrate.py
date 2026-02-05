# ============================================================================ #
#                             基底配置类                                       #
# ============================================================================ #
"""
基底相关的配置 dataclass，包括：
  - SolidSubstrateGeomConfig: 实心基底几何参数
  - PorousSubstrateGeomConfig: 多孔基底几何参数
  - SubstrateMeshConfig: 基底网格配置（共用）
  - SolidSubstrateConfig: 实心基底完整配置
  - PorousSubstrateConfig: 多孔基底完整配置

注意：所有配置均不指定默认值，需要显式构造。
"""
from dataclasses import dataclass

import numpy as np

from abq_serp_sub.core.context.material import HyperelasticMaterialConfig


@dataclass(frozen=True)
class SolidSubstrateGeomConfig:
    """
    实心基底几何参数配置。

    Attributes:
        length: 基底长度（X方向）
        width: 基底宽度（Y方向）
        depth: 拉伸深度（Z方向）
    """
    length: float
    width: float
    depth: float


@dataclass(frozen=True)
class PorousSubstrateGeomConfig:
    """
    多孔基底几何参数配置。

    Attributes:
        square_size: 正方形单元边长
        circles: 圆孔数据数组，形状为 (n_rows, n_cols, 3)，每个元素为 (x, y, r)
        depth: 拉伸深度（Z方向）
    """
    square_size: float
    circles: np.ndarray
    depth: float


@dataclass(frozen=True)
class SubstrateMeshConfig:
    """
    基底网格配置（共用）。

    Attributes:
        seed_size: 基底布种尺寸
        edge_seed_size: 边缘细化布种尺寸
    """
    seed_size: float
    edge_seed_size: float


@dataclass(frozen=True)
class SubstrateConfig:
    """
    基底配置基类。

    Attributes:
        modelname: Abaqus 模型名称
        partname: 部件名称
        material: 材料参数配置
        mesh: 网格配置
    """
    modelname: str
    partname: str
    material: HyperelasticMaterialConfig
    mesh: SubstrateMeshConfig


@dataclass(frozen=True)
class SolidSubstrateConfig(SubstrateConfig):
    """
    实心基底完整配置。

    Attributes:
        geom: 实心基底几何参数配置
    """
    geom: SolidSubstrateGeomConfig


@dataclass(frozen=True)
class PorousSubstrateConfig(SubstrateConfig):
    """
    多孔基底完整配置。

    Attributes:
        geom: 多孔基底几何参数配置
    """
    geom: PorousSubstrateGeomConfig

