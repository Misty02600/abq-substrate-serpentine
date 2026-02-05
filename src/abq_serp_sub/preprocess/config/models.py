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
}


# region 基底配置


class SubstrateTypeEnum(str, Enum):
    """基底类型枚举"""
    SOLID = "solid"
    POROUS = "porous"


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

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> "SubstrateConfig":
        """验证类型特定字段"""
        if self.type == SubstrateTypeEnum.SOLID:
            if self.length is None or self.width is None:
                raise ValueError("实心基底必须指定 length 和 width")
        elif self.type == SubstrateTypeEnum.POROUS:
            if any(v is None for v in [self.n_rows, self.n_cols, self.porosity, self.square_size]):
                raise ValueError("多孔基底必须指定 n_rows, n_cols, porosity, square_size")
            if self.porosity > 0.7854:
                raise ValueError(f"porosity {self.porosity} 超过理论最大值 π/4 ≈ 0.7854")
        return self


# endregion


# region 加载配置


class LoadingConfig(BaseModel):
    """加载条件配置"""

    u1: float = Field(description="第一步位移（单侧）")
    u2: float = Field(description="第二步位移（单侧）")


# endregion


# region 导线配置


class WireConfig(BaseModel):
    """蛇形导线配置"""

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


class AnalysisConfig(BaseModel):
    """分析步配置（静态步参数）"""

    stabilization_magnitude: float = Field(
        gt=0, default=0.002, description="稳定化幅度"
    )
    adaptive_damping_ratio: float = Field(
        gt=0, default=0.2, description="自适应阻尼比"
    )


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


class DynamicsAnalysisConfig(BaseModel):
    """动力学分析配置（整合静态、隐式、显式）"""

    step_type: StepTypeEnum = Field(
        default=StepTypeEnum.STATIC,
        description="分析步类型"
    )
    # 静态分析配置
    static: Optional[AnalysisConfig] = Field(
        default=None,
        description="静态分析步配置（当 step_type=static 时使用）"
    )
    # 隐式动力学配置
    implicit: Optional[ImplicitDynamicsConfig] = Field(
        default=None,
        description="隐式动力学配置（当 step_type=implicit 时使用）"
    )
    # 显式动力学配置
    explicit: Optional[ExplicitDynamicsConfig] = Field(
        default=None,
        description="显式动力学配置（当 step_type=explicit 时使用）"
    )


class StaticStepConfig(BaseModel):
    """静态分析步增量配置"""

    max_num_inc: int = Field(ge=1, default=100, description="最大增量步数")
    initial_inc: float = Field(gt=0, default=0.1, description="初始增量")
    min_inc: float = Field(gt=0, default=1e-08, description="最小增量")
    max_inc: float = Field(gt=0, default=1.0, description="最大增量")


class StepConfig(BaseModel):
    """单个分析步配置（用于 TOML/YAML 配置）"""

    step_type: StepTypeEnum = Field(
        default=StepTypeEnum.STATIC,
        description="分析步类型"
    )
    # 静态分析参数
    max_num_inc: int = Field(ge=1, default=100, description="最大增量步数")
    initial_inc: float = Field(gt=0, default=0.1, description="初始增量")
    min_inc: float = Field(gt=0, default=1e-08, description="最小增量")
    max_inc: float = Field(gt=0, default=1.0, description="最大增量")
    # 重启动配置
    enable_restart: bool = Field(default=False, description="是否启用重启动")
    restart_intervals: int = Field(ge=1, default=1, description="重启动间隔")
    set_time_incrementation: bool = Field(
        default=True, description="是否设置时间增量控制"
    )
    # 隐式/显式动力学参数（可选）
    implicit: Optional[ImplicitDynamicsConfig] = Field(
        default=None, description="隐式动力学配置"
    )
    explicit: Optional[ExplicitDynamicsConfig] = Field(
        default=None, description="显式动力学配置"
    )


# endregion


# region 相互作用配置


class InteractionConfig(BaseModel):
    """相互作用配置"""

    use_cohesive: bool = Field(
        default=False, description="是否使用 Cohesive 接触（否则使用 Tie 约束）"
    )


# endregion


# region 输出配置


class OutputConfig(BaseModel):
    """输出配置"""

    global_output: bool = Field(
        default=False, description="是否使用全局输出（否则仅 TPC_A 节点）"
    )


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
    loading: LoadingConfig
    wire: WireConfig
    pores: PoresConfig
    computing: ComputingConfig = Field(default_factory=ComputingConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    interaction: InteractionConfig = Field(default_factory=InteractionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    naming: NamingConfig = Field(default_factory=NamingConfig)
    steps: List[StepConfig] = Field(
        default_factory=list, description="分析步配置列表（空列表时使用默认两步配置）"
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
        param_values: dict[str, float | int] = {
            "n_rows": self.substrate.n_rows,
            "porosity": self.substrate.porosity,
            "T_xi": self.pores.T_xi,
            "T_delta": self.pores.T_delta,
            "random_seed": self.pores.random_seed,
            "depth": self.substrate.depth,
            "seed_size": self.substrate.seed_size,
            "edge_seed_size": self.substrate.edge_seed_size,
        }

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
