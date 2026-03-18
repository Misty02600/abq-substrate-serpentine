"""
Pydantic 配置模型

用于配置文件的类型验证和序列化。
这些模型用于本地 Python 环境（uv 管理），生成 JSON 参数文件后，
ABAQUS Python 只需读取 JSON 并构建现有的 dataclass 配置上下文。

使用流程:
    1. Hydra 加载 YAML 配置
    2. OmegaConf resolver 计算派生值
    3. Pydantic 模型验证类型
    4. 序列化为 JSON 文件
"""
from enum import Enum
from typing import ClassVar, Optional, Tuple, List
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# 参数简写映射（用于生成模型名称）
PARAM_ABBREV: dict[str, str] = {
    "n_rows": "n",
    "porosity": "phi",
    "T_xi": "xi",
    "T_delta": "delta",
    "random_seed": "seed",
    "depth": "d",
    "seed_size": "sub",
    "edge_seed_size": "edge",
    # Cohesive 参数
    "interaction.cohesive.max_stress_normal": "sig",
    "interaction.cohesive.stiffness_normal": "K",
    "interaction.cohesive.fracture_energy": "Gc",
    # 分析步参数
    "steps.0.step_type": "stype",
}


# region 基底配置


class SubstrateTypeEnum(str, Enum):
    """基底类型枚举"""
    SOLID = "solid"
    POROUS = "porous"


class SubstrateMaterialConfig(BaseModel):
    """基底材料配置 (Hyperelastic - Mooney-Rivlin)"""
    name: str = Field(default="PDMS", description="材料名称")
    density: Optional[float] = Field(default=9.7e-10, gt=0, description="密度 (tonne/mm³)，PDMS默认~970 kg/m³")
    c1: float = Field(default=0.27027, description="Mooney-Rivlin C1 参数")
    c2: float = Field(default=0.067568, description="Mooney-Rivlin C2 参数")
    d: float = Field(default=0.12, description="体积压缩性 D 参数")


class SubstrateConfig(BaseModel):
    """基底配置（支持实心和多孔两种类型）"""

    type: SubstrateTypeEnum = Field(
        default=SubstrateTypeEnum.POROUS,
        description="基底类型: solid（实心）或 porous（多孔）"
    )

    # 实心基底参数（type=solid 时使用）
    length: Optional[float] = Field(
        default=None, gt=0, description="基底长度（X方向），实心基底必填"
    )
    width: Optional[float] = Field(
        default=None, gt=0, description="基底宽度（Y方向），实心基底必填"
    )

    # 多孔基底参数（type=porous 时使用）
    n_rows: Optional[int] = Field(
        default=None, ge=1, description="网格行数，多孔基底必填"
    )
    n_cols: Optional[int] = Field(
        default=None, ge=1, description="网格列数，多孔基底必填"
    )
    porosity: Optional[float] = Field(
        default=None, ge=0, le=0.7854, description="孔隙率，多孔基底必填"
    )
    square_size: Optional[float] = Field(
        default=None, gt=0, description="正方形单元边长，多孔基底必填"
    )

    # 通用参数
    depth: float = Field(gt=0, description="基底厚度")
    seed_size: float = Field(gt=0, description="基底布种尺寸")
    edge_seed_size: float = Field(gt=0, description="边缘布种尺寸")
    elem_code: str = Field(
        default="C3D8R",
        description="单元类型代码，如 C3D8R, C3D8RH 等",
    )

    # 材料配置（可选，默认使用 PDMS）
    material: Optional[SubstrateMaterialConfig] = Field(
        default=None, description="材料参数，留空使用 PDMS 默认值"
    )

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> "SubstrateConfig":
        """验证类型特定字段"""
        if self.type == SubstrateTypeEnum.SOLID:
            if self.length is None or self.width is None:
                raise ValueError("实心基底必须指定 length 和 width")
        elif self.type == SubstrateTypeEnum.POROUS:
            if any(v is None for v in [self.n_rows, self.n_cols, self.porosity, self.square_size]):
                raise ValueError("多孔基底必须指定 n_rows, n_cols, porosity, square_size")
            if self.porosity is not None and self.porosity > 0.7854:
                raise ValueError(f"porosity {self.porosity} 超过理论最大值 π/4 ≈ 0.7854")
        return self


# endregion





# region 导线配置


class WireConfig(BaseModel):
    """蛇形导线配置"""

    # 几何参数
    w: float = Field(gt=0, description="导线宽度")
    l_1: float = Field(gt=0, description="水平节距（一个完整周期宽度）")
    l_2: float = Field(gt=0, description="竖直直线段长度")
    m: int = Field(ge=1, description="周期数")
    seed_size: float = Field(gt=0, description="导线布种尺寸")
    rotation_angle: float = Field(default=0, description="旋转角度（度）")
    rotation_center: str | List[float] = Field(
        default="center",
        description="旋转中心: 'origin', 'center', 或 [x, y, z] 坐标"
    )
    has_end_caps: bool = Field(default=True, description="是否有端点圆盘")
    flip_vertical: bool = Field(default=False, description="是否沿水平轴（X轴）翻转")

    @field_validator("rotation_center")
    @classmethod
    def _validate_rotation_center(cls, v):
        if isinstance(v, list):
            if len(v) != 3:
                raise ValueError(
                    f"rotation_center 坐标列表必须包含恰好 3 个元素 [x, y, z]，"
                    f"当前长度为 {len(v)}"
                )
        elif isinstance(v, str) and v not in ("origin", "center"):
            raise ValueError(
                f"rotation_center 字符串仅支持 'origin' 或 'center'，"
                f"当前值为 '{v}'"
            )
        return v

    # 材料参数 - PI 层
    pi_thickness: float = Field(gt=0, default=0.004, description="PI层厚度 (mm)")
    pi_E: Optional[float] = Field(default=None, gt=0, description="PI弹性模量 (MPa)")
    pi_nu: Optional[float] = Field(default=None, gt=0, lt=0.5, description="PI泊松比")
    pi_density: Optional[float] = Field(default=1.42e-9, gt=0, description="PI密度 (tonne/mm³)，默认~1420 kg/m³")

    # 材料参数 - Cu 层
    cu_thickness: float = Field(gt=0, default=0.0003, description="Cu层厚度 (mm)")
    cu_E: Optional[float] = Field(default=None, gt=0, description="Cu弹性模量 (MPa)")
    cu_nu: Optional[float] = Field(default=None, gt=0, lt=0.5, description="Cu泊松比")
    cu_density: Optional[float] = Field(default=8.96e-9, gt=0, description="Cu密度 (tonne/mm³)，默认~8960 kg/m³")


# endregion


# region 孔隙配置


class PoresConfig(BaseModel):
    """孔隙配置"""

    use_standard_circles: bool = Field(
        default=False, description="是否使用标准圆孔排列"
    )
    T_xi: float = Field(ge=0, description="坐标偏差截断上下限")
    T_delta: float = Field(ge=0, description="直径偏差截断上下限")
    random_seed: int = Field(ge=0, description="随机种子")


# endregion


# region 计算配置


class ComputingConfig(BaseModel):
    """计算资源配置"""

    num_cpus: int = Field(ge=1, default=1, description="CPU 核心数")
    enable_restart: bool = Field(default=False, description="是否启用重启动")


# endregion


# region 分析配置


class StepTypeEnum(str, Enum):
    """分析步类型枚举"""
    STATIC = "static"
    IMPLICIT_DYNAMICS = "implicit"
    EXPLICIT_DYNAMICS = "explicit"


class ImplicitApplicationEnum(str, Enum):
    """隐式动力学应用类型"""
    QUASI_STATIC = "QUASI_STATIC"
    MODERATE_DISSIPATION = "MODERATE_DISSIPATION"
    TRANSIENT_FIDELITY = "TRANSIENT_FIDELITY"


class AmplitudeTypeEnum(str, Enum):
    """加载幅值类型"""
    RAMP = "RAMP"
    STEP = "STEP"


class TimeIncrementationMethodEnum(str, Enum):
    """时间增量方法"""
    AUTOMATIC_GLOBAL = "AUTOMATIC_GLOBAL"
    AUTOMATIC_EBE = "AUTOMATIC_EBE"
    FIXED_USER_DEFINED_INC = "FIXED_USER_DEFINED_INC"
    FIXED_EBE = "FIXED_EBE"


class ImplicitDynamicsConfig(BaseModel):
    """隐式动力学分析步配置"""

    max_num_inc: int = Field(ge=1, default=10000, description="最大增量步数")
    initial_inc: float = Field(gt=0, default=0.001, description="初始增量")
    min_inc: float = Field(gt=0, default=1e-09, description="最小增量")
    time_period: float = Field(gt=0, default=1.0, description="分析时间周期")
    application: ImplicitApplicationEnum = Field(
        default=ImplicitApplicationEnum.QUASI_STATIC,
        description="应用类型"
    )
    amplitude: AmplitudeTypeEnum = Field(
        default=AmplitudeTypeEnum.RAMP,
        description="加载幅值类型"
    )
    alpha: Optional[float] = Field(
        default=None,
        ge=-0.41421,
        le=0,
        description="数值阻尼参数 (None 表示 DEFAULT)"
    )
    nohaf: bool = Field(default=False, description="是否禁用 half-increment residual")
    nlgeom: bool = Field(default=True, description="是否启用几何非线性")


class ExplicitDynamicsConfig(BaseModel):
    """显式动力学分析步配置"""

    time_period: float = Field(gt=0, default=1.0, description="分析时间周期")
    time_incrementation_method: TimeIncrementationMethodEnum = Field(
        default=TimeIncrementationMethodEnum.AUTOMATIC_GLOBAL,
        description="时间增量方法"
    )
    improved_dt_method: bool = Field(
        default=True,
        description="是否使用改进的时间步长方法"
    )
    scale_factor: float = Field(
        gt=0, default=1.0,
        description="稳定时间增量的缩放因子"
    )
    linear_bulk_viscosity: float = Field(
        ge=0, default=0.06,
        description="线性体积粘性"
    )
    quad_bulk_viscosity: float = Field(
        ge=0, default=1.2,
        description="二次体积粘性"
    )
    nlgeom: bool = Field(default=True, description="是否启用几何非线性")
    adiabatic: bool = Field(default=False, description="绝热分析")
    user_defined_inc: Optional[float] = Field(
        default=None,
        gt=0,
        description="用户定义的时间增量"
    )


class StaticStepConfig(BaseModel):
    """静态分析步增量配置"""

    max_num_inc: int = Field(ge=1, default=100, description="最大增量步数")
    initial_inc: float = Field(gt=0, default=0.1, description="初始增量")
    min_inc: float = Field(gt=0, default=1e-08, description="最小增量")
    max_inc: float = Field(gt=0, default=1.0, description="最大增量")


class FieldOutputConfig(BaseModel):
    """场输出配置"""

    # 输出变量列表
    variables: List[str] = Field(
        default=["S", "E", "U", "RF"],
        description="场输出变量列表 (如 S, E, U, RF, COORD 等)"
    )
    # 输出频率
    frequency: int = Field(
        ge=1, default=1, description="输出频率 (每 N 个增量步输出一次)"
    )
    # 输出位置
    position: str = Field(
        default="INTEGRATION_POINTS",
        description="输出位置: INTEGRATION_POINTS, NODAL, ELEMENT_CENTROID 等"
    )


class StepConfig(BaseModel):
    """单个分析步配置（用于 TOML/YAML 配置）"""

    name: Optional[str] = Field(
        default=None,
        description="分析步名称，省略时自动命名为 Step-1/Step-2/..."
    )
    previous: Optional[str] = Field(
        default=None,
        description="前序分析步名称，省略时自动推断（首步为 Initial，其余接前一步）"
    )

    step_type: StepTypeEnum = Field(
        default=StepTypeEnum.STATIC,
        description="分析步类型"
    )
    # 位移加载（单侧）
    displacement: Optional[float] = Field(
        default=None,
        description="该分析步施加的位移（单侧），省略时该步不施加位移"
    )
    # 静态分析参数
    max_num_inc: int = Field(ge=1, default=100, description="最大增量步数")
    initial_inc: float = Field(gt=0, default=0.1, description="初始增量")
    min_inc: float = Field(gt=0, default=1e-08, description="最小增量")
    max_inc: float = Field(gt=0, default=1.0, description="最大增量")
    stabilization_magnitude: float = Field(
        gt=0, default=0.002, description="稳定化幅度（耗散能比例法）"
    )
    adaptive_damping_ratio: float = Field(
        gt=0, default=0.2, description="自适应阻尼比"
    )
    # 重启动配置
    enable_restart: bool = Field(default=False, description="是否启用重启动")
    restart_intervals: int = Field(ge=1, default=1, description="重启动间隔")
    set_time_incrementation: bool = Field(
        default=True, description="是否设置时间增量控制"
    )
    ia: Optional[float] = Field(
        default=None,
        gt=0,
        description="通用控制参数 IA，仅覆盖 timeIncrementation 第2项"
    )
    # 隐式/显式动力学参数（可选）
    implicit: Optional[ImplicitDynamicsConfig] = Field(
        default=None, description="隐式动力学配置"
    )
    explicit: Optional[ExplicitDynamicsConfig] = Field(
        default=None, description="显式动力学配置"
    )
    # 场输出配置（可选）
    field_output: Optional[FieldOutputConfig] = Field(
        default=None, description="场输出配置"
    )


# endregion


# region 相互作用配置


class MasterSurfaceEnum(str, Enum):
    """主面选择枚举"""
    SUBSTRATE_TOP = "substrate_top"
    WIRE_BOTTOM = "wire_bottom"


class SlidingTypeEnum(str, Enum):
    """接触滑移类型枚举"""
    FINITE = "finite"  # 有限滑移（默认）
    SMALL = "small"    # 小滑移


class CohesiveConfig(BaseModel):
    """Cohesive 接触参数配置"""

    # 刚度参数 (Knn, Kss, Ktt)
    stiffness_normal: float = Field(
        gt=0, default=1.0e6, description="法向刚度 Knn"
    )
    stiffness_shear_1: float = Field(
        gt=0, default=1.0e6, description="切向刚度 Kss"
    )
    stiffness_shear_2: float = Field(
        gt=0, default=1.0e6, description="切向刚度 Ktt"
    )

    # 损伤起始准则 - 最大应力
    max_stress_normal: float = Field(
        gt=0, default=1.0, description="法向最大应力"
    )
    max_stress_shear_1: float = Field(
        gt=0, default=1.0, description="切向最大应力 1"
    )
    max_stress_shear_2: float = Field(
        gt=0, default=1.0, description="切向最大应力 2"
    )

    # 损伤演化
    fracture_energy: float = Field(
        gt=0, default=0.1, description="断裂能 (N/mm)"
    )

    # 粘性正则化（稳定损伤演化求解）
    viscosity_coef: float = Field(
        ge=0, default=5e-6, description="粘性正则化系数，用于稳定 Cohesive 损伤演化计算"
    )


class InteractionConfig(BaseModel):
    """相互作用配置"""

    use_cohesive: bool = Field(
        default=False, description="是否使用 Cohesive 接触（否则使用 Tie 约束）"
    )

    # 主从面设置
    master_surface: MasterSurfaceEnum = Field(
        default=MasterSurfaceEnum.SUBSTRATE_TOP,
        description="主面选择: substrate_top 或 wire_bottom"
    )

    # 接触滑移类型（use_cohesive=true 时使用）
    # 注意: Cohesive 接触仅支持 SMALL 滑移
    sliding: SlidingTypeEnum = Field(
        default=SlidingTypeEnum.SMALL,
        description="接触滑移类型: finite（有限滑移）或 small（小滑移）。Cohesive 接触仅支持 small"
    )

    # Cohesive 参数（use_cohesive=true 时使用）
    cohesive: Optional[CohesiveConfig] = Field(
        default=None, description="Cohesive 接触参数"
    )

    @model_validator(mode="after")
    def _cohesive_requires_small_sliding(self) -> "InteractionConfig":
        """Cohesive 接触仅支持小滑移。"""
        if self.use_cohesive and self.sliding != SlidingTypeEnum.SMALL:
            raise ValueError(
                "Cohesive 接触仅支持 small 滑移 (sliding=small)，"
                "不能与 finite 滑移一起使用"
            )
        return self


# endregion


# region 命名配置


class NamingConfig(BaseModel):
    """模型命名配置"""

    custom_params: Optional[List[str]] = Field(
        default=None, description="自定义命名参数列表"
    )


# endregion


# region 完整配置


class Config(BaseModel):
    """完整配置模型（顶层）"""

    model_config = ConfigDict(extra="ignore")  # 忽略多余的键（如 hydra 内部配置）

    substrate: SubstrateConfig
    wire: WireConfig
    pores: Optional[PoresConfig] = Field(
        default=None, description="孔隙配置（仅 substrate.type='porous' 时需要）"
    )
    computing: ComputingConfig = Field(default_factory=ComputingConfig)
    interaction: InteractionConfig = Field(default_factory=InteractionConfig)
    naming: NamingConfig = Field(default_factory=NamingConfig)
    fix_substrate_bottom_z: bool = Field(
        default=False,
        description="是否约束基底底面 z 方向位移（施加 u3=0 边界条件）"
    )
    steps: List[StepConfig] = Field(
        default_factory=list, description="分析步配置列表（空列表表示不创建分析步）"
    )

    # 模型名称（生成时设置）
    modelname: str = Field(default="", description="生成的模型名称")

    @model_validator(mode="after")
    def _compute_derived_values(self) -> "Config":
        """计算派生值：modelname"""
        # 自动生成模型名称
        if not self.modelname:
            self.modelname = self._generate_modelname()

        return self

    def _generate_modelname(self) -> str:
        """
        根据配置生成模型名称。

        命名规则:
        - 前缀: std（标准圆孔）或 uni（随机圆孔）
        - 参数: 根据 naming.custom_params 配置
        - 数值格式: 小数点替换为 p（如 0.5 → 0p5）

        Returns
        -------
        str
            生成的模型名称，如 "uni_n16_phi0p5_xi0p0_delta0p06_seed1"。
        """
        # 前缀
        prefix = "std" if self.pores.use_standard_circles else "uni"
        parts = [prefix]

        # 获取要包含的参数
        custom_params = self.naming.custom_params or []

        # 参数值映射
        param_values: dict[str, float | int | str | None] = {
            "n_rows": self.substrate.n_rows,
            "porosity": self.substrate.porosity,
            "T_xi": self.pores.T_xi,
            "T_delta": self.pores.T_delta,
            "random_seed": self.pores.random_seed,
            "depth": self.substrate.depth,
            "seed_size": self.substrate.seed_size,
            "edge_seed_size": self.substrate.edge_seed_size,
        }

        # 添加 Cohesive 参数（如果存在）
        if self.interaction.cohesive:
            coh = self.interaction.cohesive
            param_values["interaction.cohesive.max_stress_normal"] = coh.max_stress_normal
            param_values["interaction.cohesive.stiffness_normal"] = coh.stiffness_normal
            param_values["interaction.cohesive.fracture_energy"] = coh.fracture_energy

        # 添加分析步参数（如果存在）
        if self.steps:
            param_values["steps.0.step_type"] = self.steps[0].step_type.value

        for param in custom_params:
            if param in PARAM_ABBREV and param in param_values:
                abbrev = PARAM_ABBREV[param]
                value = param_values[param]
                # 格式化数值：小数点替换为 p
                if isinstance(value, float):
                    value_str = str(value).replace(".", "p")
                else:
                    value_str = str(value)
                parts.append(f"{abbrev}{value_str}")

        return "_".join(parts)


# endregion
