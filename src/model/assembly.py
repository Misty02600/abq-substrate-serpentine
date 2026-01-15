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

from dataclasses import dataclass

from .pores import calculate_circle_radius, generate_circles_grid
from .substrate import build_porous_substrate, refine_substrate_edges_around_wire
from ..utils.abaqus_utils import get_bounding_box
from .wire import build_serpentine_wire


# region 分析步配置

@dataclass
class StepIncrementConfig:
    """
    分析步增量控制配置。

    这些是用户可能需要调整的参数，后续可添加到配置文件中。

    Attributes:
        max_num_inc (int): 最大增量步数，默认 150
        initial_inc (float): 初始增量，默认 0.1
        min_inc (float): 最小增量，默认 1e-08
        max_inc (float): 最大增量，默认 0.5
    """
    max_num_inc: int = 150
    initial_inc: float = 0.1
    min_inc: float = 1e-08
    max_inc: float = 0.5


# 预设配置
DEFAULT_PRELOAD_CONFIG = StepIncrementConfig()  # Step-1 默认配置

# endregion


# region 通用分析配置函数

def create_preload_step(
    model: "Model",
    name: str = "Step-1",
    previous: str = "Initial",
    config: StepIncrementConfig | None = None,
    enable_restart: bool = False,
):
    """
    创建预加载分析步（Step-1）。

    Args:
        model: Abaqus 模型对象
        name (str): 分析步名称，默认 "Step-1"
        previous (str): 前一个分析步名称，默认 "Initial"
        config (StepIncrementConfig | None): 增量控制配置，None 时使用默认值
        enable_restart (bool): 是否启用重启动功能，默认 False

    Returns:
        Step: 创建的分析步对象
    """
    if config is None:
        config = DEFAULT_PRELOAD_CONFIG

    step = model.StaticStep(
        name=name,
        previous=previous,
        nlgeom=ON,
        maxNumInc=config.max_num_inc,
        initialInc=config.initial_inc,
        minInc=config.min_inc,
        maxInc=config.max_inc,
        stabilizationMagnitude=0.002,
        stabilizationMethod=DISSIPATED_ENERGY_FRACTION,
        continueDampingFactors=False,
        adaptiveDampingRatio=0.2,
    )

    if enable_restart:
        step.Restart(frequency=0, numberIntervals=1, overlay=OFF, timeMarks=OFF)

    step.control.setValues(
        allowPropagation=OFF,
        resetDefaultValues=OFF,
        timeIncrementation=(4.0, 8.0, 9.0, 16.0, 10.0, 4.0, 12.0, 8.0, 6.0, 3.0, 50.0),
    )

    return step


def create_stretch_step(
    model: "Model",
    u1: float,
    u2: float,
    name: str = "Step-2",
    previous: str = "Step-1",
    config: StepIncrementConfig | None = None,
    enable_restart: bool = False,
):
    """
    创建拉伸分析步（Step-2）。

    增量控制根据位移差自动计算，每步拉伸约 0.008。
    如果提供了 config，则使用 config.min_inc 作为最小增量。

    Args:
        model: Abaqus 模型对象
        u1 (float): 第一步施加的位移（用于计算增量）
        u2 (float): 第二步施加的位移（用于计算增量）
        name (str): 分析步名称，默认 "Step-2"
        previous (str): 前一个分析步名称，默认 "Step-1"
        config (StepIncrementConfig | None): 增量控制配置（仅使用 min_inc），None 时使用默认值
        enable_restart (bool): 是否启用重启动功能，默认 False

    Returns:
        Step: 创建的分析步对象
    """
    if config is None:
        config = DEFAULT_PRELOAD_CONFIG

    # 计算增量步大小，每步拉伸 0.008
    step_increment = 0.008 / (u2 - u1) if (u2 - u1) > 0.01 else 0.5
    max_num_inc = int(1 / step_increment) * 6

    step = model.StaticStep(
        name=name,
        previous=previous,
        nlgeom=ON,
        maxNumInc=max_num_inc,
        initialInc=step_increment,
        minInc=config.min_inc,
        maxInc=step_increment,
        stabilizationMagnitude=0.002,
        stabilizationMethod=DISSIPATED_ENERGY_FRACTION,
        continueDampingFactors=False,
        adaptiveDampingRatio=0.2,
    )

    if enable_restart:
        step.Restart(frequency=0, numberIntervals=2, overlay=OFF, timeMarks=OFF)

    return step


def create_analysis_steps(
    model: "Model",
    u1: float,
    u2: float,
    preload_config: StepIncrementConfig | None = None,
    stretch_config: StepIncrementConfig | None = None,
    enable_restart: bool = False,
):
    """
    创建分析步 Step-1 和 Step-2（便捷函数）。

    Args:
        model: Abaqus 模型对象
        u1 (float): 第一步施加的位移
        u2 (float): 第二步施加的位移
        preload_config (StepIncrementConfig | None): Step-1 增量控制配置
        stretch_config (StepIncrementConfig | None): Step-2 增量控制配置
        enable_restart (bool): 是否启用重启动功能，默认 False

    Returns:
        tuple: (step1, step2) 创建的分析步对象
    """
    step1 = create_preload_step(
        model=model,
        config=preload_config,
        enable_restart=enable_restart,
    )

    step2 = create_stretch_step(
        model=model,
        u1=u1,
        u2=u2,
        config=stretch_config,
        enable_restart=enable_restart,
    )

    return step1, step2


def setup_field_outputs(
    model: "Model",
    modelname: str,
    global_output: bool = False,
):
    """
    设置场输出请求。

    Args:
        model: Abaqus 模型对象
        modelname (str): 模型名称
        global_output (bool): 是否使用全局输出，默认 False
    """
    if global_output:
        # 使用全局输出
        model.fieldOutputRequests["F-Output-1"].setValues(
            variables=("U", "RF", "LE", "CSTRESS", "CFORCE"),
            sectionPoints=(1, 2, 3, 4, 5, 6, 7, 8, 9),
        )
    else:
        # 使用分别的场输出
        _regionDef = model.rootAssembly.allInstances["Substrate-1"].sets["TPC_A"]
        model.FieldOutputRequest(
            name="F-Output-1",
            createStepName="Step-2",
            variables=("U",),
            frequency=1,
            region=_regionDef,
        )

        _regionDef = model.rootAssembly.allInstances["Wire-1"].sets["All"]
        model.FieldOutputRequest(
            name="F-Output-2",
            createStepName="Step-2",
            variables=("LE", "U", "CSTRESS", "CFORCE"),
            frequency=1,
            region=_regionDef,
            sectionPoints=(1, 2, 3, 4, 5, 6, 7, 8, 9),
        )


# endregion


def create_porous_model(
    porosity,
    T_xi,
    T_delta,
    random_seed,
    n_rows,
    n_cols,
    square_size,
    u1,
    u2,
    substrate_seed_size,
    substrate_edge_seed_size,
    depth,
    w,
    l_1,
    l_2,
    m,
    wire_seed_size,
    USE_STANDARD_CIRCLES,
    num_cpus,
    modelname,
    origin,
    global_output=False,
    enable_restart=False,
    use_cohesive=False,
    wire_rotation_angle=0.0,
) -> "Model":
    """
    创建多孔基底模型的主函数

    Args:
        porosity (float): 孔隙率 (0 < porosity <= 0.7854)
        T_xi (float): 坐标偏差的截断上下限（圆形区域的半径）
        T_delta (float): 直径偏差的截断上下限
        random_seed (int): 随机种子，用于控制随机圆孔生成
        n_rows (int): 网格行数
        n_cols (int): 网格列数
        square_size (float): 正方形单元边长
        u1 (float): 第一步施加的位移
        u2 (float): 第二步施加的位移
        substrate_seed_size (float): 基底布种尺寸
        substrate_edge_seed_size (float): 基底边细化布种尺寸（用于细化导线区域网格）
        depth (float): 部件厚度
        w (float): 蛇形线宽度
        l_1 (float): 单元体水平节距（一个完整周期宽度）
        l_2 (float): 竖直直线段长度
        m (int): 周期数（完整周期的个数）
        wire_seed_size (float): 蛇形线布种尺寸
        USE_STANDARD_CIRCLES (bool): 是否使用标准圆孔排列
        num_cpus (int): CPU核心数，用于numCpus和numDomains
        modelname (str): 模型名称
        origin (tuple): 蛇形线原点坐标 (x, y, z)
        global_output (bool): 是否使用全局输出，默认为False
        enable_restart (bool): 是否启用重启动功能，默认为False
        use_cohesive (bool): 是否使用Cohesive接触，默认为False（使用Tie约束）
        wire_rotation_angle (float): 蛇形线绕z轴逆时针旋转角度（单位：度），默认为0.0

    Returns:
        Model: 创建的模型对象
    """

    # region 初始化和模型创建
    # 设置随机种子
    import numpy as np
    np.random.seed(random_seed)

    print(f"正在创建模型: {modelname}")

    # 创建模型
    model = mdb.Model(name=modelname)
    # endregion

    # region 几何构建
    radius_mean = calculate_circle_radius(square_size, porosity)  # 半径的期望值
    print("根据孔隙率计算得到的圆孔半径：", radius_mean)

    # 生成圆孔
    if USE_STANDARD_CIRCLES:
        # 标准排列
        circles = []
        for i in range(n_rows):
            row = []
            for j in range(n_cols):
                center_x = (j + 0.5) * square_size
                center_y = (i + 0.5) * square_size
                row.append([center_x, center_y, radius_mean])
            circles.append(row)
        circles = np.array(circles)
    else:
        # 随机排列
        circles = generate_circles_grid(
            n_rows,
            n_cols,
            square_size,
            radius_mean,
            T_xi,
            T_delta,
        )
    # endregion

    # region 部件创建和装配

    # 创建基底部件（已包含每个单元的细化划分）
    sub_part = build_porous_substrate(
        modelname=modelname,
        partname="Substrate",
        circles=circles,
        square_size=square_size,
        depth=depth,
        substrate_seed_size=substrate_seed_size,
        generate_mesh=False
    )

    # 创建蛇形线部件
    wire_part = build_serpentine_wire(
        modelname=modelname,
        partname="Wire",
        w=w,
        l_1=l_1,
        l_2=l_2,
        m=m,
        wire_seed_size=wire_seed_size,
        origin=origin,
    )

    asm = model.rootAssembly
    sub_inst = asm.Instance(name="Substrate-1", part=sub_part, dependent=ON)
    wire_inst = asm.Instance(name="Wire-1", part=wire_part, dependent=ON)

    # 旋转Wire实例（如果指定了旋转角度）
    if wire_rotation_angle != 0.0:
        asm.rotate(
            instanceList=('Wire-1',),
            axisPoint=origin,
            axisDirection=(0.0, 0.0, 1.0),
            angle=wire_rotation_angle
        )
        print(f"Wire实例已旋转 {wire_rotation_angle} 度")

    # 计算导线边界并对导线周围的基底边进行细化
    wire_bbox = get_bounding_box(wire_inst)
    wire_x_min, wire_y_min, wire_z_min = wire_bbox['low']
    wire_x_max, wire_y_max, wire_z_max = wire_bbox['high']
    wire_y_min -= w / 2
    wire_y_max += w / 2
    wire_bounds = (wire_x_min, wire_y_min, wire_z_min, wire_x_max, wire_y_max, wire_z_max)

    refine_substrate_edges_around_wire(
        modelname=modelname,
        partname="Substrate",
        wire_bounds=wire_bounds,
        substrate_edge_seed_size=substrate_edge_seed_size,
    )
    # endregion

    # region 分析步&场输出
    step1, step2 = create_analysis_steps(
        model=model,
        u1=u1,
        u2=u2,
        enable_restart=enable_restart,
    )

    setup_field_outputs(
        model=model,
        modelname=modelname,
        global_output=global_output,
    )
    # endregion

    # region 相互作用

    if use_cohesive:
        # 使用Cohesive接触
        mdb.models[modelname].ContactProperty('IntProp-1')
        mdb.models[modelname].interactionProperties['IntProp-1'].CohesiveBehavior()
        mdb.models[modelname].ContactStd(name='Int-1', createStepName='Initial')
        mdb.models[modelname].interactions['Int-1'].includedPairs.setValuesInStep(
            stepName='Initial', useAllstar=ON)
        mdb.models[modelname].interactions['Int-1'].contactPropertyAssignments.appendInStep(
            stepName='Initial', assignments=((GLOBAL, SELF, 'IntProp-1'), ))
    else:
        # 使用Tie约束
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

    # 三点式约束
    # TPC_A点约束yz方向
    mdb.models[modelname].DisplacementBC(
        name="TPC_A",
        createStepName="Initial",
        region=sub_inst.sets["TPC_A"],
        u1=UNSET,
        u2=SET,
        u3=SET,
        ur1=UNSET,
        ur2=UNSET,
        ur3=UNSET,
        amplitude=UNSET,
        distributionType=UNIFORM,
        fieldName="",
        localCsys=None,
    )

    # TPC_B点约束z方向
    mdb.models[modelname].DisplacementBC(
        name="TPC_B",
        createStepName="Initial",
        region=sub_inst.sets["TPC_B"],
        u1=UNSET,
        u2=UNSET,
        u3=SET,
        ur1=UNSET,
        ur2=UNSET,
        ur3=UNSET,
        amplitude=UNSET,
        distributionType=UNIFORM,
        fieldName="",
        localCsys=None,
    )

    # 左侧施加位移
    mdb.models[modelname].DisplacementBC(
        name="left-U",
        createStepName="Initial",
        region=sub_inst.sets["LeftFace"],
        u1=SET,
        u2=UNSET,
        u3=UNSET,
        ur1=UNSET,
        ur2=UNSET,
        ur3=UNSET,
        amplitude=UNSET,
        distributionType=UNIFORM,
        fieldName="",
        localCsys=None,
    )

    mdb.models[modelname].boundaryConditions["left-U"].setValuesInStep(
        stepName="Step-1", u1=-u1
    )

    mdb.models[modelname].boundaryConditions["left-U"].setValuesInStep(
        stepName="Step-2", u1=-u2
    )

    # 右侧施加位移
    mdb.models[modelname].DisplacementBC(
        name="right-U",
        createStepName="Initial",
        region=sub_inst.sets["RightFace"],
        u1=SET,
        u2=UNSET,
        u3=UNSET,
        ur1=UNSET,
        ur2=UNSET,
        ur3=UNSET,
        amplitude=UNSET,
        distributionType=UNIFORM,
        fieldName="",
        localCsys=None,
    )

    mdb.models[modelname].boundaryConditions["right-U"].setValuesInStep(
        stepName="Step-1", u1=u1
    )

    mdb.models[modelname].boundaryConditions["right-U"].setValuesInStep(
        stepName="Step-2", u1=u2
    )

    # endregion

    # region 作业创建
    # 创建分析作业
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