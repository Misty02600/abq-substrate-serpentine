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
    HyperelasticMaterialConfig,
    # 模型配置
    ModelConfig,
    ComputingConfig,
    MasterSurface,
    SlidingType,
    CohesiveConfig as CohesiveDataclass,
    InteractionConfig,
    # 分析步配置
    StepType,
    StaticStepConfig as StaticStepDataclass,
    ImplicitDynamicsStepConfig as ImplicitStepDataclass,
    ExplicitDynamicsStepConfig as ExplicitStepDataclass,
    ImplicitApplication,
    AmplitudeType,
    TimeIncrementationMethod,
    FieldOutputConfig,
    AnalysisStepConfig,
    # 旋转中心
    RotationCenter,
)
from abq_serp_sub.processes.parts.material_instances import PDMS, PI, CU


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

    # 解析材料配置（可选，默认使用 PDMS）
    material = PDMS
    if "material" in substrate and substrate["material"]:
        mat = substrate["material"]
        material = HyperelasticMaterialConfig(
            name=mat.get("name", "PDMS"),
            c1=mat.get("c1", PDMS.c1),
            c2=mat.get("c2", PDMS.c2),
            d=mat.get("d", PDMS.d),
            density=mat.get("density", PDMS.density),
        )

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
            material=material,
            mesh=SubstrateMeshConfig(
                seed_size=substrate["seed_size"],
                edge_seed_size=substrate["edge_seed_size"],
                elem_code=substrate.get("elem_code", "C3D8R"),
            ),
        )
    elif substrate_type == "porous":
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
            material=material,
            mesh=SubstrateMeshConfig(
                seed_size=substrate["seed_size"],
                edge_seed_size=substrate["edge_seed_size"],
                elem_code=substrate.get("elem_code", "C3D8R"),
            ),
        )
    else:
        raise ValueError(
            f"不支持的基底类型: '{substrate_type}'，仅支持 'solid' 或 'porous'"
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

    # 解析 PI 材料配置（可选，默认使用 PI 实例）
    # 使用 or 确保当值为 None 时也使用默认值
    pi_elastic = ElasticMaterialConfig(
        name="PI",
        youngs_modulus=wire.get("pi_E") or PI.youngs_modulus,
        poissons_ratio=wire.get("pi_nu") or PI.poissons_ratio,
        density=wire.get("pi_density") or PI.density,
    )

    # 解析 Cu 材料配置（可选，默认使用 CU 实例）
    cu_elastic = ElasticMaterialConfig(
        name="Cu",
        youngs_modulus=wire.get("cu_E") or CU.youngs_modulus,
        poissons_ratio=wire.get("cu_nu") or CU.poissons_ratio,
        density=wire.get("cu_density") or CU.density,
    )

    wire_section = WireSectionConfig(
        pi_thickness=wire["pi_thickness"],
        cu_thickness=wire["cu_thickness"],
        pi_elastic=pi_elastic,
        cu_elastic=cu_elastic,
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
                stabilization_magnitude=step_dict.get("stabilization_magnitude", 0.002),
                adaptive_damping_ratio=step_dict.get("adaptive_damping_ratio", 0.2),
            )
        elif step_type == StepType.IMPLICIT_DYNAMICS:
            # 隐式动力学：共用参数从顶层读取，专用参数从 implicit 子字典读取
            impl = step_dict.get("implicit") or {}
            app_raw = impl.get("application", "QUASI_STATIC")
            if hasattr(app_raw, "value"):
                app_raw = app_raw.value
            # amplitude 映射
            amp_map = {
                "RAMP": AmplitudeType.RAMP,
                "STEP": AmplitudeType.STEP,
            }
            app_map = {
                "QUASI_STATIC": ImplicitApplication.QUASI_STATIC,
                "MODERATE_DISSIPATION": ImplicitApplication.MODERATE_DISSIPATION,
                "TRANSIENT_FIDELITY": ImplicitApplication.TRANSIENT_FIDELITY,
            }

            config = ImplicitStepDataclass(
                max_num_inc=step_dict.get("max_num_inc", impl.get("max_num_inc", 10000)),
                initial_inc=step_dict.get("initial_inc", impl.get("initial_inc", 0.001)),
                min_inc=step_dict.get("min_inc", impl.get("min_inc", 1e-09)),
                time_period=step_dict.get("time_period", impl.get("time_period", 1.0)),
                application=app_map.get(
                    app_raw,
                    ImplicitApplication.QUASI_STATIC
                ),
                amplitude=amp_map.get(
                    impl.get("amplitude", "RAMP"), AmplitudeType.RAMP
                ),
                alpha=impl.get("alpha", None),
                nohaf=impl.get("nohaf", False),
                initial_conditions=impl.get("initial_conditions", False),
                nlgeom=step_dict.get("nlgeom", impl.get("nlgeom", True)),
            )
        elif step_type == StepType.EXPLICIT_DYNAMICS:
            # 显式动力学：从 explicit 子字典读取参数
            expl = step_dict.get("explicit") or {}

            method_map = {
                "AUTOMATIC_GLOBAL": TimeIncrementationMethod.AUTOMATIC_GLOBAL,
                "AUTOMATIC_EBE": TimeIncrementationMethod.AUTOMATIC_EBE,
                "FIXED_USER_DEFINED_INC": TimeIncrementationMethod.FIXED_USER_DEFINED_INC,
                "FIXED_EBE": TimeIncrementationMethod.FIXED_EBE,
            }

            config = ExplicitStepDataclass(
                time_period=expl.get("time_period", 1.0),
                time_incrementation_method=method_map.get(
                    expl.get("time_incrementation_method", "AUTOMATIC_GLOBAL"),
                    TimeIncrementationMethod.AUTOMATIC_GLOBAL,
                ),
                improved_dt_method=expl.get("improved_dt_method", True),
                scale_factor=expl.get("scale_factor", 1.0),
                linear_bulk_viscosity=expl.get("linear_bulk_viscosity", 0.06),
                quad_bulk_viscosity=expl.get("quad_bulk_viscosity", 1.2),
                nlgeom=expl.get("nlgeom", True),
                adiabatic=expl.get("adiabatic", False),
                user_defined_inc=expl.get("user_defined_inc", None),
            )
        else:
            config = StaticStepDataclass(
                max_num_inc=step_dict.get("max_num_inc", 100),
                initial_inc=step_dict.get("initial_inc", 0.1),
                min_inc=step_dict.get("min_inc", 1e-08),
                max_inc=step_dict.get("max_inc", 1.0),
                stabilization_magnitude=step_dict.get("stabilization_magnitude", 0.002),
                adaptive_damping_ratio=step_dict.get("adaptive_damping_ratio", 0.2),
            )

        # 解析场输出配置
        field_output = None
        if "field_output" in step_dict:
            fo = step_dict["field_output"]
            variables = fo.get("variables", ["S", "E", "U", "RF"])
            # 确保是元组
            if isinstance(variables, list):
                variables = tuple(variables)
            field_output = FieldOutputConfig(
                variables=variables,
                frequency=fo.get("frequency", 1),
                position=fo.get("position", "INTEGRATION_POINTS"),
            )

        step_config = AnalysisStepConfig(
            step_type=step_type,
            config=config,
            displacement=step_dict.get("displacement", None),
            enable_restart=step_dict.get("enable_restart", False),
            restart_intervals=step_dict.get("restart_intervals", 1),
            set_time_incrementation=step_dict.get("set_time_incrementation", True),
            field_output=field_output,
        )
        result.append(step_config)

    return tuple(result)


# 主面映射
MASTER_SURFACE_MAP = {
    "substrate_top": MasterSurface.SUBSTRATE_TOP,
    "wire_bottom": MasterSurface.WIRE_BOTTOM,
}
SLIDING_TYPE_MAP = {
    "finite": SlidingType.FINITE,
    "small": SlidingType.SMALL,
}


def build_interaction_config(interaction_dict: dict) -> InteractionConfig:
    """
    根据配置字典构建相互作用配置。

    Args:
        interaction_dict: interaction 配置字典

    Returns:
        InteractionConfig dataclass
    """
    use_cohesive = interaction_dict.get("use_cohesive", False)

    # 解析主面
    master_str = interaction_dict.get("master_surface", "substrate_top")
    master_surface = MASTER_SURFACE_MAP.get(master_str, MasterSurface.SUBSTRATE_TOP)
    # 解析滑移类型
    sliding_str = interaction_dict.get("sliding", "small")
    if hasattr(sliding_str, "value"):
        sliding_str = sliding_str.value
    sliding = SLIDING_TYPE_MAP.get(sliding_str, SlidingType.SMALL)

    # 解析 Cohesive 参数
    cohesive = None
    if use_cohesive and "cohesive" in interaction_dict:
        coh = interaction_dict["cohesive"]
        cohesive = CohesiveDataclass(
            stiffness_normal=coh.get("stiffness_normal", 1.0e6),
            stiffness_shear_1=coh.get("stiffness_shear_1", 1.0e6),
            stiffness_shear_2=coh.get("stiffness_shear_2", 1.0e6),
            max_stress_normal=coh.get("max_stress_normal", 1.0),
            max_stress_shear_1=coh.get("max_stress_shear_1", 1.0),
            max_stress_shear_2=coh.get("max_stress_shear_2", 1.0),
            fracture_energy=coh.get("fracture_energy", 0.1),
            viscosity_coef=coh.get("viscosity_coef", 5e-6),
        )

    return InteractionConfig(
        use_cohesive=use_cohesive,
        master_surface=master_surface,
        sliding=sliding,
        cohesive=cohesive,
    )


def build_model_config(cfg: dict) -> ModelConfig:
    """根据配置字典构建完整模型配置 dataclass。"""
    # 构建分析步配置（如果存在）
    steps = build_steps_config(cfg.get("steps", []))

    return ModelConfig(
        modelname=cfg["modelname"],
        substrate_config=build_substrate_config(cfg),
        wire_config=build_wire_config(cfg),
        computing=ComputingConfig(
            num_cpus=cfg["computing"]["num_cpus"],
            enable_restart=cfg["computing"]["enable_restart"],
        ),
        interaction=build_interaction_config(cfg.get("interaction", {})),
        steps=steps,
        fix_substrate_bottom_z=cfg.get("fix_substrate_bottom_z", False),
    )
