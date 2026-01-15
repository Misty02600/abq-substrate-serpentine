import os
import sys
from pathlib import Path
import inspect
from typing import TYPE_CHECKING

from abaqus import *
from abaqusConstants import *

if TYPE_CHECKING:
    from abaqus.Model.Model import Model

# 脚本所在目录：noGUI 里 __file__ 一定有；Run Script 时看 ② 退路
try:                                    # ① 绝大多数情况下
    SCRIPT_DIR = Path(__file__).parent.resolve()
except NameError:                       # ② 只有 GUI ▸ Run Script 才会进这里
    fname = inspect.getfile(inspect.currentframe())
    SCRIPT_DIR = Path(fname).parent.resolve() if not fname.startswith('<') else Path(os.getcwd()).resolve()

# 把脚本目录放到 import 搜索路径最前
sys.path.append(str(SCRIPT_DIR))

from src.model.substrate import build_solid_substrate
from src.model.wire import build_serpentine_wire_no_caps
from src.utils.abaqus_utils import get_bounding_box


# region 模型创建

def create_solid_serpentine_model(
    modelname: str,
    substrate_length: float,
    substrate_width: float,
    depth: float,
    substrate_seed_size: float,
    w: float,
    l_1: float,
    l_2: float,
    m: int,
    wire_seed_size: float,
    pi_thickness: float,
    cu_thickness: float,
    origin: tuple[float, float, float] | None,
    u1: float,
    u2: float,
    num_cpus: int = 4,
    wire_rotation_angle: float = 0.0,
    stabilization_magnitude: float = 0.002,
    adaptive_damping_ratio: float = 0.2,
    use_cohesive: bool = False,
    global_output: bool = False,
):
    """
    创建实心基底+蛇形导线模型并设置加载、约束与作业。

    Args:
        modelname (str): 模型名称。
        substrate_length (float): 基底长度（X方向）。
        substrate_width (float): 基底宽度（Y方向）。
        depth (float): 基底厚度（Z方向）。
        substrate_seed_size (float): 基底全局布种尺寸。
        w (float): 蛇形线宽。
        l_1 (float): 蛇形线水平节距。
        l_2 (float): 竖直直线段长度。
        m (int): 周期数。
        wire_seed_size (float): 导线布种尺寸。
        pi_thickness (float): PI 单层厚度（上下两层相同）。
        cu_thickness (float): Cu 单层厚度（中间层）。
        origin (tuple[float, float, float] | None): 导线草图原点（若为None则自动居中放置）。
        u1 (float): 第一步左右端施加的位移量。
        u2 (float): 第二步左右端施加的位移量。
        num_cpus (int, optional): 作业使用的CPU数。默认4。
        wire_rotation_angle (float, optional): 导线绕Z轴逆时针旋转角度（度）。默认0.0。
        stabilization_magnitude (float, optional): 稳定化幅度。默认0.002。
        adaptive_damping_ratio (float, optional): 自适应阻尼比。默认0.2。
        use_cohesive (bool, optional): 是否使用Cohesive接触（否则Tie）。默认False。
        global_output (bool, optional): 是否使用全局场输出。默认False。

    Returns:
        Model: 创建好的 Abaqus 模型对象。
    """
    print(f"正在创建模型: {modelname}")
    model = mdb.Model(name=modelname)

    # 基底
    sub_part = build_solid_substrate(
        modelname=modelname,
        partname="Substrate",
        length=substrate_length,
        width=substrate_width,
        depth=depth,
        substrate_seed_size=substrate_seed_size,
        generate_mesh=True,
    )

    # 导线
    wire_part = build_serpentine_wire_no_caps(
        modelname=modelname,
        partname="Wire",
        w=w,
        l_1=l_1,
        l_2=l_2,
        m=m,
        wire_seed_size=wire_seed_size,
        pi_thickness=pi_thickness,
        cu_thickness=cu_thickness,
        origin=origin if origin is not None else (0.0, 0.0, depth),
    )

    # 装配
    asm = model.rootAssembly
    sub_inst = asm.Instance(name="Substrate-1", part=sub_part, dependent=ON)
    wire_inst = asm.Instance(name="Wire-1", part=wire_part, dependent=ON)

    if wire_rotation_angle != 0.0:
        asm.rotate(
            instanceList=("Wire-1",),
            axisPoint=origin if origin is not None else (0.0, 0.0, depth),
            axisDirection=(0.0, 0.0, 1.0),
            angle=wire_rotation_angle,
        )
        print(f"Wire实例已旋转 {wire_rotation_angle} 度")

    # 自动居中放置（通过实例包围盒计算平移量；不依赖“把origin放中间”的近似）
    if origin is None:
        wire_bbox = get_bounding_box(wire_inst)
        (wire_x_min, wire_y_min, _wire_z_min) = wire_bbox["low"]
        (wire_x_max, wire_y_max, _wire_z_max) = wire_bbox["high"]

        wire_center_x = 0.5 * (wire_x_min + wire_x_max)
        wire_center_y = 0.5 * (wire_y_min + wire_y_max)

        target_center_x = 0.5 * substrate_length
        target_center_y = 0.5 * substrate_width

        dx = target_center_x - wire_center_x
        dy = target_center_y - wire_center_y

        asm.translate(instanceList=("Wire-1",), vector=(dx, dy, 0.0))
        print(f"Wire实例已居中平移: dx={dx:.3f}, dy={dy:.3f}")

    # 分析步
    step1 = model.StaticStep(
        name="Step-1",
        previous="Initial",
        nlgeom=ON,
        maxNumInc=3000,
        initialInc=0.1,
        minInc=1e-08,
        maxInc=0.5,
        stabilizationMagnitude=stabilization_magnitude,
        stabilizationMethod=DISSIPATED_ENERGY_FRACTION,
        continueDampingFactors=False,
        adaptiveDampingRatio=adaptive_damping_ratio,
    )

    step1.control.setValues(
        allowPropagation=OFF,
        resetDefaultValues=OFF,
        timeIncrementation=(
            4.0,
            8.0,
            9.0,
            16.0,
            10.0,
            4.0,
            12.0,
            8.0,
            6.0,
            3.0,
            50.0,
        ),
    )

    # 若 u1 与 u2 相同（容差内），则不创建 Step-2
    delta_u = u2 - u1
    has_step2 = abs(delta_u) > 1e-12

    if has_step2:
        step2_increment = 0.008 / delta_u if delta_u > 0.01 else 0.5
        max_num_inc = int(1 / step2_increment) * 6

        model.StaticStep(
            name="Step-2",
            previous="Step-1",
            nlgeom=ON,
            maxNumInc=max_num_inc,
            initialInc=step2_increment,
            minInc=1e-08,
            maxInc=step2_increment,
            stabilizationMagnitude=stabilization_magnitude,
            stabilizationMethod=DISSIPATED_ENERGY_FRACTION,
            continueDampingFactors=False,
            adaptiveDampingRatio=adaptive_damping_ratio,
        )

    # 场输出
    if global_output:
        model.fieldOutputRequests["F-Output-1"].setValues(
            variables=("U", "RF", "LE", "CSTRESS", "CFORCE"),
            sectionPoints=(1, 2, 3, 4, 5, 6, 7, 8, 9),
        )
    else:
        output_step = "Step-2" if has_step2 else "Step-1"

        tpc_region = model.rootAssembly.allInstances["Substrate-1"].sets["TPC_A"]
        model.FieldOutputRequest(
            name="F-Output-1",
            createStepName=output_step,
            variables=("U",),
            frequency=1,
            region=tpc_region,
        )

        wire_region = model.rootAssembly.allInstances["Wire-1"].sets["All"]
        model.FieldOutputRequest(
            name="F-Output-2",
            createStepName=output_step,
            variables=("LE", "U", "CSTRESS", "CFORCE"),
            frequency=1,
            region=wire_region,
            sectionPoints=(1, 2, 3, 4, 5, 6, 7, 8, 9),
        )

    # 接触/约束
    if use_cohesive:
        model.ContactProperty("IntProp-1")
        model.interactionProperties["IntProp-1"].Damage(
            initTable=((0.5, 0.5, 0.5),),
            useEvolution=ON,
            evolutionType=ENERGY,
            evolTable=((0.003,),),
        )
        model.interactionProperties["IntProp-1"].CohesiveBehavior(
            defaultPenalties=OFF,
            table=((2000.0, 2000.0, 2000.0),),
        )

        # 显式创建接触对（与 tests/abaqusMacros.py 录制宏一致）
        model.SurfaceToSurfaceContactStd(
            name="Int-1",
            createStepName="Initial",
            main=wire_inst.surfaces["Bottom"],
            secondary=sub_inst.surfaces["TopFace"],
            sliding=FINITE,
            thickness=ON,
            interactionProperty="IntProp-1",
            adjustMethod=NONE,
            initialClearance=OMIT,
            datumAxis=None,
            clearanceRegion=None,
        )
    else:
        model.Tie(
            name="Constraint-1",
            main=sub_inst.surfaces["TopFace"],
            secondary=wire_inst.surfaces["Bottom"],
            positionToleranceMethod=COMPUTED,
            adjust=ON,
            tieRotations=ON,
            thickness=ON,
        )

    # 边界条件
    model.DisplacementBC(
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

    model.DisplacementBC(
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

    model.DisplacementBC(
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

    model.boundaryConditions["left-U"].setValuesInStep(stepName="Step-1", u1=-u1)
    if has_step2:
        model.boundaryConditions["left-U"].setValuesInStep(stepName="Step-2", u1=-u2)

    model.DisplacementBC(
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

    model.boundaryConditions["right-U"].setValuesInStep(stepName="Step-1", u1=u1)
    if has_step2:
        model.boundaryConditions["right-U"].setValuesInStep(stepName="Step-2", u1=u2)

    # 作业
    mdb.Job(
        name=modelname,
        model=modelname,
        description=f"Analysis job for model {modelname}",
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
        userSubroutine="",
        scratch="",
        resultsFormat=ODB,
        numThreadsPerMpiProcess=1,
        multiprocessingMode=DEFAULT,
        numCpus=num_cpus,
        numDomains=num_cpus,
        numGPUs=0,
    )

    print(f"模型 {modelname} 创建完成")
    return model

# endregion


if __name__ == "__main__":
    # 示例参数，可按需修改
    model_name = "Solid-Serpentine-Example"

    model_params = dict(
        modelname=model_name,
        substrate_length=6.0,
        substrate_width=5.0,
        depth=0.5,
        substrate_seed_size=0.03,
        w=0.2,
        l_1=3.0,
        l_2=2.0,
        m=1,
        wire_seed_size=0.03,
        origin=None,
        pi_thickness=0.005,
        cu_thickness=0.003,
        u1=2,
        u2=2,
        num_cpus=16,
        wire_rotation_angle=0.0,
        stabilization_magnitude=0.002,
        adaptive_damping_ratio=0.2,
        use_cohesive=True,
        global_output=True,
    )

    create_solid_serpentine_model(**model_params)
