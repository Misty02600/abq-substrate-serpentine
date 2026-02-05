"""
蛇形导线相关的配置 dataclass，包括：
  - RotationCenter: 旋转中心枚举（origin/center）
  - WireGeomConfig: 蛇形线几何参数 (w, l_1, l_2, m, origin)
  - WireSectionConfig: 复合层截面配置（厚度 + 弹性属性）
  - WireMeshConfig: 网格配置（布种尺寸）
  - WireConfig: 聚合包装类（含 modelname, partname）

注意：所有配置均不指定默认值，需要显式构造。
"""
from dataclasses import dataclass
from enum import Enum

from abq_serp_sub.core.context.material import ElasticMaterialConfig


class RotationCenter(Enum):
    """旋转中心枚举"""
    ORIGIN = "origin"       # 绕草图原点旋转
    PART_CENTER = "center"  # 绕部件几何中心旋转


@dataclass(frozen=True)
class WireGeomConfig:
    """
    蛇形导线几何参数配置。

    Attributes:
        w: 蛇形线宽
        l_1: 单元体水平节距（一个完整周期宽度）
        l_2: 竖直直线段长度
        m: 周期数
        rotation_angle: 旋转角度（度）
        rotation_center: 旋转中心（枚举或具体坐标）
        has_end_caps: 是否有端点圆盘
        flip_vertical: 是否沿水平轴（X轴）翻转
    """
    w: float
    l_1: float
    l_2: float
    m: int
    rotation_angle: float
    rotation_center: RotationCenter | tuple[float, float, float]
    has_end_caps: bool
    flip_vertical: bool


@dataclass(frozen=True)
class WireSectionConfig:
    """
    蛇形导线复合层截面配置（PI-Cu-PI 复合壳）。

    Attributes:
        pi_thickness: PI 单层厚度（上下两层相同）
        cu_thickness: Cu 单层厚度（中间层）
        pi_elastic: PI 材料弹性参数
        cu_elastic: Cu 材料弹性参数
    """
    pi_thickness: float
    cu_thickness: float
    pi_elastic: ElasticMaterialConfig
    cu_elastic: ElasticMaterialConfig


@dataclass(frozen=True)
class WireMeshConfig:
    """
    蛇形导线网格配置。

    Attributes:
        seed_size: 蛇形线布种尺寸
    """
    seed_size: float


@dataclass(frozen=True)
class WireConfig:
    """
    蛇形导线完整配置（聚合类）。

    Attributes:
        modelname: Abaqus 模型名称
        partname: 部件名称
        geom: 几何参数配置
        section: 复合层截面配置
        mesh: 网格配置
    """
    modelname: str
    partname: str
    geom: WireGeomConfig
    section: WireSectionConfig
    mesh: WireMeshConfig
