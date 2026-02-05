"""预定义常用材料配置实例"""
from abq_serp_sub.core.context import (
    HyperelasticMaterialConfig,
    ElasticMaterialConfig,
)

# PDMS 超弹性材料（Mooney-Rivlin 模型）
PDMS = HyperelasticMaterialConfig(
    name="PDMS",
    c1=0.27027,
    c2=0.067568,
    d=0.12,
)

# 聚酰亚胺 (Polyimide) 弹性材料
PI = ElasticMaterialConfig(
    name="PI",
    youngs_modulus=2500.0,
    poissons_ratio=0.27,
)

# 铜 (Copper) 弹性材料
CU = ElasticMaterialConfig(
    name="Cu",
    youngs_modulus=130000.0,
    poissons_ratio=0.34,
)

