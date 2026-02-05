"""
测试 preprocess.config.models 模块的 Pydantic 模型。

这些测试验证配置验证和序列化功能。
"""
import pytest
from pydantic import ValidationError

from abq_serp_sub.preprocess.config.models import (
    SubstrateConfig,
    LoadingConfig,
    WireConfig,
    PoresConfig,
    ComputingConfig,
    AnalysisConfig,
    InteractionConfig,
    OutputConfig,
    NamingConfig,
    Config,
    StepTypeEnum,
    ImplicitApplicationEnum,
    AmplitudeTypeEnum,
    ImplicitDynamicsConfig,
    ExplicitDynamicsConfig,
    DynamicsAnalysisConfig,
)


# region 基底配置测试
class TestSubstrateConfig:
    """基底配置 Pydantic 模型测试"""

    def test_valid_porous_config(self):
        """测试有效多孔配置"""
        config = SubstrateConfig(
            type="porous",
            n_rows=16,
            n_cols=32,
            porosity=0.5,
            depth=0.1,
            seed_size=0.05,
            edge_seed_size=0.02,
            square_size=0.5,
        )
        assert config.n_rows == 16
        assert config.n_cols == 32
        assert config.porosity == 0.5

    def test_valid_solid_config(self):
        """测试有效实心配置"""
        config = SubstrateConfig(
            type="solid",
            length=8.0,
            width=11.0,
            depth=0.8,
            seed_size=0.05,
            edge_seed_size=0.02,
        )
        assert config.length == 8.0
        assert config.width == 11.0

    def test_invalid_porosity_too_high(self):
        """测试孔隙率过高"""
        with pytest.raises(ValidationError):
            SubstrateConfig(
                type="porous",
                n_rows=16,
                n_cols=32,
                porosity=0.9,  # 超过 π/4 ≈ 0.7854
                depth=0.1,
                seed_size=0.05,
                edge_seed_size=0.02,
                square_size=0.5,
            )

    def test_solid_missing_length(self):
        """测试实心基底缺少 length"""
        with pytest.raises(ValidationError):
            SubstrateConfig(
                type="solid",
                width=11.0,  # 缺少 length
                depth=0.8,
                seed_size=0.05,
                edge_seed_size=0.02,
            )

    def test_porous_missing_porosity(self):
        """测试多孔基底缺少 porosity"""
        with pytest.raises(ValidationError):
            SubstrateConfig(
                type="porous",
                n_rows=16,
                n_cols=32,
                # 缺少 porosity
                depth=0.1,
                seed_size=0.05,
                edge_seed_size=0.02,
                square_size=0.5,
            )


# endregion


# region 导线配置测试
class TestWireConfig:
    """导线配置 Pydantic 模型测试"""

    def test_valid_config(self):
        """测试有效配置"""
        config = WireConfig(
            w=0.5,
            l_1=6.0,
            l_2=6.0,
            m=1,
            seed_size=0.05,
            rotation_angle=0.0,
            has_end_caps=True,
            flip_vertical=False,
        )
        assert config.w == 0.5
        assert config.m == 1

    def test_invalid_width(self):
        """测试无效宽度"""
        with pytest.raises(ValidationError):
            WireConfig(
                w=-0.5,  # 必须 > 0
                l_1=6.0,
                l_2=6.0,
                m=1,
                seed_size=0.05,
            )


# endregion


# region 孔隙配置测试
class TestPoresConfig:
    """孔隙配置测试"""

    def test_valid_config(self):
        """测试有效配置"""
        config = PoresConfig(
            use_standard_circles=False,
            T_xi=0.05,
            T_delta=0.06,
            random_seed=42,
        )
        assert config.use_standard_circles is False
        assert config.random_seed == 42

    def test_default_standard_circles(self):
        """测试默认不使用标准圆"""
        config = PoresConfig(
            T_xi=0.0,
            T_delta=0.0,
            random_seed=1,
        )
        assert config.use_standard_circles is False


# endregion


# region 计算配置测试
class TestComputingConfig:
    """计算配置测试"""

    def test_valid_config(self):
        """测试有效配置"""
        config = ComputingConfig(
            num_cpus=8,
            enable_restart=True,
        )
        assert config.num_cpus == 8
        assert config.enable_restart is True

    def test_default_values(self):
        """测试默认值"""
        config = ComputingConfig()
        assert config.num_cpus == 1
        assert config.enable_restart is False


# endregion


# region 动力学分析配置测试
class TestStepTypeEnum:
    """分析步类型枚举测试"""

    def test_enum_values(self):
        """测试枚举值"""
        assert StepTypeEnum.STATIC.value == "static"
        assert StepTypeEnum.IMPLICIT_DYNAMICS.value == "implicit"
        assert StepTypeEnum.EXPLICIT_DYNAMICS.value == "explicit"


class TestImplicitDynamicsConfig:
    """隐式动力学配置测试"""

    def test_valid_config(self):
        """测试有效配置"""
        config = ImplicitDynamicsConfig(
            max_num_inc=10000,
            initial_inc=0.001,
            min_inc=1e-09,
            time_period=1.0,
            application=ImplicitApplicationEnum.QUASI_STATIC,
            amplitude=AmplitudeTypeEnum.RAMP,
            alpha=-0.05,
            nohaf=True,
            nlgeom=True,
        )
        assert config.max_num_inc == 10000
        assert config.alpha == -0.05
        assert config.nohaf is True

    def test_default_values(self):
        """测试默认值"""
        config = ImplicitDynamicsConfig()
        assert config.application == ImplicitApplicationEnum.QUASI_STATIC
        assert config.amplitude == AmplitudeTypeEnum.RAMP
        assert config.alpha is None
        assert config.nohaf is False

    def test_alpha_bounds(self):
        """测试 alpha 参数边界"""
        # alpha 必须在 [-0.41421, 0] 范围内
        with pytest.raises(ValidationError):
            ImplicitDynamicsConfig(alpha=0.1)  # 超过上界

        with pytest.raises(ValidationError):
            ImplicitDynamicsConfig(alpha=-0.5)  # 超过下界


class TestExplicitDynamicsConfig:
    """显式动力学配置测试"""

    def test_valid_config(self):
        """测试有效配置"""
        config = ExplicitDynamicsConfig(
            time_period=1.0,
            scale_factor=0.9,
            linear_bulk_viscosity=0.06,
            quad_bulk_viscosity=1.2,
        )
        assert config.time_period == 1.0
        assert config.scale_factor == 0.9


class TestDynamicsAnalysisConfig:
    """动力学分析整合配置测试"""

    def test_static_config(self):
        """测试静态分析配置"""
        config = DynamicsAnalysisConfig(
            step_type=StepTypeEnum.STATIC,
            static=AnalysisConfig(
                stabilization_magnitude=0.002,
                adaptive_damping_ratio=0.2,
            ),
        )
        assert config.step_type == StepTypeEnum.STATIC
        assert config.static is not None

    def test_implicit_config(self):
        """测试隐式动力学配置"""
        config = DynamicsAnalysisConfig(
            step_type=StepTypeEnum.IMPLICIT_DYNAMICS,
            implicit=ImplicitDynamicsConfig(
                max_num_inc=5000,
                initial_inc=0.01,
            ),
        )
        assert config.step_type == StepTypeEnum.IMPLICIT_DYNAMICS
        assert config.implicit is not None


# endregion


# region 完整配置测试
class TestConfig:
    """完整配置模型测试"""

    def test_modelname_generation(self):
        """测试模型名称自动生成"""
        config = Config(
            substrate=SubstrateConfig(
                type="porous",
                n_rows=16,
                n_cols=32,
                porosity=0.5,
                depth=0.1,
                seed_size=0.05,
                edge_seed_size=0.02,
                square_size=0.5,
            ),
            loading=LoadingConfig(u1=0.1, u2=0.5),
            wire=WireConfig(
                w=0.5,
                l_1=6.0,
                l_2=6.0,
                m=1,
                seed_size=0.05,
            ),
            pores=PoresConfig(
                T_xi=0.0,
                T_delta=0.06,
                random_seed=1,
            ),
            naming=NamingConfig(
                custom_params=["n_rows", "porosity"],
            ),
        )
        # 模型名称应该自动生成
        assert config.modelname != ""
        assert "n16" in config.modelname
        assert "phi0p5" in config.modelname

    def test_extra_fields_ignored(self):
        """测试忽略多余字段（如 hydra 配置）"""
        config = Config(
            substrate=SubstrateConfig(
                type="porous",
                n_rows=16,
                n_cols=32,
                porosity=0.5,
                depth=0.1,
                seed_size=0.05,
                edge_seed_size=0.02,
                square_size=0.5,
            ),
            loading=LoadingConfig(u1=0.1, u2=0.5),
            wire=WireConfig(
                w=0.5,
                l_1=6.0,
                l_2=6.0,
                m=1,
                seed_size=0.05,
            ),
            pores=PoresConfig(
                T_xi=0.0,
                T_delta=0.0,
                random_seed=1,
            ),
            hydra_internal_field="should_be_ignored",  # 额外字段
        )
        assert not hasattr(config, "hydra_internal_field")


# endregion
