from __future__ import annotations
import os
import sys
from pathlib import Path
import inspect
from typing import TYPE_CHECKING

import section
import regionToolset
import displayGroupMdbToolset as dgm
import part
import material
import assembly
import step
import interaction
import load
import mesh
import optimization
import job
import sketch
import visualization
import xyPlot
import displayGroupOdbToolset as dgo
import connectorBehavior
from abaqus import *
from abaqusConstants import *

if TYPE_CHECKING:
    from abaqus.Model.Model import Model

# 脚本所在目录：noGUI 里 __file__ 一定有；Run Script 时看 ② 退路
try:                                    # ① 绝大多数情况下
    SCRIPT_DIR = Path(__file__).parent.resolve()
except NameError:                       # ② 只有 GUI ▸ Run Script 才会进这里
    import os
    fname = inspect.getfile(inspect.currentframe())
    SCRIPT_DIR = Path(fname).parent.resolve() if not fname.startswith('<')\
                 else Path(os.getcwd()).resolve()

# 把脚本目录放到 import 搜索路径最前
sys.path.append(str(SCRIPT_DIR))

from abq_serp_sub.processes.parts.substrate import build_substrate, refine_substrate_edges_around_wire
from abq_serp_sub.utils.abaqus_utils import get_bounding_box
from abq_serp_sub.processes.parts.wire import build_serpentine_wire, build_serpentine_wire_no_caps

# 配置类从 core.context 子包导入
from abq_serp_sub.core.context import (
    # 基底配置
    SolidSubstrateConfig,
    SolidSubstrateGeomConfig,
    PorousSubstrateConfig,
    SubstrateMeshConfig,
    # 导线配置
    RotationCenter,
    WireConfig,
    WireGeomConfig,
    WireSectionConfig,
    WireMeshConfig,
    # 分析步配置
    StepType,
    StaticStepConfig,
    AnalysisStepConfig,
    # 模型配置
    ModelConfig,
    LoadingConfig,
    ComputingConfig,
    InteractionConfig,
    OutputConfig,
)

# 分析步创建函数
from abq_serp_sub.processes.steps import (
    create_step,
    create_implicit_dynamics_step,
    create_explicit_dynamics_step,
    create_dynamics_step,
    reset_all_step_counters,
    create_stretch_config,
    create_analysis_steps,
    create_steps_from_configs,
    setup_field_outputs,
)


# 配置构建函数从 preprocess.builders 导入
from abq_serp_sub.preprocess.builders import (
    build_substrate_config,
    build_wire_config,
    build_model_config,
)


# region 创建蛇形导线-基底模型
def create_model(config: ModelConfig) -> "Model":
    """
    使用配置对象创建蛇形导线-基底模型。

    Args:
        config: ModelConfig 配置对象

    Returns:
        Model: 创建的模型对象
    """
    # 解构配置
    modelname = config.modelname
    substrate_config = config.substrate_config
    wire_config = config.wire_config
    loading = config.loading
    computing = config.computing
    interaction = config.interaction
    output = config.output
    steps = config.steps

    # region 初始化和模型创建
    print(f"正在创建模型: {modelname}")
    model = mdb.Model(name=modelname)
    # endregion

    # region 部件创建
    sub_part = build_substrate(substrate_config)

    if wire_config.geom.has_end_caps:
        wire_part = build_serpentine_wire(wire_config)
    else:
        wire_part = build_serpentine_wire_no_caps(wire_config)

    asm = model.rootAssembly
    sub_inst = asm.Instance(name="Substrate-1", part=sub_part, dependent=ON)
    wire_inst = asm.Instance(name="Wire-1", part=wire_part, dependent=ON)

    # 将导线居中于基底
    sub_bbox = get_bounding_box(sub_inst)
    wire_bbox = get_bounding_box(wire_inst)

    sub_center = tuple((low + high) / 2 for low, high in zip(sub_bbox['low'], sub_bbox['high']))
    wire_center = tuple((low + high) / 2 for low, high in zip(wire_bbox['low'], wire_bbox['high']))

    # 计算偏移（X, Y 居中，Z 移到基底顶面）
    offset = (
        sub_center[0] - wire_center[0],
        sub_center[1] - wire_center[1],
        sub_bbox['high'][2] - wire_bbox['low'][2],  # 导线底面贴合基底顶面
    )
    asm.translate(instanceList=('Wire-1',), vector=offset)
    print(f"Wire 已居中于基底，偏移: {offset}")

    # 垂直翻转（沿 X 轴旋转 180°）
    if wire_config.geom.flip_vertical:
        wire_bbox = get_bounding_box(wire_inst)
        wire_center = tuple((low + high) / 2 for low, high in zip(wire_bbox['low'], wire_bbox['high']))
        asm.rotate(
            instanceList=('Wire-1',),
            axisPoint=wire_center,
            axisDirection=(1.0, 0.0, 0.0),  # 绕 X 轴
            angle=180.0
        )
        print("Wire 已沿水平轴翻转")

    # 旋转 Wire 实例（居中后再旋转）
    rotation_angle = wire_config.geom.rotation_angle
    if rotation_angle != 0.0:
        # 重新获取翻转后的 bounding box
        wire_bbox = get_bounding_box(wire_inst)
        wire_center = tuple((low + high) / 2 for low, high in zip(wire_bbox['low'], wire_bbox['high']))

        # 解析旋转中心
        rc = wire_config.geom.rotation_center
        match rc:
            case RotationCenter.ORIGIN:
                # ORIGIN 现在指居中后的导线中心
                axis_point = wire_center
            case RotationCenter.PART_CENTER:
                axis_point = wire_center
            case (x, y, z):
                axis_point = (x, y, z)

        asm.rotate(
            instanceList=('Wire-1',),
            axisPoint=axis_point,
            axisDirection=(0.0, 0.0, 1.0),
            angle=rotation_angle
        )
        print(f"Wire实例已旋转 {rotation_angle} 度，旋转中心: {axis_point}")

    # 细化导线周围的基底边（仅对多孔基底）
    if isinstance(substrate_config, PorousSubstrateConfig):
        wire_bbox = get_bounding_box(wire_inst)
        wire_x_min, wire_y_min, wire_z_min = wire_bbox['low']
        wire_x_max, wire_y_max, wire_z_max = wire_bbox['high']
        wire_y_min -= wire_config.geom.w / 2
        wire_y_max += wire_config.geom.w / 2
        wire_bounds = (wire_x_min, wire_y_min, wire_z_min, wire_x_max, wire_y_max, wire_z_max)

        refine_substrate_edges_around_wire(
            modelname=modelname,
            partname="Substrate",
            wire_bounds=wire_bounds,
            substrate_edge_seed_size=substrate_config.mesh.edge_seed_size,
        )
    # endregion

    # region 分析步&场输出
    if steps:
        # 使用配置列表创建分析步
        create_steps_from_configs(model=model, step_configs=steps)
    else:
        # 向后兼容：使用默认两步配置
        create_analysis_steps(
            model=model,
            u1=loading.u1,
            u2=loading.u2,
            enable_restart=computing.enable_restart,
        )

    setup_field_outputs(
        model=model,
        modelname=modelname,
        global_output=output.global_output,
    )
    # endregion

    # region 相互作用
    if interaction.use_cohesive:
        mdb.models[modelname].ContactProperty('IntProp-1')
        mdb.models[modelname].interactionProperties['IntProp-1'].CohesiveBehavior()
        mdb.models[modelname].ContactStd(name='Int-1', createStepName='Initial')
        mdb.models[modelname].interactions['Int-1'].includedPairs.setValuesInStep(
            stepName='Initial', useAllstar=ON)
        mdb.models[modelname].interactions['Int-1'].contactPropertyAssignments.appendInStep(
            stepName='Initial', assignments=((GLOBAL, SELF, 'IntProp-1'), ))
    else:
        mdb.models[modelname].Tie(
            name="Constraint-1",
            main=sub_inst.surfaces["TopFace"],
            secondary=wire_inst.surfaces["Bottom"],
            positionToleranceMethod=COMPUTED,
            adjust=ON,
            tieRotations=ON,
            thickness=ON,
        )
    # endregion

    # region 边界条件
    mdb.models[modelname].DisplacementBC(
        name="TPC_A",
        createStepName="Initial",
        region=sub_inst.sets["TPC_A"],
        u1=UNSET, u2=SET, u3=SET,
        ur1=UNSET, ur2=UNSET, ur3=UNSET,
        amplitude=UNSET, distributionType=UNIFORM,
        fieldName="", localCsys=None,
    )

    mdb.models[modelname].DisplacementBC(
        name="TPC_B",
        createStepName="Initial",
        region=sub_inst.sets["TPC_B"],
        u1=UNSET, u2=UNSET, u3=SET,
        ur1=UNSET, ur2=UNSET, ur3=UNSET,
        amplitude=UNSET, distributionType=UNIFORM,
        fieldName="", localCsys=None,
    )

    mdb.models[modelname].DisplacementBC(
        name="left-U",
        createStepName="Initial",
        region=sub_inst.sets["LeftFace"],
        u1=SET, u2=UNSET, u3=UNSET,
        ur1=UNSET, ur2=UNSET, ur3=UNSET,
        amplitude=UNSET, distributionType=UNIFORM,
        fieldName="", localCsys=None,
    )
    mdb.models[modelname].boundaryConditions["left-U"].setValuesInStep(
        stepName="Step-1", u1=-loading.u1
    )
    mdb.models[modelname].boundaryConditions["left-U"].setValuesInStep(
        stepName="Step-2", u1=-loading.u2
    )

    mdb.models[modelname].DisplacementBC(
        name="right-U",
        createStepName="Initial",
        region=sub_inst.sets["RightFace"],
        u1=SET, u2=UNSET, u3=UNSET,
        ur1=UNSET, ur2=UNSET, ur3=UNSET,
        amplitude=UNSET, distributionType=UNIFORM,
        fieldName="", localCsys=None,
    )
    mdb.models[modelname].boundaryConditions["right-U"].setValuesInStep(
        stepName="Step-1", u1=loading.u1
    )
    mdb.models[modelname].boundaryConditions["right-U"].setValuesInStep(
        stepName="Step-2", u1=loading.u2
    )
    # endregion

    # region 作业创建
    num_cpus = computing.num_cpus
    mdb.Job(
        name=modelname,
        model=modelname,
        description=f'Analysis job for model {modelname}',
        type=ANALYSIS,
        atTime=None,
        waitMinutes=0,
        waitHours=0,
        queue=None,
        memory=90,
        memoryUnits=PERCENTAGE,
        getMemoryFromAnalysis=True,
        explicitPrecision=SINGLE,
        nodalOutputPrecision=SINGLE,
        echoPrint=OFF,
        modelPrint=OFF,
        contactPrint=OFF,
        historyPrint=OFF,
        userSubroutine='',
        scratch='',
        resultsFormat=ODB,
        numThreadsPerMpiProcess=1,
        multiprocessingMode=DEFAULT,
        numCpus=num_cpus,
        numDomains=num_cpus,
        numGPUs=0
    )
    # endregion

    print(f"模型 {modelname} 创建完成")
    return model


def create_model_from_dict(cfg: dict) -> "Model":
    """
    从配置字典创建蛇形导线-基底模型（便捷函数）。

    Args:
        cfg: 配置字典

    Returns:
        Model: 创建的模型对象
    """
    config = build_model_config(cfg)
    return create_model(config)
# endregion

# region 从 JSON 创建模型
def create_model_from_json(json_path: str) -> "Model":
    """
    从 JSON 文件创建模型。

    Args:
        json_path: JSON 配置文件路径

    Returns:
        Model: 创建的模型对象
    """
    import json
    with open(json_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    return create_model_from_dict(cfg)
# endregion


if __name__ == "__main__":

    from abq_serp_sub.processes.parts.material_instances import PDMS, PI, CU

    test_config = ModelConfig(
        modelname="test_model",
        substrate_config=SolidSubstrateConfig(
            modelname="test_model",
            partname="Substrate",
            geom=SolidSubstrateGeomConfig(
                length=8.0,
                width=11.0,
                depth=0.8,
            ),
            material=PDMS,
            mesh=SubstrateMeshConfig(
                seed_size=0.05,
                edge_seed_size=0.05,
            ),
        ),
        wire_config=WireConfig(
            modelname="test_model",
            partname="Wire",
            geom=WireGeomConfig(
                w=0.5,
                l_1=6.0,
                l_2=6.0,
                m=1,
                rotation_angle=0,
                rotation_center=RotationCenter.PART_CENTER,
                has_end_caps=False,
                flip_vertical=True,
            ),
            section=WireSectionConfig(
                pi_thickness=4e-3,
                cu_thickness=0.3e-3,
                pi_elastic=PI,
                cu_elastic=CU,
            ),
            mesh=WireMeshConfig(seed_size=0.05),
        ),
        loading=LoadingConfig(u1=0.1, u2=0.5),
        computing=ComputingConfig(num_cpus=4, enable_restart=False),
        interaction=InteractionConfig(use_cohesive=False),
        output=OutputConfig(global_output=False),
        # 分析步配置
        steps=(
            # Step-1: 预加载步
            AnalysisStepConfig(
                step_type=StepType.STATIC,
                config=StaticStepConfig(
                    max_num_inc=150,
                    initial_inc=0.1,
                    min_inc=1e-08,
                    max_inc=0.5,
                ),
                enable_restart=False,
                restart_intervals=1,
                set_time_incrementation=True,
            ),
            # Step-2: 拉伸步
            AnalysisStepConfig(
                step_type=StepType.STATIC,
                config=StaticStepConfig(
                    max_num_inc=10000,
                    initial_inc=0.02,
                    min_inc=1e-08,
                    max_inc=0.05,
                ),
                enable_restart=False,
                restart_intervals=2,
                set_time_incrementation=False,
            ),
        ),
    )
    print("使用内置测试配置")
    model = create_model(test_config)