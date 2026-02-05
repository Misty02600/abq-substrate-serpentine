"""
测试 core.context 模块的配置类。

这些测试不需要 ABAQUS 环境，可以在普通 Python 中运行。
"""
import pytest
from abq_serp_sub.core.context import (
    # 材料配置
    HyperelasticMaterialConfig,
    ElasticMaterialConfig,
    # 基底配置
    SolidSubstrateGeomConfig,
    SubstrateMeshConfig,
    SolidSubstrateConfig,
    # 导线配置
    RotationCenter,
    WireGeomConfig,
    WireSectionConfig,
    WireMeshConfig,
    WireConfig,
    # 模型配置
    LoadingConfig,
    ComputingConfig,
    InteractionConfig,
    OutputConfig,
    # 分析步配置
    StepType,
    StaticStepConfig,
    AnalysisStepConfig,
)


# region 材料配置测试
class TestHyperelasticMaterialConfig:
    """超弹性材料配置测试"""

    def test_create_pdms_config(self):
        """测试创建 PDMS 材料配置"""
        pdms = HyperelasticMaterialConfig(
            name="pdms",
            c1=0.0694,
            c2=0.0694,
            d=0.0,
        )
        assert pdms.name == "pdms"
        assert pdms.c1 == 0.0694
        assert pdms.c2 == 0.0694
        assert pdms.d == 0.0

    def test_frozen_config(self):
        """测试配置不可变"""
        pdms = HyperelasticMaterialConfig(
            name="pdms",
            c1=0.0694,
            c2=0.0694,
            d=0.0,
        )
        with pytest.raises(AttributeError):
            pdms.name = "new_name"


class TestElasticMaterialConfig:
    """弹性材料配置测试"""

    def test_create_pi_config(self):
        """测试创建 PI 材料配置"""
        pi = ElasticMaterialConfig(
            name="pi",
            youngs_modulus=2.5,
            poissons_ratio=0.34,
        )
        assert pi.name == "pi"
        assert pi.youngs_modulus == 2.5
        assert pi.poissons_ratio == 0.34

    def test_create_cu_config(self):
        """测试创建 Cu 材料配置"""
        cu = ElasticMaterialConfig(
            name="cu",
            youngs_modulus=119.0,
            poissons_ratio=0.34,
        )
        assert cu.name == "cu"
        assert cu.youngs_modulus == 119.0


# endregion


# region 基底配置测试
class TestSolidSubstrateGeomConfig:
    """实心基底几何配置测试"""

    def test_create_config(self):
        """测试创建配置"""
        geom = SolidSubstrateGeomConfig(
            length=8.0,
            width=11.0,
            depth=0.5,
        )
        assert geom.length == 8.0
        assert geom.width == 11.0
        assert geom.depth == 0.5


class TestSubstrateMeshConfig:
    """基底网格配置测试"""

    def test_create_config(self):
        """测试创建配置"""
        mesh = SubstrateMeshConfig(
            seed_size=0.15,
            edge_seed_size=0.05,
        )
        assert mesh.seed_size == 0.15
        assert mesh.edge_seed_size == 0.05


# endregion


# region 导线配置测试
class TestRotationCenter:
    """旋转中心枚举测试"""

    def test_origin_value(self):
        """测试 ORIGIN 值"""
        assert RotationCenter.ORIGIN.value == "origin"

    def test_part_center_value(self):
        """测试 PART_CENTER 值"""
        assert RotationCenter.PART_CENTER.value == "center"


class TestWireGeomConfig:
    """导线几何配置测试"""

    def test_create_config(self):
        """测试创建配置"""
        geom = WireGeomConfig(
            w=0.5,
            l_1=6.0,
            l_2=6.0,
            m=1,
            rotation_angle=0.0,
            rotation_center=RotationCenter.PART_CENTER,
            has_end_caps=False,
            flip_vertical=True,
        )
        assert geom.w == 0.5
        assert geom.l_1 == 6.0
        assert geom.m == 1
        assert geom.rotation_angle == 0.0
        assert geom.rotation_center == RotationCenter.PART_CENTER
        assert geom.has_end_caps is False
        assert geom.flip_vertical is True

    def test_custom_rotation_center(self):
        """测试自定义旋转中心坐标"""
        geom = WireGeomConfig(
            w=0.5,
            l_1=6.0,
            l_2=6.0,
            m=1,
            rotation_angle=45.0,
            rotation_center=(1.0, 2.0, 3.0),
            has_end_caps=True,
            flip_vertical=False,
        )
        assert geom.rotation_center == (1.0, 2.0, 3.0)


class TestWireSectionConfig:
    """导线截面配置测试"""

    def test_create_config(self):
        """测试创建配置"""
        pi = ElasticMaterialConfig(name="pi", youngs_modulus=2.5, poissons_ratio=0.34)
        cu = ElasticMaterialConfig(name="cu", youngs_modulus=119.0, poissons_ratio=0.34)

        section = WireSectionConfig(
            pi_thickness=4e-3,
            cu_thickness=0.3e-3,
            pi_elastic=pi,
            cu_elastic=cu,
        )
        assert section.pi_thickness == 4e-3
        assert section.cu_thickness == 0.3e-3
        assert section.pi_elastic.name == "pi"
        assert section.cu_elastic.name == "cu"


# endregion


# region 分析步配置测试
class TestStepType:
    """分析步类型枚举测试"""

    def test_static_value(self):
        """测试 STATIC 值"""
        assert StepType.STATIC.value == "static"

    def test_implicit_dynamics_value(self):
        """测试 IMPLICIT_DYNAMICS 值"""
        assert StepType.IMPLICIT_DYNAMICS.value == "implicit"

    def test_explicit_dynamics_value(self):
        """测试 EXPLICIT_DYNAMICS 值"""
        assert StepType.EXPLICIT_DYNAMICS.value == "explicit"


class TestStaticStepConfig:
    """静态分析步配置测试"""

    def test_create_config(self):
        """测试创建配置"""
        config = StaticStepConfig(
            max_num_inc=150,
            initial_inc=0.1,
            min_inc=1e-08,
            max_inc=0.5,
        )
        assert config.max_num_inc == 150
        assert config.initial_inc == 0.1
        assert config.min_inc == 1e-08
        assert config.max_inc == 0.5


class TestAnalysisStepConfig:
    """分析步配置容器测试"""

    def test_create_static_step(self):
        """测试创建静态分析步配置"""
        static_config = StaticStepConfig(
            max_num_inc=150,
            initial_inc=0.1,
            min_inc=1e-08,
            max_inc=0.5,
        )
        step = AnalysisStepConfig(
            step_type=StepType.STATIC,
            config=static_config,
            enable_restart=True,
            restart_intervals=5,
            set_time_incrementation=True,
        )
        assert step.step_type == StepType.STATIC
        assert step.config == static_config
        assert step.enable_restart is True
        assert step.restart_intervals == 5
        assert step.set_time_incrementation is True


# endregion


# region 模型配置测试
class TestLoadingConfig:
    """加载配置测试"""

    def test_create_config(self):
        """测试创建配置"""
        loading = LoadingConfig(u1=0.1, u2=0.5)
        assert loading.u1 == 0.1
        assert loading.u2 == 0.5


class TestComputingConfig:
    """计算配置测试"""

    def test_create_config(self):
        """测试创建配置"""
        computing = ComputingConfig(num_cpus=4, enable_restart=True)
        assert computing.num_cpus == 4
        assert computing.enable_restart is True


class TestInteractionConfig:
    """相互作用配置测试"""

    def test_create_config(self):
        """测试创建配置"""
        interaction = InteractionConfig(use_cohesive=False)
        assert interaction.use_cohesive is False


class TestOutputConfig:
    """输出配置测试"""

    def test_create_config(self):
        """测试创建配置"""
        output = OutputConfig(global_output=True)
        assert output.global_output is True


# endregion
