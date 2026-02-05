"""
parts 子模块

包含部件构建函数:
- substrate: 基底部件构建（含 pores 圆孔生成）
- wire: 蛇形导线部件构建
- material_instances: 预定义材料实例
"""

from abq_serp_sub.core.pores import (
    calculate_circle_radius,
    generate_circles_grid,
    generate_random_center,
    generate_random_diameter_deviation,
    generate_uniform_in_disk,
)
from abq_serp_sub.processes.parts.substrate import (
    build_porous_substrate,
    build_solid_substrate,
    refine_substrate_edges_around_wire,
)
from abq_serp_sub.processes.parts.wire import (
    build_serpentine_wire,
    build_serpentine_wire_no_caps,
)
from abq_serp_sub.processes.parts.material_instances import (
    PDMS,
    PI,
    CU,
)

__all__ = [
    # pores
    "calculate_circle_radius",
    "generate_circles_grid",
    "generate_random_center",
    "generate_random_diameter_deviation",
    "generate_uniform_in_disk",
    # substrate
    "build_porous_substrate",
    "build_solid_substrate",
    "refine_substrate_edges_around_wire",
    # wire
    "build_serpentine_wire",
    "build_serpentine_wire_no_caps",
    # material_instances
    "pdms",
    "pi",
    "cu",
]
