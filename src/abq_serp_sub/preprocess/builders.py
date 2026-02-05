# ============================================================================ #
#                         配置构建函数                                          #
# ============================================================================ #
"""
从配置字典构建 dataclass 配置对象的函数。

- build_substrate_config: 构建基底配置
- build_wire_config: 构建导线配置
- build_model_config: 构建完整模型配置
"""
import numpy as np

from abq_serp_sub.core.pores import (
    calculate_circle_radius,
    generate_circles_grid,
    generate_circles_grid_standard,
)
from abq_serp_sub.core.context import (
    # 基底配置
    SubstrateConfig,
    SolidSubstrateConfig,
    SolidSubstrateGeomConfig,
    PorousSubstrateConfig,
    PorousSubstrateGeomConfig,
    SubstrateMeshConfig,
    # 导线配置
    WireConfig,
    WireGeomConfig,
    WireSectionConfig,
    WireMeshConfig,
    ElasticMaterialConfig,
    # 模型配置
    ModelConfig,
    LoadingConfig,
    ComputingConfig,
    InteractionConfig,
    OutputConfig,
    # 分析步配置
    StepType,
    StaticStepConfig as StaticStepDataclass,
    AnalysisStepConfig,
    # 旋转中心
    RotationCenter,
)
from abq_serp_sub.processes.parts.material_instances import PDMS


def build_substrate_config(cfg: dict) -> SubstrateConfig:
    """
    根据配置字典构建基底配置 dataclass。

    根据 type 字段判断类型：
    - type == "solid": 实心基底 (SolidSubstrateConfig)
    - type == "porous": 多孔基底 (PorousSubstrateConfig)

    Args:
        cfg: 完整配置字典

    Returns:
        SolidSubstrateConfig 或 PorousSubstrateConfig
    """
    modelname = cfg["modelname"]
    substrate = cfg["substrate"]

    substrate_type = substrate.get("type", "porous")

    if substrate_type == "solid":
        # 实心基底
        return SolidSubstrateConfig(
            modelname=modelname,
            partname="Substrate",
            geom=SolidSubstrateGeomConfig(
                length=substrate["length"],
                width=substrate["width"],
                depth=substrate["depth"],
            ),
            material=PDMS,
            mesh=SubstrateMeshConfig(
                seed_size=substrate["seed_size"],
                edge_seed_size=substrate["edge_seed_size"],
            ),
        )
    else:
        # 多孔基底
        pores = cfg["pores"]
        np.random.seed(pores["random_seed"])
        radius_mean = calculate_circle_radius(substrate["square_size"], substrate["porosity"])

        if pores["use_standard_circles"]:
            circles = generate_circles_grid_standard(
                substrate["n_rows"], substrate["n_cols"],
                substrate["square_size"], radius_mean
            )
        else:
            circles = generate_circles_grid(
                substrate["n_rows"], substrate["n_cols"],
                substrate["square_size"], radius_mean,
                pores["T_xi"], pores["T_delta"],
            )

        return PorousSubstrateConfig(
            modelname=modelname,
            partname="Substrate",
            geom=PorousSubstrateGeomConfig(
                square_size=substrate["square_size"],
                circles=circles,
                depth=substrate["depth"],
            ),
            material=PDMS,
            mesh=SubstrateMeshConfig(
                seed_size=substrate["seed_size"],
                edge_seed_size=substrate["edge_seed_size"],
            ),
        )


def _parse_rotation_center(value) -> RotationCenter | tuple[float, float, float]:
    """
    解析旋转中心配置值。

    Args:
        value: 'origin', 'center', 或 [x, y, z] 列表

    Returns:
        RotationCenter 枚举或 (x, y, z) 坐标元组
    """
    if isinstance(value, str):
        if value.lower() == "origin":
            return RotationCenter.ORIGIN
        elif value.lower() == "center":
            return RotationCenter.PART_CENTER
        else:
            raise ValueError(f"无效的旋转中心字符串: {value}")
    elif isinstance(value, (list, tuple)) and len(value) == 3:
        return tuple(float(v) for v in value)
    else:
        raise ValueError(f"无效的旋转中心值: {value}")

def build_wire_config(cfg: dict) -> WireConfig:
    """根据配置字典构建导线配置 dataclass。"""
    modelname = cfg["modelname"]
    wire = cfg["wire"]

    wire_section = WireSectionConfig(
        pi_thickness=wire["pi_thickness"],
        cu_thickness=wire["cu_thickness"],
        pi_elastic=ElasticMaterialConfig(
            E=wire["pi_E"],
            nu=wire["pi_nu"],
        ),
        cu_elastic=ElasticMaterialConfig(
            E=wire["cu_E"],
            nu=wire["cu_nu"],
        ),
    )

    return WireConfig(
        modelname=modelname,
        partname="Wire",
        geom=WireGeomConfig(
            w=wire["w"],
            l_1=wire["l_1"],
            l_2=wire["l_2"],
            m=wire["m"],
            rotation_angle=wire["rotation_angle"],
            rotation_center=_parse_rotation_center(wire.get("rotation_center", "center")),
            has_end_caps=wire["has_end_caps"],
            flip_vertical=wire["flip_vertical"],
        ),
        section=wire_section,
        mesh=WireMeshConfig(seed_size=wire["seed_size"]),
    )


# 分析步类型映射
STEP_TYPE_MAP = {
    "static": StepType.STATIC,
    "implicit": StepType.IMPLICIT_DYNAMICS,
    "explicit": StepType.EXPLICIT_DYNAMICS,
}


def build_steps_config(steps_list: list[dict]) -> tuple[AnalysisStepConfig, ...]:
    """
    根据配置列表构建分析步配置元组。

    Args:
        steps_list: 分析步配置字典列表

    Returns:
        AnalysisStepConfig 元组
    """
    if not steps_list:
        return ()

    result = []
    for step_dict in steps_list:
        step_type_str = step_dict.get("step_type", "static")
        step_type = STEP_TYPE_MAP.get(step_type_str, StepType.STATIC)

        # 构建静态分析步配置
        if step_type == StepType.STATIC:
            config = StaticStepDataclass(
                max_num_inc=step_dict.get("max_num_inc", 100),
                initial_inc=step_dict.get("initial_inc", 0.1),
                min_inc=step_dict.get("min_inc", 1e-08),
                max_inc=step_dict.get("max_inc", 1.0),
            )
        else:
            # TODO: 支持隐式/显式动力学配置
            config = StaticStepDataclass(
                max_num_inc=step_dict.get("max_num_inc", 100),
                initial_inc=step_dict.get("initial_inc", 0.1),
                min_inc=step_dict.get("min_inc", 1e-08),
                max_inc=step_dict.get("max_inc", 1.0),
            )

        step_config = AnalysisStepConfig(
            step_type=step_type,
            config=config,
            enable_restart=step_dict.get("enable_restart", False),
            restart_intervals=step_dict.get("restart_intervals", 1),
            set_time_incrementation=step_dict.get("set_time_incrementation", True),
        )
        result.append(step_config)

    return tuple(result)


def build_model_config(cfg: dict) -> ModelConfig:
    """根据配置字典构建完整模型配置 dataclass。"""
    # 构建分析步配置（如果存在）
    steps = build_steps_config(cfg.get("steps", []))

    return ModelConfig(
        modelname=cfg["modelname"],
        substrate_config=build_substrate_config(cfg),
        wire_config=build_wire_config(cfg),
        loading=LoadingConfig(
            u1=cfg["loading"]["u1"],
            u2=cfg["loading"]["u2"],
        ),
        computing=ComputingConfig(
            num_cpus=cfg["computing"]["num_cpus"],
            enable_restart=cfg["computing"]["enable_restart"],
        ),
        interaction=InteractionConfig(
            use_cohesive=cfg["interaction"]["use_cohesive"],
        ),
        output=OutputConfig(
            global_output=cfg["output"]["global_output"],
        ),
        steps=steps,
    )
