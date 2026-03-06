"""预定义常用材料配置实例"""
from abq_serp_sub.core.context import (
    HyperelasticMaterialConfig,
    YeohMaterialConfig,
    ElasticMaterialConfig,
)

# PDMS 超弹性材料（Mooney-Rivlin 模型）
# 密度: ~970 kg/m³ = 9.7e-10 tonne/mm³
PDMS = HyperelasticMaterialConfig(
    name="PDMS",
    c1=0.27027,
    c2=0.067568,
    d=0.12,
    density=9.7e-10,
)

# Ecoflex 超弹性材料（Mooney-Rivlin 模型）
# C10=0.00268, C01=0.00067, D1=6
# 密度: ~1070 kg/m³ = 1.07e-9 tonne/mm³
ECOFLEX = HyperelasticMaterialConfig(
    name="Ecoflex",
    c1=0.00268,
    c2=0.00067,
    d=6.0,
    density=1.07e-9,
)

# 聚酰亚胺 (Polyimide) 弹性材料
# 密度: ~1420 kg/m³ = 1.42e-9 tonne/mm³
PI = ElasticMaterialConfig(
    name="PI",
    youngs_modulus=2500.0,
    poissons_ratio=0.27,
    density=1.42e-9,
)

# 铜 (Copper) 弹性材料
# 密度: ~8960 kg/m³ = 8.96e-9 tonne/mm³
CU = ElasticMaterialConfig(
    name="Cu",
    youngs_modulus=130000.0,
    poissons_ratio=0.34,
    density=8.96e-9,
)
